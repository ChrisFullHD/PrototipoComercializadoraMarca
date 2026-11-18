# Sistema de Gestión de Ventas e Inventario para Comercializadora Marca

## Integrantes y usuarios de github

- **Giovanni Alexis Gómez Carrasco:** strx177, StrX22
- **Joaquín Alejandro Guarachi Gaspar:** JoakoGG
- **Christian Matías Alexander Mollo Quispe:** ChrisFullHD

## Descripción del proyecto

El proyecto consiste en el desarrollo de un sistema web interno para **Comercializadora Marca**, un negocio dedicado principalmente a la venta minorista de productos. Su objetivo es centralizar la información del negocio y facilitar la administración de sus operaciones, especialmente el control del inventario, que actualmente se realiza mediante inspecciones visuales y registros manuales.

La aplicación permite gestionar los productos y sus existencias, registrar ventas, controlar las operaciones pendientes de pago y mantener actualizada la información relacionada con los movimientos del inventario. Además, incorpora herramientas para administrar proveedores, consultar estadísticas, generar reportes y gestionar los usuarios que tienen acceso al sistema.

## Apartados principales de la aplicación

1. **Inventario:** Permite registrar, modificar, buscar y consultar productos, controlar las existencias, identificar productos con bajo stock y gestionar artículos comercializados por peso y mediante códigos de barras.

2. **Ventas/Fiados:** Permite registrar ventas, agregar productos, calcular los montos correspondientes y descontar automáticamente las unidades vendidas del inventario. Además, contempla el registro y seguimiento de las ventas que quedan pendientes de pago.

3. **Devolución/Bajas:** Permite registrar devoluciones de productos y actualizar las existencias correspondientes. También contempla el registro de productos vencidos, dañados o que deben retirarse del inventario.

4. **Notificaciones:** Permite informar sobre situaciones relevantes para la administración del negocio, especialmente productos con bajo stock y próximos a vencer.

5. **Proveedores:** Permite registrar y consultar información de contacto de los proveedores para facilitar las gestiones relacionadas con la reposición de productos.

6. **Estadísticas/Reportes:** Permite consultar información sobre las ventas, los ingresos y los productos con mayor rotación. Además, permite generar y exportar reportes periódicos de ventas e inventario.

7. **Facturas:** Permite registrar y consultar información relacionada con las facturas del negocio mediante un apartado de estructura sencilla.

8. **Usuarios:** Permite administrar las cuentas de acceso al sistema y establecer permisos según los roles definidos. Contempla dos roles principales: administrador y empleado.

9. **Respaldos:** Permite crear y guardar respaldos de la base de datos en la nube.

## Tecnologías utilizadas

El sistema utiliza **Python y Django** como framework principal, **HTMX** para incorporar interactividad en las interfaces y **SQLite** como sistema de gestión de base de datos. Su funcionamiento se orienta al computador disponible en el negocio, utilizando almacenamiento local y considerando mecanismos complementarios de respaldo de información.

## Gestores

| App                   | Modelos                                                                       | HU                                                          | Responsable      | Rama              |
| --------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------------- | ----------------- |
| Inventario            | Producto, Producto_Peso, Producto_Unitario, Categoria, Movimientos_Inventario | HU01, HU02, HU03, HU04, HU05, HU06, HU07, HU08              | Joaquín Guarachi | feature/jguarachi |
| Ventas/Fiados         | Venta, Detalle_Venta                                                          | HU09, HU10, HU11, HU12, HU13, HU14, HU15, HU16, HU17        | Joaquín Guarachi | feature/jguarachi |
| Devolución/Bajas      | Devolucion                                                                    | HU18, HU19, HU20, HU21                                      | Giovanni Gómez   | feature/ggomez    |
| Notificaciones        | Notificacion\*                                                                | HU22                                                        | Christian Mollo  | feature/cmollo    |
| Proveedores           | Proveedor                                                                     | HU23, HU24                                                  | Christian Mollo  | feature/cmollo    |
| Estadísticas/Reportes | Reporte                                                                       | HU25, HU26, HU27, HU28, HU29, HU30                          | Giovanni Gómez   | feature/ggomez    |
| Facturas              | Factura\*                                                                     | Sin HU asociadas (Considerado en retroalimentación cliente) | Christian Mollo  | feature/cmollo    |
| Usuarios              | Usuario, Rol                                                                  | Sin HU asociadas                                            | Joaquín Guarachi | feature/jguarachi |
| Respaldos             | Respaldo\*                                                                    | Sin HU asociadas                                            | Giovanni Gómez   | feature/ggomez    |

## Historias de usuario

| HU    | Descripción                                               |
| ----- | --------------------------------------------------------- |
| HU-01 | Registrar productos                                       |
| HU-02 | Modificar información de productos                        |
| HU-03 | Asociar códigos de barras a productos                     |
| HU-04 | Consultar stock de productos                              |
| HU-05 | Buscar productos registrados                              |
| HU-06 | Consultar disponibilidad de productos                     |
| HU-07 | Consultar movimientos del inventario                      |
| HU-08 | Registrar fechas de vencimiento                           |
| HU-09 | Escanear códigos de barras durante una venta              |
| HU-10 | Registrar ventas                                          |
| HU-11 | Agregar productos a una venta                             |
| HU-12 | Calcular el total de una venta                            |
| HU-13 | Descontar automáticamente el stock al completar una venta |
| HU-14 | Registrar productos vendidos por peso                     |
| HU-15 | Calcular el precio de productos vendidos por peso         |
| HU-16 | Registrar ventas fiadas                                   |
| HU-17 | Mantener registro de ventas pendientes de pago            |
| HU-18 | Registrar devoluciones de productos                       |
| HU-19 | Actualizar el stock después de una devolución             |
| HU-20 | Dar de baja productos                                     |
| HU-21 | Registrar la baja de productos vencidos                   |
| HU-22 | Generar alertas de productos próximos a vencer            |
| HU-23 | Registrar proveedores                                     |
| HU-24 | Consultar información de contacto de proveedores          |
| HU-25 | Consultar historial de ventas                             |
| HU-26 | Identificar productos con mayor rotación                  |
| HU-27 | Consultar estadísticas de ventas                          |
| HU-28 | Consultar ingresos por período                            |
| HU-29 | Generar reportes mensuales de ventas e inventario         |
| HU-30 | Exportar reportes en formato de planilla                  |
