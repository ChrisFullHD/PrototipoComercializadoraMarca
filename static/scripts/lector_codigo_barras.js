/*
 * Lector de códigos de barras — Comercializadora Marca
 * ====================================================
 *
 * CONTRATO CON EL RESTO DEL SISTEMA (no cambiar sin revisar los consumidores)
 * ---------------------------------------------------------------------------
 * Marcado (componentes/lector_codigo_barras.html):
 *   [data-barcode-reader]           raíz; data-action-mode ("lookup" | "input"),
 *                                   data-target-input (selector CSS del campo destino),
 *                                   data-stop-after-read="true" (opcional),
 *                                   data-confirm-reads="N" (opcional, defecto 2),
 *                                   data-video-width / data-video-height (opcionales)
 *   [data-reader-mode="usb|camera"] [data-usb-panel] [data-camera-panel]
 *   [data-barcode-request]          formulario HTMX (solo modo lookup)
 *   [data-barcode-input]            campo del lector USB
 *   [data-reader-status]            estado; data-state: idle|loading|error|encontrado|no_encontrado|invalido
 *   [data-barcode-result-container] contenedor del resultado
 *   [data-camera-select] [data-camera-start] [data-camera-stop] [data-camera-video]
 *   Respuesta del backend: [data-barcode-result] con data-state, data-code, data-message,
 *   data-product-id, data-product-name, data-product-barcode, data-category,
 *   data-unit-stock, data-weight-stock, data-price.
 *
 * Eventos (burbujean desde la raíz):
 *   barcode:assigned          { code, source, target }          (modo input)
 *   barcode:product-found     { code, state, product{...} }     (modo lookup)
 *   barcode:product-not-found { code, state }
 *   barcode:invalid           { code, state }
 *   barcode:processed         { code, state }                   (tras cada respuesta HTMX)
 *
 * API opcional por elemento:  root.barcodeReader = { submit, startCamera, stopCamera, isCameraActive }
 *
 * Depuración:
 *   ?barcode_debug en la URL, o window.cmBarcodeDebug = true
 *   cmBarcodeTest("7801234567894")        simula una lectura (prueba la escritura)
 *   cmBarcodeSnapshot()                   muestra el cuadro, las zonas localizadas y lo que recibe ZXing
 *   cmBarcodeTestImage("/static/img/ean13_prueba.png")   prueba el motor con una imagen
 *   window.cmBarcodeAllFormats = true     (antes de activar la cámara) quita la restricción EAN/UPC
 *
 * MOTOR DE LECTURA POR CÁMARA (ZXing)
 * -----------------------------------
 * 1. Localiza el código en cada fotograma (tensor de estructura por bloques: zonas con bordes
 *    fuertes y de una sola orientación). Funciona aunque el código ocupe una fracción pequeña
 *    del cuadro, esté inclinado o vertical.
 * 2. Recorta esa zona desde el video a resolución completa, la endereza y la amplía.
 * 3. Preprocesa para distintas iluminaciones (estiramiento de niveles por percentiles, gamma,
 *    realce horizontal) y prueba los binarizadores local (Hybrid) y global de ZXing.
 * 4. Si no hay candidatos, recorre cuadro completo y mosaicos.
 * 5. Exige lecturas repetidas antes de aceptar (evita falsos positivos de webcams ruidosas).
 */
(function () {
  "use strict";

  if (window.cmBarcodeReaderInitialized) {
    return;
  }
  window.cmBarcodeReaderInitialized = true;

  var CONFIG = {
    VIDEO_WIDTH: 1920, // resolución ideal solicitada a la webcam (cae sola a la máxima real)
    VIDEO_HEIGHT: 1080,
    LOC_WIDTH: 640, // ancho de la imagen reducida usada para localizar
    BLOCK: 8, // lado del bloque de localización (px de la imagen reducida)
    MIN_BLOCKS: 8, // bloques mínimos para considerar un candidato
    MIN_COHERENCE: 0.55, // coherencia de orientación mínima (0-1)
    MIN_ENERGY: 60, // energía de gradiente mínima por píxel de un bloque (sobre el ruido)
    MAX_SIGN_BIAS: 0.6, // |suma con signo| / suma absoluta máxima (barras alternan signo)
    MAX_CANDIDATES: 3,
    ROI_TARGET: 900, // lado largo objetivo de la zona recortada (px)
    ROI_MAX: 1600,
    TICK_MS: 40, // pausa mínima entre intentos
    TIME_BUDGET_MS: 70, // tiempo máximo de decodificación por ciclo
    CONFIRM_READS: 2,
    CONFIRM_WINDOW_MS: 2000,
    CAMERA_DUPLICATE_MS: 2500,
    USB_DUPLICATE_MS: 1500,
    CAMERA_STORAGE_KEY: "cmBarcodeCamera",
  };

  // Variantes de preprocesado/decodificación que se rotan entre ciclos.
  var DEG = Math.PI / 180;
  var COMBOS = [
    { jitter: 0, sharpen: false, gamma: 1, binarizer: "hybrid" },
    { jitter: 0, sharpen: false, gamma: 1, binarizer: "global" },
    { jitter: 0, sharpen: true, gamma: 1, binarizer: "hybrid" },
    { jitter: 4 * DEG, sharpen: false, gamma: 1, binarizer: "hybrid" },
    { jitter: -4 * DEG, sharpen: false, gamma: 1, binarizer: "hybrid" },
    { jitter: 0, sharpen: false, gamma: 0.65, binarizer: "global" },
    { jitter: 0, sharpen: false, gamma: 1.6, binarizer: "hybrid" },
    { jitter: 0, sharpen: true, gamma: 1, binarizer: "global" },
  ];

  // Zonas de respaldo (fracciones del cuadro: cx, cy, ancho, alto).
  var FALLBACK_REGIONS = [
    [0.5, 0.5, 1, 1],
    [0.5, 0.5, 0.55, 0.55],
    [0.3, 0.3, 0.65, 0.65],
    [0.7, 0.3, 0.65, 0.65],
    [0.3, 0.7, 0.65, 0.65],
    [0.7, 0.7, 0.65, 0.65],
  ];

  var readers = [];

  /* ------------------------------------------------------------------ */
  /* Utilidades generales                                                */
  /* ------------------------------------------------------------------ */

  function debugEnabled() {
    return (
      window.cmBarcodeDebug === true ||
      /[?&]barcode_debug\b/.test(window.location.search)
    );
  }

  function log() {
    if (!debugEnabled()) {
      return;
    }
    console.log.apply(
      console,
      ["[barcode]"].concat(Array.prototype.slice.call(arguments))
    );
  }

  // ZXing avisa con console.warn ("non-ReaderException ...") por cada formato que no
  // encuentra nada en cada intento. Es ruido normal del escaneo continuo.
  var originalWarn = console.warn;
  console.warn = function () {
    if (
      typeof arguments[0] === "string" &&
      arguments[0].indexOf("non-ReaderException") !== -1
    ) {
      return;
    }
    return originalWarn.apply(console, arguments);
  };

  // BarcodeFormat / DecodeHintType viven en @zxing/library (window.ZXing);
  // se usa window.ZXingBrowser como respaldo.
  function zxingExport(name) {
    if (window.ZXing && window.ZXing[name]) {
      return window.ZXing[name];
    }
    if (window.ZXingBrowser && window.ZXingBrowser[name]) {
      return window.ZXingBrowser[name];
    }
    return null;
  }

  function stopTracks(stream) {
    if (stream) {
      stream.getTracks().forEach(function (track) {
        track.stop();
      });
    }
  }

  function storageGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      // Almacenamiento no disponible: la preferencia simplemente no se recuerda.
    }
  }

  /* ------------------------------------------------------------------ */
  /* Procesamiento de imagen (funciones puras, sin DOM)                  */
  /* ------------------------------------------------------------------ */

  function rgbaToGray(data) {
    var n = data.length >> 2;
    var gray = new Uint8ClampedArray(n);
    for (var i = 0, j = 0; j < n; i += 4, j++) {
      gray[j] = (data[i] * 77 + data[i + 1] * 150 + data[i + 2] * 29) >> 8;
    }
    return gray;
  }

  /**
   * Localiza zonas con aspecto de código de barras (bordes fuertes y orientación coherente).
   * gray: luminancia w*h. Devuelve candidatos ordenados por puntaje, en píxeles de gray:
   *   { x0, y0, x1, y1, theta, coherence, blocks }
   * theta = dirección del gradiente (rad, eje y hacia abajo). Girar la imagen -theta deja
   * las barras verticales.
   */
  function localizeBarcodes(gray, w, h) {
    var B = CONFIG.BLOCK;
    var bw = Math.floor(w / B);
    var bh = Math.floor(h / B);
    if (bw < 4 || bh < 4) {
      return [];
    }
    var n = bw * bh;
    var sxx = new Float32Array(n);
    var syy = new Float32Array(n);
    var sxy = new Float32Array(n);
    var gxSum = new Float32Array(n); // suma con signo (se cancela en un código de barras)
    var gySum = new Float32Array(n);
    var gxAbs = new Float32Array(n);
    var gyAbs = new Float32Array(n);
    var xMax = bw * B;
    var yMax = bh * B;

    for (var y = 1; y < yMax - 1; y++) {
      var row = y * w;
      var brow = ((y / B) | 0) * bw;
      for (var x = 1; x < xMax - 1; x++) {
        var i = row + x;
        var gx = gray[i + 1] - gray[i - 1];
        var gy = gray[i + w] - gray[i - w];
        var b = brow + ((x / B) | 0);
        sxx[b] += gx * gx;
        syy[b] += gy * gy;
        sxy[b] += gx * gy;
        gxSum[b] += gx;
        gySum[b] += gy;
        gxAbs[b] += gx < 0 ? -gx : gx;
        gyAbs[b] += gy < 0 ? -gy : gy;
      }
    }

    // Un bloque "de barras" cumple tres cosas:
    //  1. energía de gradiente por encima del ruido (umbral absoluto bajo: sirve con poca luz);
    //  2. una orientación dominante (coherencia);
    //  3. el gradiente cambia de signo a lo largo de esa orientación (varias barras). Un borde
    //     simple del fondo (caja, mano, sombra) tiene un solo signo y se descarta.
    var area = B * B;
    var mask = new Uint8Array(n);
    var maskCount = 0;
    for (var m = 0; m < n; m++) {
      var tot = sxx[m] + syy[m];
      if (tot / area < CONFIG.MIN_ENERGY) {
        continue;
      }
      var dif = sxx[m] - syy[m];
      var coh = Math.sqrt(dif * dif + 4 * sxy[m] * sxy[m]) / (tot + 1e-6);
      if (coh < CONFIG.MIN_COHERENCE) {
        continue;
      }
      var along = dif >= 0
        ? Math.abs(gxSum[m]) / (gxAbs[m] + 1e-6)
        : Math.abs(gySum[m]) / (gyAbs[m] + 1e-6);
      if (along <= CONFIG.MAX_SIGN_BIAS) {
        mask[m] = 1;
        maskCount++;
      }
    }
    if (maskCount < CONFIG.MIN_BLOCKS) {
      return [];
    }

    // Dilatación 3x3 para unir los grupos de barras separados por espacios anchos.
    var dil = new Uint8Array(n);
    for (var by = 0; by < bh; by++) {
      for (var bx = 0; bx < bw; bx++) {
        if (!mask[by * bw + bx]) {
          continue;
        }
        for (var dy = -1; dy <= 1; dy++) {
          var ny = by + dy;
          if (ny < 0 || ny >= bh) continue;
          for (var dx = -1; dx <= 1; dx++) {
            var nx = bx + dx;
            if (nx < 0 || nx >= bw) continue;
            dil[ny * bw + nx] = 1;
          }
        }
      }
    }

    // Componentes conexas (8-vecindad) sobre la máscara dilatada.
    var label = new Uint8Array(n);
    var stack = new Int32Array(n);
    var candidates = [];
    for (var s = 0; s < n; s++) {
      if (!dil[s] || label[s]) {
        continue;
      }
      var sp = 0;
      stack[sp++] = s;
      label[s] = 1;
      var comp = {
        count: 0,
        minX: bw, minY: bh, maxX: -1, maxY: -1,
        sxx: 0, syy: 0, sxy: 0,
      };
      while (sp > 0) {
        var cur = stack[--sp];
        var cx = cur % bw;
        var cy = (cur / bw) | 0;
        if (mask[cur]) {
          comp.count++;
          if (cx < comp.minX) comp.minX = cx;
          if (cx > comp.maxX) comp.maxX = cx;
          if (cy < comp.minY) comp.minY = cy;
          if (cy > comp.maxY) comp.maxY = cy;
          comp.sxx += sxx[cur];
          comp.syy += syy[cur];
          comp.sxy += sxy[cur];
        }
        for (var ay = cy - 1; ay <= cy + 1; ay++) {
          if (ay < 0 || ay >= bh) continue;
          for (var ax = cx - 1; ax <= cx + 1; ax++) {
            if (ax < 0 || ax >= bw) continue;
            var nidx = ay * bw + ax;
            if (dil[nidx] && !label[nidx]) {
              label[nidx] = 1;
              stack[sp++] = nidx;
            }
          }
        }
      }

      if (comp.count < CONFIG.MIN_BLOCKS) {
        continue;
      }
      var den = comp.sxx + comp.syy;
      var cdif = comp.sxx - comp.syy;
      var ccoh = Math.sqrt(cdif * cdif + 4 * comp.sxy * comp.sxy) / (den + 1e-6);
      if (ccoh < CONFIG.MIN_COHERENCE) {
        continue;
      }
      candidates.push({
        x0: comp.minX * B,
        y0: comp.minY * B,
        x1: (comp.maxX + 1) * B,
        y1: (comp.maxY + 1) * B,
        theta: 0.5 * Math.atan2(2 * comp.sxy, cdif),
        coherence: ccoh,
        blocks: comp.count,
        score: comp.count * ccoh,
      });
    }

    candidates.sort(function (a, b) {
      return b.score - a.score;
    });
    return candidates.slice(0, CONFIG.MAX_CANDIDATES);
  }

  /** Reduce a la mitad promediando 2x2 (para refinar el ángulo sin coste alto). */
  function halveGray(gray, w, h) {
    var nw = w >> 1;
    var nh = h >> 1;
    var out = new Uint8ClampedArray(nw * nh);
    for (var y = 0; y < nh; y++) {
      var r0 = 2 * y * w;
      var r1 = r0 + w;
      var o = y * nw;
      for (var x = 0; x < nw; x++) {
        var i = 2 * x;
        out[o + x] = (gray[r0 + i] + gray[r0 + i + 1] + gray[r1 + i] + gray[r1 + i + 1]) >> 2;
      }
    }
    return { gray: out, w: nw, h: nh };
  }

  /** Convierte un candidato (coordenadas reducidas) en una región del cuadro original. */
  function candidateRegion(c, f) {
    var B = CONFIG.BLOCK;
    var x0 = c.x0 * f;
    var x1 = c.x1 * f;
    var y0 = c.y0 * f;
    var y1 = c.y1 * f;
    var padX = 2 * B * f + 0.15 * (x1 - x0);
    var padY = 2 * B * f + 0.25 * (y1 - y0);
    return {
      cx: (x0 + x1) / 2,
      cy: (y0 + y1) / 2,
      mw: x1 - x0 + 2 * padX,
      mh: y1 - y0 + 2 * padY,
      theta: c.theta,
    };
  }

  /**
   * Parámetros para dibujar una región enderezada y ampliada en un canvas:
   *   dest = translate(W/2,H/2) · rotate(-theta) · scale(scale) · translate(-cx,-cy)
   * (sx, sy, sw, sh) es el rectángulo de origen necesario, ya acotado al cuadro.
   */
  function roiTransform(cx, cy, mw, mh, theta, vw, vh) {
    var cos = Math.abs(Math.cos(theta));
    var sin = Math.abs(Math.sin(theta));
    var wr = mw * cos + mh * sin;
    var hr = mw * sin + mh * cos;
    var longSide = Math.max(wr, hr, 1);
    var scale =
      longSide < CONFIG.ROI_TARGET
        ? Math.min(4, CONFIG.ROI_TARGET / longSide)
        : Math.min(1, CONFIG.ROI_MAX / longSide);
    var W = Math.max(16, Math.round(wr * scale));
    var H = Math.max(16, Math.round(hr * scale));
    var R = 0.5 * Math.sqrt(wr * wr + hr * hr) + 2;
    var sx = Math.max(0, cx - R);
    var sy = Math.max(0, cy - R);
    var ex = Math.min(vw, cx + R);
    var ey = Math.min(vh, cy + R);
    return {
      cx: cx, cy: cy, theta: theta, scale: scale, W: W, H: H,
      sx: sx, sy: sy, sw: Math.max(1, ex - sx), sh: Math.max(1, ey - sy),
    };
  }

  /**
   * Estira los niveles entre los percentiles 2 y 98 y aplica gamma (in situ).
   * Devuelve false si la imagen no tiene contraste útil.
   */
  function stretchLevels(lum, gamma) {
    var total = lum.length;
    var hist = new Uint32Array(256);
    for (var i = 0; i < total; i++) {
      hist[lum[i]]++;
    }
    var lowCut = total * 0.02;
    var highCut = total * 0.98;
    var acc = 0;
    var lo = 0;
    var hi = 255;
    var v;
    for (v = 0; v < 256; v++) {
      acc += hist[v];
      if (acc >= lowCut) { lo = v; break; }
    }
    acc = 0;
    for (v = 0; v < 256; v++) {
      acc += hist[v];
      if (acc >= highCut) { hi = v; break; }
    }
    if (hi - lo < 12) {
      return false;
    }
    var range = hi - lo;
    var lut = new Uint8ClampedArray(256);
    for (v = 0; v < 256; v++) {
      var t = (v - lo) / range;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      if (gamma !== 1) {
        t = Math.pow(t, gamma);
      }
      lut[v] = t * 255 + 0.5;
    }
    for (var j = 0; j < total; j++) {
      lum[j] = lut[lum[j]];
    }
    return true;
  }

  /** Realce de bordes solo en horizontal (las barras son bordes verticales). */
  function sharpenHorizontal(lum, w, h, k) {
    var out = new Uint8ClampedArray(lum.length);
    for (var y = 0; y < h; y++) {
      var o = y * w;
      out[o] = lum[o];
      out[o + w - 1] = lum[o + w - 1];
      for (var x = 1; x < w - 1; x++) {
        var c = lum[o + x];
        out[o + x] = c + k * (c - 0.5 * (lum[o + x - 1] + lum[o + x + 1]));
      }
    }
    return out;
  }

  /* ------------------------------------------------------------------ */
  /* Lector                                                              */
  /* ------------------------------------------------------------------ */

  function initializeReader(root) {
    if (root.dataset.readerReady === "true") {
      return;
    }
    root.dataset.readerReady = "true";

    var usbModeButton = root.querySelector('[data-reader-mode="usb"]');
    var cameraModeButton = root.querySelector('[data-reader-mode="camera"]');
    var usbPanel = root.querySelector("[data-usb-panel]");
    var cameraPanel = root.querySelector("[data-camera-panel]");
    var requestForm = root.querySelector("[data-barcode-request]");
    var codeInput = root.querySelector("[data-barcode-input]");
    var status = root.querySelector("[data-reader-status]");
    var resultContainer = root.querySelector("[data-barcode-result-container]");
    var cameraSelect = root.querySelector("[data-camera-select]");
    var cameraStartButton = root.querySelector("[data-camera-start]");
    var cameraStopButton = root.querySelector("[data-camera-stop]");
    var video = root.querySelector("[data-camera-video]");

    if (
      !usbModeButton || !cameraModeButton || !usbPanel || !cameraPanel ||
      !requestForm || !codeInput || !status || !cameraSelect ||
      !cameraStartButton || !cameraStopButton || !video
    ) {
      console.error("[barcode] Faltan elementos en el componente:", root);
      return;
    }

    var actionMode =
      root.dataset.actionMode || (root.dataset.targetInput ? "input" : "lookup");
    var confirmReads = parseInt(root.dataset.confirmReads, 10);
    if (!(confirmReads >= 1)) {
      confirmReads = CONFIG.CONFIRM_READS;
    }
    var videoWidth = parseInt(root.dataset.videoWidth, 10) || CONFIG.VIDEO_WIDTH;
    var videoHeight = parseInt(root.dataset.videoHeight, 10) || CONFIG.VIDEO_HEIGHT;

    // Estado
    var cameraActive = false;
    var cameraStartPending = false;
    var cameraStartToken = 0;
    var overconstrainedRetried = false;
    var requestPending = false;
    var lastCameraCode = "";
    var lastCameraSeenAt = 0;
    var lastUsbCode = "";
    var lastUsbReadAt = 0;
    var audioCtx = null;

    // Motor de cámara
    var activeStream = null;
    var scanTimer = null;
    var nativeDetector = null;
    var zxingReader = null;
    var pending = { code: "", count: 0, lastAt: 0 };
    var smallCanvas = null;
    var smallCtx = null;
    var roiCanvas = null;
    var roiCtx = null;
    var tickIndex = 0;
    var fallbackIndex = 0;
    var lastCandidates = [];
    var lastProcessed = null;
    var lastTop = null; // mejor candidato del último ciclo: { cx, cy, modulePx }
    var hintAnchor = null;
    var noReadCycles = 0;
    var lastHintAt = 0;
    var stats = { ticks: 0, candidatos: 0, intentos: 0, planas: 0, lecturas: 0, errores: {} };
    var lastStatsAt = 0;

    log("init", {
      actionMode: actionMode,
      selector: root.dataset.targetInput,
      targetFound: !!resolveTargetInput(),
      confirmReads: confirmReads,
    });

    /* ---------- Campo destino ---------- */

    // Se resuelve en el momento de usarlo (no al iniciar) para tolerar formularios
    // renderizados después o ids distintos.
    function resolveTargetInput() {
      var selector = (root.dataset.targetInput || "").trim();
      if (!selector) {
        return null;
      }
      var el = null;
      try {
        el = document.querySelector(selector);
      } catch (e) {
        el = null;
      }
      if (!el) {
        el = document.getElementById(selector.replace(/^#/, ""));
      }
      return el;
    }

    function writeToTarget(target, code) {
      target.value = code;
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
      target.classList.remove("is-invalid");
      target.classList.add("is-valid");
      clearTimeout(target._cmBarcodeFlash);
      target._cmBarcodeFlash = setTimeout(function () {
        target.classList.remove("is-valid");
      }, 3000);
    }

    /* ---------- Feedback ---------- */

    function primeAudio() {
      // Debe llamarse dentro de un gesto del usuario (clic) para que Chrome permita
      // reproducir el beep después, desde el bucle de la cámara.
      try {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === "suspended") {
          audioCtx.resume();
        }
      } catch (e) {
        audioCtx = null;
      }
    }

    function playSuccessBeep() {
      try {
        primeAudio();
        if (!audioCtx) {
          return;
        }
        var osc = audioCtx.createOscillator();
        var gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.15);
      } catch (e) {
        // El audio no es esencial.
      }
    }

    function setStatus(message, state) {
      status.textContent = message;
      status.dataset.state = state || "idle";
    }

    function renderAssignedCard(code) {
      if (!resultContainer) {
        return;
      }
      var card = document.createElement("div");
      card.className = "barcode-reader__result-card is-found";
      card.setAttribute("data-barcode-result", "");
      card.dataset.state = "encontrado";
      card.dataset.code = code;

      var title = document.createElement("strong");
      title.textContent = "Código asignado: " + code;
      var detail = document.createElement("span");
      detail.textContent =
        "El código fue ingresado en el formulario del producto. Puedes continuar completando los datos.";

      card.appendChild(title);
      card.appendChild(detail);
      resultContainer.replaceChildren(card);
    }

    /* ---------- Modos ---------- */

    function updateMode(mode) {
      var usbActive = mode === "usb";
      usbModeButton.classList.toggle("is-active", usbActive);
      cameraModeButton.classList.toggle("is-active", !usbActive);
      usbModeButton.setAttribute("aria-pressed", String(usbActive));
      cameraModeButton.setAttribute("aria-pressed", String(!usbActive));
      usbPanel.hidden = !usbActive;
      cameraPanel.hidden = usbActive;

      if (usbActive) {
        stopCamera();
        setStatus("Modo USB listo. Selecciona el campo y escanea un producto.");
      } else {
        loadCameras();
      }
    }

    /* ---------- Procesamiento de un código (USB y cámara) ---------- */

    function assignToTarget(code, source) {
      var target = resolveTargetInput();
      if (!target) {
        console.error(
          "[barcode] Campo destino no encontrado:",
          root.dataset.targetInput
        );
        setStatus(
          "Código " + code + " leído, pero no se encontró el campo destino (" +
            root.dataset.targetInput + ").",
          "error"
        );
        return;
      }

      writeToTarget(target, code);
      log("asignado", code, "->", target);
      renderAssignedCard(code);

      root.dispatchEvent(
        new CustomEvent("barcode:assigned", {
          bubbles: true,
          detail: { code: code, source: source, target: target },
        })
      );

      if (source === "camera" && root.dataset.stopAfterRead === "true") {
        stopCamera();
        setStatus("Código " + code + " asignado. Cámara detenida.", "encontrado");
      } else {
        setStatus(
          "Código detectado: " + code + ". Ingresado en el campo de código de barras.",
          "encontrado"
        );
      }
    }

    function submitBarcode(value, source) {
      var code = String(value || "").trim();
      if (!code) {
        setStatus("No se recibió ningún código. Intenta escanear nuevamente.", "error");
        return;
      }
      if (actionMode !== "input" && requestPending) {
        return;
      }
      if (
        source === "usb" &&
        code === lastUsbCode &&
        Date.now() - lastUsbReadAt < CONFIG.USB_DUPLICATE_MS
      ) {
        return;
      }
      if (
        source === "camera" &&
        code === lastCameraCode &&
        Date.now() - lastCameraSeenAt < CONFIG.CAMERA_DUPLICATE_MS
      ) {
        return;
      }

      if (source === "usb") {
        lastUsbCode = code;
        lastUsbReadAt = Date.now();
      } else {
        lastCameraCode = code;
        lastCameraSeenAt = Date.now();
      }

      playSuccessBeep();

      if (actionMode === "input") {
        assignToTarget(code, source);
        return;
      }

      setStatus("Código detectado: " + code + ". Consultando inventario...", "loading");
      codeInput.value = code;
      if (typeof requestForm.requestSubmit === "function") {
        requestForm.requestSubmit();
      } else {
        requestForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      }
      codeInput.value = "";
    }

    /* ---------- Respuesta HTMX (solo modo lookup) ---------- */

    function readResult(event) {
      if (actionMode === "input") {
        return;
      }
      if (!resultContainer || event.detail.target !== resultContainer) {
        return;
      }

      var result = resultContainer.querySelector("[data-barcode-result]");
      if (!result) {
        return;
      }

      requestPending = false;
      var state = result.dataset.state;
      var code = result.dataset.code || "";
      setStatus(result.dataset.message || result.textContent.trim(), state);

      var target = resolveTargetInput();
      if (state !== "invalido" && target) {
        writeToTarget(target, code);
      }

      var detail = { code: code, state: state };

      if (state === "encontrado") {
        detail.product = {
          id: result.dataset.productId,
          name: result.dataset.productName,
          barcode: result.dataset.productBarcode,
          category: result.dataset.category,
          unitStock: result.dataset.unitStock,
          weightStock: result.dataset.weightStock,
          price: result.dataset.price,
        };
        root.dispatchEvent(
          new CustomEvent("barcode:product-found", { bubbles: true, detail: detail })
        );
      } else if (state === "no_encontrado") {
        root.dispatchEvent(
          new CustomEvent("barcode:product-not-found", { bubbles: true, detail: detail })
        );
      } else {
        lastCameraCode = "";
        root.dispatchEvent(
          new CustomEvent("barcode:invalid", { bubbles: true, detail: detail })
        );
      }

      root.dispatchEvent(
        new CustomEvent("barcode:processed", { bubbles: true, detail: detail })
      );
    }

    function requestFailed(event) {
      if (actionMode === "input") {
        return;
      }
      var requestElement = event.detail.elt || event.target;
      if (requestElement !== requestForm) {
        return;
      }

      requestPending = false;
      lastCameraCode = "";
      setStatus(
        "No se pudo consultar el código. Revisa la conexión e intenta nuevamente.",
        "error"
      );
    }

    /* ---------- Cámaras ---------- */

    function mediaUnavailableMessage() {
      return window.isSecureContext
        ? "Tu navegador no soporta acceso a la cámara."
        : "La cámara requiere localhost o una conexión HTTPS segura.";
    }

    async function populateCamerasSilently() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        return;
      }
      try {
        var devices = await navigator.mediaDevices.enumerateDevices();
        var videoDevices = devices.filter(function (d) {
          return d.kind === "videoinput";
        });
        if (videoDevices.length === 0) {
          return;
        }
        var wanted = cameraSelect.value || storageGet(CONFIG.CAMERA_STORAGE_KEY) || "";
        cameraSelect.replaceChildren();
        cameraSelect.add(new Option("Cámara predeterminada", ""));
        videoDevices.forEach(function (device, index) {
          cameraSelect.add(
            new Option(device.label || "Cámara " + (index + 1), device.deviceId)
          );
        });
        if (
          wanted &&
          Array.from(cameraSelect.options).some(function (o) {
            return o.value === wanted;
          })
        ) {
          cameraSelect.value = wanted;
        }
        cameraSelect.disabled = false;
      } catch (e) {
        // Silencioso: los permisos pueden no haberse otorgado aún.
      }
    }

    function loadCameras() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus(mediaUnavailableMessage(), "error");
        return;
      }
      setStatus(
        "Modo cámara listo. Pulsa «Activar cámara» para conceder permisos y comenzar."
      );
      cameraStartButton.disabled = false;
      cameraStartButton.hidden = false;
      cameraStopButton.hidden = true;
      populateCamerasSilently();
    }

    /* ---------- Motor de lectura por cámara ---------- */

    function noteDecodeError(error) {
      var key =
        (error && (error.name || (error.constructor && error.constructor.name))) ||
        "desconocido";
      stats.errores[key] = (stats.errores[key] || 0) + 1;
    }

    function printStats() {
      if (!debugEnabled()) {
        return;
      }
      var now = Date.now();
      if (now - lastStatsAt < 3000) {
        return;
      }
      lastStatsAt = now;
      console.log(
        "[barcode] ciclos=" + stats.ticks +
          " candidatos=" + stats.candidatos +
          " intentos=" + stats.intentos +
          " sin_contraste=" + stats.planas +
          " lecturas=" + stats.lecturas +
          " px_por_barra≈" + (lastTop ? lastTop.modulePx.toFixed(1) : "-"),
        JSON.stringify(stats.errores)
      );
    }

    function buildZXingReader() {
      var Z = window.ZXing;
      var BarcodeFormat = zxingExport("BarcodeFormat");
      var DecodeHintType = zxingExport("DecodeHintType");
      if (
        !Z || !Z.MultiFormatReader || !Z.BinaryBitmap || !Z.HybridBinarizer ||
        !Z.RGBLuminanceSource || !BarcodeFormat || !DecodeHintType
      ) {
        return null;
      }
      var hints = new Map();
      // Diagnóstico: window.cmBarcodeAllFormats = true quita la restricción a EAN/UPC.
      if (window.cmBarcodeAllFormats !== true) {
        hints.set(DecodeHintType.POSSIBLE_FORMATS, [
          BarcodeFormat.EAN_13,
          BarcodeFormat.EAN_8,
          BarcodeFormat.UPC_A,
          BarcodeFormat.UPC_E,
        ]);
      }
      hints.set(DecodeHintType.TRY_HARDER, true);
      var mfr = new Z.MultiFormatReader();
      mfr.setHints(hints);
      return mfr;
    }

    async function buildNativeDetector() {
      if (!("BarcodeDetector" in window)) {
        return null;
      }
      try {
        var supported = await window.BarcodeDetector.getSupportedFormats();
        var wanted = ["ean_13", "ean_8", "upc_a", "upc_e"].filter(function (f) {
          return supported.indexOf(f) !== -1;
        });
        if (!wanted.length) {
          return null;
        }
        return new window.BarcodeDetector({ formats: wanted });
      } catch (e) {
        return null;
      }
    }

    function ensureCanvases() {
      if (!smallCanvas) {
        smallCanvas = document.createElement("canvas");
        smallCtx = smallCanvas.getContext("2d", { willReadFrequently: true });
        roiCanvas = document.createElement("canvas");
        roiCtx = roiCanvas.getContext("2d", { willReadFrequently: true });
      }
    }

    /** Imagen reducida en gris para localizar (barata: ~640 px de ancho). */
    function grabSmall(src, sw, sh) {
      ensureCanvases();
      var w = Math.min(CONFIG.LOC_WIDTH, sw);
      var h = Math.max(8, Math.round((w * sh) / sw));
      if (smallCanvas.width !== w || smallCanvas.height !== h) {
        smallCanvas.width = w;
        smallCanvas.height = h;
      }
      smallCtx.imageSmoothingEnabled = true;
      smallCtx.imageSmoothingQuality = "high";
      smallCtx.drawImage(src, 0, 0, sw, sh, 0, 0, w, h);
      var data = smallCtx.getImageData(0, 0, w, h).data;
      return { gray: rgbaToGray(data), w: w, h: h, f: sw / w };
    }

    /** Dibuja la región enderezada y ampliada y devuelve su luminancia cruda. */
    function grabRegion(src, tf) {
      ensureCanvases();
      if (roiCanvas.width !== tf.W || roiCanvas.height !== tf.H) {
        roiCanvas.width = tf.W;
        roiCanvas.height = tf.H;
      }
      roiCtx.setTransform(1, 0, 0, 1, 0, 0);
      roiCtx.fillStyle = "#fff";
      roiCtx.fillRect(0, 0, tf.W, tf.H);
      roiCtx.imageSmoothingEnabled = true;
      roiCtx.imageSmoothingQuality = "high";
      roiCtx.translate(tf.W / 2, tf.H / 2);
      roiCtx.rotate(-tf.theta);
      roiCtx.scale(tf.scale, tf.scale);
      roiCtx.drawImage(
        src,
        tf.sx, tf.sy, tf.sw, tf.sh,
        tf.sx - tf.cx, tf.sy - tf.cy, tf.sw, tf.sh
      );
      roiCtx.setTransform(1, 0, 0, 1, 0, 0);
      return rgbaToGray(roiCtx.getImageData(0, 0, tf.W, tf.H).data);
    }

    function decodeLuma(lum, w, h, binarizer) {
      var Z = window.ZXing;
      var source = new Z.RGBLuminanceSource(lum, w, h);
      var bin =
        binarizer === "global" && Z.GlobalHistogramBinarizer
          ? new Z.GlobalHistogramBinarizer(source)
          : new Z.HybridBinarizer(source);
      try {
        var result = zxingReader.decodeWithState(new Z.BinaryBitmap(bin));
        var text = String(result.getText() || "").trim();
        if (!text) {
          return null;
        }
        var BarcodeFormat = zxingExport("BarcodeFormat");
        var fmt = result.getBarcodeFormat();
        return { text: text, format: (BarcodeFormat && BarcodeFormat[fmt]) || fmt };
      } catch (e) {
        noteDecodeError(e);
        return null;
      }
    }

    /**
     * Un ciclo de lectura sobre `src` (video o imagen): localiza, recorta y decodifica.
     * Devuelve { text, format } o null.
     */
    function scanSource(src, sw, sh) {
      if (!zxingReader) {
        return null;
      }
      var t0 = performance.now();
      tickIndex += 1;
      stats.ticks += 1;

      var small = grabSmall(src, sw, sh);
      var candidates = localizeBarcodes(small.gray, small.w, small.h);
      stats.candidatos += candidates.length;
      // Resolución estimada: un EAN-13 tiene 95 módulos; ZXing necesita ~2 px por módulo.
      if (candidates.length) {
        var top = candidates[0];
        lastTop = {
          cx: ((top.x0 + top.x1) / 2) * small.f,
          cy: ((top.y0 + top.y1) / 2) * small.f,
          modulePx: (Math.max(top.x1 - top.x0, top.y1 - top.y0) * small.f) / 95,
        };
      } else {
        lastTop = null;
      }
      lastCandidates = candidates.map(function (c) {
        return {
          x0: c.x0 * small.f, y0: c.y0 * small.f,
          x1: c.x1 * small.f, y1: c.y1 * small.f,
        };
      });

      // Lista de intentos de este ciclo (el mejor candidato recibe dos variantes).
      var attempts = [];
      var n = COMBOS.length;
      candidates.slice(0, 2).forEach(function (c, index) {
        var region = candidateRegion(c, small.f);
        attempts.push({ region: region, combo: COMBOS[0], key: "c" + index });
        if (index === 0) {
          attempts.push({
            region: region,
            combo: COMBOS[1 + (tickIndex % (n - 1))],
            key: "c0",
          });
        }
      });
      if (!candidates.length || tickIndex % 4 === 0) {
        var fb = FALLBACK_REGIONS[fallbackIndex++ % FALLBACK_REGIONS.length];
        attempts.push({
          region: {
            cx: sw * fb[0], cy: sh * fb[1], mw: sw * fb[2], mh: sh * fb[3], theta: 0,
          },
          combo: COMBOS[0],
          key: "fb",
        });
      }

      var raw = null;
      var rawKey = "";
      for (var a = 0; a < attempts.length; a++) {
        var att = attempts[a];
        var r = att.region;
        var tf = roiTransform(r.cx, r.cy, r.mw, r.mh, r.theta + att.combo.jitter, sw, sh);
        var key = att.key + "|" + att.combo.jitter;
        if (key !== rawKey) {
          raw = grabRegion(src, tf);
          rawKey = key;
        }

        // Segunda pasada de ángulo: en la imagen reducida los módulos miden ~1 px y la
        // orientación sale con varios grados de error. En el recorte ampliado se mide bien.
        if (!r.refined && att.key !== "fb") {
          var tiltDeg = Math.abs(((r.theta / DEG) % 90 + 90) % 90);
          tiltDeg = Math.min(tiltDeg, 90 - tiltDeg);
          r.refined = true;
          if (tiltDeg > 2) {
            var half = halveGray(raw, tf.W, tf.H);
            var fine = localizeBarcodes(half.gray, half.w, half.h);
            if (fine.length) {
              var delta = fine[0].theta;
              if (Math.abs(delta) > 0.8 * DEG && Math.abs(delta) < 20 * DEG) {
                r.theta += delta;
                tf = roiTransform(r.cx, r.cy, r.mw, r.mh, r.theta + att.combo.jitter, sw, sh);
                raw = grabRegion(src, tf);
                rawKey = key;
              }
            }
          }
        }
        var lum = raw.slice();
        if (!stretchLevels(lum, att.combo.gamma)) {
          stats.planas += 1;
          continue;
        }
        if (att.combo.sharpen) {
          lum = sharpenHorizontal(lum, tf.W, tf.H, 1.2);
        }
        lastProcessed = { lum: lum, w: tf.W, h: tf.H };
        stats.intentos += 1;
        var hit = decodeLuma(lum, tf.W, tf.H, att.combo.binarizer);
        if (hit) {
          stats.lecturas += 1;
          log("ZXing leyó:", hit.text, hit.format, "zona:", att.key, "variante:", att.combo);
          return hit;
        }
        if (performance.now() - t0 > CONFIG.TIME_BUDGET_MS) {
          break;
        }
      }
      return null;
    }

    async function scanNative() {
      try {
        var codes = await nativeDetector.detect(video);
        return codes && codes.length ? String(codes[0].rawValue || "").trim() : "";
      } catch (e) {
        log("BarcodeDetector falló, se desactiva:", e);
        nativeDetector = null;
        return "";
      }
    }

    /**
     * Lógica de aceptación: mientras el mismo código siga a la vista no se repite;
     * un código nuevo debe verse `confirmReads` veces seguidas (BarcodeDetector: 1).
     */
    function onCameraSighting(text, engine) {
      var now = Date.now();
      if (text === lastCameraCode && now - lastCameraSeenAt < CONFIG.CAMERA_DUPLICATE_MS) {
        lastCameraSeenAt = now; // sigue a la vista: no volver a disparar
        return;
      }
      var needed = engine === "native" ? 1 : confirmReads;
      if (pending.code === text && now - pending.lastAt <= CONFIG.CONFIRM_WINDOW_MS) {
        pending.count += 1;
      } else {
        pending = { code: text, count: 1, lastAt: now };
      }
      pending.lastAt = now;

      if (pending.count >= needed) {
        pending = { code: "", count: 0, lastAt: 0 };
        submitBarcode(text, "camera");
      } else {
        setStatus("Código visto: " + text + ". Confirmando lectura...", "loading");
      }
    }

    // Si una zona con aspecto de código sigue en el mismo sitio sin poder leerse, dice por qué.
    function trackUnreadCode(found) {
      if (found) {
        noReadCycles = 0;
        hintAnchor = null;
        return;
      }
      if (!lastTop) {
        noReadCycles = 0;
        hintAnchor = null;
        return;
      }
      if (
        hintAnchor &&
        Math.hypot(lastTop.cx - hintAnchor.cx, lastTop.cy - hintAnchor.cy) < 60
      ) {
        noReadCycles += 1;
      } else {
        hintAnchor = lastTop;
        noReadCycles = 1;
      }

      var now = Date.now();
      if (
        noReadCycles < 15 || now - lastHintAt < 3000 ||
        requestPending || pending.count > 0
      ) {
        return;
      }
      lastHintAt = now;
      var px = lastTop.modulePx;
      var approx = "≈" + px.toFixed(1) + " px por barra";
      var message;
      if (px < 1.4) {
        message =
          "Posible código demasiado pequeño para leerlo (" + approx +
          "; se necesitan ~2). Acércalo mientras siga nítido.";
      } else if (px < 2) {
        message =
          "Posible código con muy poca resolución (" + approx +
          "). Acércalo un poco o mejora la luz.";
      } else {
        message =
          "Posible código detectado (" + approx +
          ") pero no se logra leer. Revisa nitidez, reflejos e inclinación.";
      }
      setStatus(message);
    }

    function startScanLoop(token) {
      async function tick() {
        if (token !== cameraStartToken || !activeStream) {
          return;
        }
        var t0 = performance.now();
        try {
          if (video.readyState >= 2 && video.videoWidth) {
            var found = null;
            if (nativeDetector) {
              var nativeText = await scanNative();
              if (nativeText) {
                found = { text: nativeText, engine: "native" };
              }
            }
            if (!found && zxingReader) {
              var hit = scanSource(video, video.videoWidth, video.videoHeight);
              if (hit) {
                found = { text: hit.text, engine: "zxing" };
              }
            }
            trackUnreadCode(!!found);
            if (found && token === cameraStartToken) {
              onCameraSighting(found.text, found.engine);
            }
          }
        } catch (error) {
          noteDecodeError(error);
          log("error en el ciclo de lectura:", error);
        }
        printStats();
        if (token === cameraStartToken && activeStream) {
          var spent = performance.now() - t0;
          scanTimer = setTimeout(tick, Math.max(10, CONFIG.TICK_MS - spent));
        }
      }
      tick();
    }

    function tuneTrack(stream) {
      var track = stream.getVideoTracks()[0];
      if (!track || !track.getCapabilities) {
        return;
      }
      var caps = track.getCapabilities();
      log("cámara:", track.label, track.getSettings(), caps);
      // Enfoque, exposición y balance de blancos continuos: ayudan con luz cambiante.
      var advanced = {};
      ["focusMode", "exposureMode", "whiteBalanceMode"].forEach(function (key) {
        if (caps[key] && caps[key].indexOf("continuous") !== -1) {
          advanced[key] = "continuous";
        }
      });
      if (Object.keys(advanced).length) {
        track.applyConstraints({ advanced: [advanced] }).catch(function (e) {
          log("applyConstraints rechazado:", e);
        });
      }
    }

    function releaseStream() {
      clearTimeout(scanTimer);
      scanTimer = null;
      stopTracks(activeStream);
      activeStream = null;
      stopTracks(video.srcObject);
      video.srcObject = null;
    }

    async function startCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus(mediaUnavailableMessage(), "error");
        return;
      }

      primeAudio();
      setStatus("Solicitando acceso a la cámara...", "loading");
      cameraStartButton.disabled = true;
      video.hidden = false;
      video.muted = true;
      video.setAttribute("playsinline", "");
      cameraStartPending = true;
      var startToken = ++cameraStartToken;

      try {
        releaseStream();

        // Sin facingMode: pensado para webcams de escritorio y laptops.
        var constraints = {
          width: { ideal: videoWidth },
          height: { ideal: videoHeight },
        };
        if (cameraSelect.value) {
          constraints.deviceId = { exact: cameraSelect.value };
        }

        var stream = await navigator.mediaDevices.getUserMedia({ video: constraints });
        if (startToken !== cameraStartToken) {
          stopTracks(stream);
          cameraStartPending = false;
          return;
        }
        activeStream = stream;

        await populateCamerasSilently();
        tuneTrack(stream);

        video.srcObject = stream;
        await video.play();
        if (startToken !== cameraStartToken) {
          cameraStartPending = false;
          return;
        }

        nativeDetector = await buildNativeDetector();
        zxingReader = buildZXingReader();
        if (!nativeDetector && !zxingReader) {
          throw new Error(
            "No se cargó la librería ZXing (zxing-library debe cargarse antes que zxing-browser)."
          );
        }

        tickIndex = 0;
        fallbackIndex = 0;
        lastTop = null;
        hintAnchor = null;
        noReadCycles = 0;
        pending = { code: "", count: 0, lastAt: 0 };
        stats = { ticks: 0, candidatos: 0, intentos: 0, planas: 0, lecturas: 0, errores: {} };
        log("motor:", nativeDetector ? "BarcodeDetector + ZXing" : "ZXing", {
          video: video.videoWidth + "x" + video.videoHeight,
        });

        if (cameraSelect.value) {
          storageSet(CONFIG.CAMERA_STORAGE_KEY, cameraSelect.value);
        }

        cameraStartPending = false;
        cameraActive = true;
        overconstrainedRetried = false;
        cameraStartButton.disabled = false;
        cameraStartButton.hidden = true;
        cameraStopButton.hidden = false;
        setStatus(
          "Cámara activa. Muestra el código con buena luz; no necesita ocupar toda la imagen."
        );
        startScanLoop(startToken);
      } catch (error) {
        if (startToken !== cameraStartToken) {
          return;
        }
        cameraStartPending = false;
        stopCamera();
        cameraStartButton.disabled = false;
        cameraStartButton.hidden = false;
        cameraStopButton.hidden = true;
        console.error("[barcode] Error al iniciar la cámara:", error);

        if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
          setStatus(
            "Permiso denegado para usar la cámara. Permite el acceso en el ícono de candado del navegador.",
            "error"
          );
        } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
          setStatus("No se encontró una cámara disponible en este computador.", "error");
        } else if (error.name === "NotReadableError" || error.name === "TrackStartError") {
          setStatus(
            "La cámara está en uso por otra aplicación. Ciérrala e intenta nuevamente.",
            "error"
          );
        } else if (error.name === "OverconstrainedError" && !overconstrainedRetried) {
          overconstrainedRetried = true;
          cameraSelect.value = "";
          setStatus("Ajustando cámara predeterminada...", "loading");
          setTimeout(startCamera, 300);
        } else {
          setStatus(
            "Error al iniciar la cámara: " + (error.message || error.name),
            "error"
          );
        }
      }
    }

    function stopCamera() {
      cameraStartToken += 1;
      cameraStartPending = false;
      releaseStream();
      cameraActive = false;
      cameraStartButton.disabled = false;
      cameraStartButton.hidden = false;
      cameraStopButton.hidden = true;
      video.hidden = true;
    }

    /* ---------- Diagnóstico ---------- */

    function grayToCanvas(lum, w, h) {
      var canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      var ctx = canvas.getContext("2d");
      var image = ctx.createImageData(w, h);
      for (var i = 0, j = 0; i < lum.length; i++, j += 4) {
        image.data[j] = image.data[j + 1] = image.data[j + 2] = lum[i];
        image.data[j + 3] = 255;
      }
      ctx.putImageData(image, 0, 0);
      return canvas;
    }

    // Muestra el cuadro actual con las zonas localizadas y lo que recibe ZXing.
    function showSnapshot() {
      if (!video.videoWidth) {
        console.error("[barcode] La cámara no está activa o aún no entrega video.");
        return;
      }
      var old = document.getElementById("cm-barcode-snapshot");
      if (old) {
        old.remove();
      }
      var wrap = document.createElement("div");
      wrap.id = "cm-barcode-snapshot";
      wrap.style.cssText =
        "position:fixed;right:12px;bottom:12px;z-index:99999;background:#fff;color:#000;" +
        "border:2px solid #333;padding:6px;box-shadow:0 4px 16px rgba(0,0,0,.4);" +
        "max-width:90vw;max-height:92vh;overflow:auto;cursor:pointer;font:12px sans-serif";

      var frame = document.createElement("canvas");
      frame.width = video.videoWidth;
      frame.height = video.videoHeight;
      var ctx = frame.getContext("2d");
      ctx.drawImage(video, 0, 0);
      ctx.strokeStyle = "#00e000";
      ctx.lineWidth = Math.max(2, frame.width / 300);
      lastCandidates.forEach(function (c) {
        ctx.strokeRect(c.x0, c.y0, c.x1 - c.x0, c.y1 - c.y0);
      });
      frame.style.cssText = "display:block;width:min(640px,85vw);height:auto";
      wrap.appendChild(frame);

      var caption = document.createElement("div");
      caption.textContent =
        "Cuadro " + video.videoWidth + "x" + video.videoHeight +
        " — verde: zonas localizadas (" + lastCandidates.length + ")";
      wrap.appendChild(caption);

      if (lastProcessed) {
        var proc = grayToCanvas(lastProcessed.lum, lastProcessed.w, lastProcessed.h);
        proc.style.cssText = "display:block;width:min(640px,85vw);height:auto;margin-top:6px;border:1px solid #888";
        wrap.appendChild(proc);
        var cap2 = document.createElement("div");
        cap2.textContent =
          "Último recorte que recibió ZXing (" + lastProcessed.w + "x" + lastProcessed.h +
          "). Clic para cerrar.";
        wrap.appendChild(cap2);
      }

      wrap.addEventListener("click", function () {
        wrap.remove();
      });
      document.body.appendChild(wrap);
    }

    // Prueba el motor completo con una imagen estática (sin webcam).
    function testImage(url) {
      return new Promise(function (resolve) {
        if (!zxingReader) {
          zxingReader = buildZXingReader();
        }
        if (!zxingReader) {
          console.error("[barcode] ZXing no está cargado.");
          resolve("");
          return;
        }
        var img = new Image();
        img.onload = function () {
          var found = null;
          for (var i = 0; i < 16 && !found; i++) {
            found = scanSource(img, img.naturalWidth, img.naturalHeight);
          }
          console.log(
            "[barcode] prueba con imagen:",
            found ? found.text + " (" + found.format + ")" : "NO SE PUDO LEER",
            { ancho: img.naturalWidth, alto: img.naturalHeight, zonas: lastCandidates.length }
          );
          resolve(found ? found.text : "");
        };
        img.onerror = function () {
          console.error("[barcode] No se pudo cargar la imagen:", url);
          resolve("");
        };
        img.src = url;
      });
    }

    /* ---------- Eventos de la interfaz ---------- */

    requestForm.addEventListener("submit", function (event) {
      var code = codeInput.value.trim();
      if (!code) {
        event.preventDefault();
        setStatus("Escanea un código antes de procesarlo.", "error");
        return;
      }
      if (actionMode === "input") {
        event.preventDefault();
        codeInput.value = "";
        submitBarcode(code, "usb");
        return;
      }
      if (requestPending) {
        event.preventDefault();
        return;
      }

      requestPending = true;
      setStatus("Consultando el código en el inventario...", "loading");
    });

    // Lector USB: emula un teclado y termina con Enter.
    codeInput.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      var code = codeInput.value;
      if (actionMode === "input") {
        codeInput.value = "";
      }
      submitBarcode(code, "usb");
    });

    codeInput.addEventListener("focus", function () {
      setStatus("Lector USB activo. Escanea un código y espera el Enter final.");
    });

    usbModeButton.addEventListener("click", function () {
      updateMode("usb");
      codeInput.focus();
    });
    cameraModeButton.addEventListener("click", function () {
      stopCamera();
      updateMode("camera");
    });
    cameraStartButton.addEventListener("click", startCamera);
    cameraSelect.addEventListener("change", function () {
      if (cameraSelect.value) {
        storageSet(CONFIG.CAMERA_STORAGE_KEY, cameraSelect.value);
      } else {
        storageSet(CONFIG.CAMERA_STORAGE_KEY, "");
      }
      if (cameraActive) {
        startCamera();
      }
    });
    cameraStopButton.addEventListener("click", function () {
      stopCamera();
      setStatus("Cámara detenida.");
    });

    document.body.addEventListener("htmx:afterSwap", readResult);
    document.body.addEventListener("htmx:sendError", requestFailed);
    document.body.addEventListener("htmx:responseError", requestFailed);
    document.addEventListener("visibilitychange", function () {
      if (document.hidden && (cameraActive || cameraStartPending)) {
        stopCamera();
      }
    });
    window.addEventListener("pagehide", stopCamera);

    var api = {
      root: root,
      submit: submitBarcode,
      startCamera: startCamera,
      stopCamera: stopCamera,
      isCameraActive: function () {
        return cameraActive;
      },
      snapshot: showSnapshot,
      testImage: testImage,
    };
    root.barcodeReader = api;
    readers.push(api);
  }

  function initAllBarcodeReaders() {
    document.querySelectorAll("[data-barcode-reader]").forEach(initializeReader);
  }

  // Prueba sin cámara: cmBarcodeTest("7801234567894") debe escribir en el campo destino.
  window.cmBarcodeTest = function (code) {
    if (!readers.length) {
      console.error("[barcode] No hay ningún lector inicializado en esta página.");
      return;
    }
    readers[0].submit(String(code || "7801234567894"), "camera");
  };

  window.cmBarcodeSnapshot = function () {
    if (readers.length) {
      readers[0].snapshot();
    }
  };

  window.cmBarcodeTestImage = function (url) {
    return readers.length ? readers[0].testImage(url) : Promise.resolve("");
  };

  // Funciones puras expuestas solo para pruebas automáticas.
  window.cmBarcodeInternals = {
    CONFIG: CONFIG,
    localizeBarcodes: localizeBarcodes,
    candidateRegion: candidateRegion,
    roiTransform: roiTransform,
    stretchLevels: stretchLevels,
    sharpenHorizontal: sharpenHorizontal,
    rgbaToGray: rgbaToGray,
    halveGray: halveGray,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAllBarcodeReaders);
  } else {
    initAllBarcodeReaders();
  }
})();