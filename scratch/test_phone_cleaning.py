import sys
import os

# Add the project root to sys.path
sys.path.append("/home/techinvestor/Documents/projects/safenest-backend")

from app.utils.validators import clean_tanzania_phone

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
