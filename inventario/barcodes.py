import re


def _has_valid_check_digit(code):
    if len(code) not in {8, 12, 13, 14}:
        return False

    weighted_sum = sum(
        int(digit) * (3 if position % 2 == 0 else 1)
        for position, digit in enumerate(reversed(code[:-1]))
    )
    expected_digit = (10 - weighted_sum % 10) % 10
    return expected_digit == int(code[-1])


def _upce_to_upca(code):
    if len(code) != 8 or code[0] not in {"0", "1"}:
        return None

    number_system = code[0]
    payload = code[1:7]
    check_digit = code[7]
    last_payload_digit = payload[5]

    if last_payload_digit in {"0", "1", "2"}:
        expanded = (
            number_system
            + payload[:2]
            + last_payload_digit
            + "0000"
            + payload[2:5]
            + check_digit
        )
    elif last_payload_digit == "3":
        expanded = (
            number_system + payload[:3] + "00000" + payload[3:5] + check_digit
        )
    elif last_payload_digit == "4":
        expanded = (
            number_system + payload[:4] + "00000" + payload[4] + check_digit
        )
    else:
        expanded = (
            number_system
            + payload[:5]
            + "0000"
            + last_payload_digit
            + check_digit
        )

    return expanded if _has_valid_check_digit(expanded) else None


def barcode_lookup_values(value):
    code = (value or "").strip()
    if not re.fullmatch(r"[0-9]+", code):
        raise ValueError("El código debe contener solo dígitos.")

    values = [code]
    is_valid = _has_valid_check_digit(code)

    if len(code) == 8:
        upca = _upce_to_upca(code)
        if upca:
            values.append(upca)
            is_valid = True

    if not is_valid:
        raise ValueError(
            "El código debe ser un GTIN válido (EAN-8, UPC-A, EAN-13, UPC-E o GTIN-14)."
        )

    return values
