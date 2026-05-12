def clean_tanzania_phone(phone: str) -> str:
    """
    Clean and validate Tanzania phone number for Twilio Verify.
    Returns 9-digit format (7XXXXXXXX).
    Removes leading 0, 255, or +255.
    """
    if not phone:
        raise ValueError("Phone number is required")

    # Remove all non-digits
    digits = "".join(c for c in phone if c.isdigit())

    # Handle country code or leading zero
    if digits.startswith("255"):
        digits = digits[3:]
    elif digits.startswith("0"):
        digits = digits[1:]

    # Tanzania numbers must be 9 digits after stripping prefix
    if len(digits) != 9:
        raise ValueError("Tanzania phone number must be 9 digits (excluding country code/leading zero)")

    # Validate local prefixes (7 for mobile, 6 for mobile, 2 for fixed)
    if digits[0] not in "267":
        raise ValueError("Invalid Tanzania phone number prefix. Expected 7, 6, or 2.")

    return digits

test_cases = [
    ("0712345678", "712345678"),
    ("+255712345678", "712345678"),
    ("255712345678", "712345678"),
    ("712345678", "712345678"),
    ("0222345678", "222345678"), # Fixed line
    (" 0712 345 678 ", "712345678"),
]

invalid_cases = [
    "1234567",       # Too short
    "0123456789",    # Invalid prefix (01)
    "0812345678",    # Invalid prefix (08)
    "07123456789",   # Too long
]

print("--- Testing Valid Cases ---")
for inp, exp in test_cases:
    try:
        res = clean_tanzania_phone(inp)
        status = "PASS" if res == exp else "FAIL"
        print(f"Input: {inp:15} | Expected: {exp:10} | Got: {res:10} | {status}")
    except Exception as e:
        print(f"Input: {inp:15} | Expected: {exp:10} | Got: ERROR ({e}) | FAIL")

print("\n--- Testing Invalid Cases ---")
for inp in invalid_cases:
    try:
        res = clean_tanzania_phone(inp)
        print(f"Input: {inp:15} | Got: {res:10} | FAIL (Should have raised ValueError)")
    except ValueError as e:
        print(f"Input: {inp:15} | Got expected error: {e} | PASS")
    except Exception as e:
        print(f"Input: {inp:15} | Got unexpected error: {type(e).__name__}: {e} | FAIL")
