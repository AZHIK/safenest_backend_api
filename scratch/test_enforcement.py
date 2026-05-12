import sys
import os

# Add the project root to sys.path
sys.path.append("/home/techinvestor/Documents/projects/safenest-backend")

from app.utils.validators import clean_tanzania_phone
from pydantic import ValidationError
from app.schemas.auth import OTPRequest, OTPVerify

def test_enforcement():
    print("--- Testing Tanzania Phone Enforcement ---")
    
    # Case 1: TZ numbers (Should PASS)
    tz_cases = ["0712345678", "+255712345678", "255712345678", "712345678"]
    for p in tz_cases:
        try:
            res = clean_tanzania_phone(p)
            print(f"TZ Input: {p:15} | Got: {res} | PASS")
        except Exception as e:
            print(f"TZ Input: {p:15} | Error: {e} | FAIL")

    # Case 2: International numbers (Should FAIL)
    intl_cases = ["+1615765170", "+447700900123", "+254712345678"]
    for p in intl_cases:
        try:
            res = clean_tanzania_phone(p)
            print(f"Intl Input: {p:15} | Got: {res} | FAIL (Should have failed)")
        except ValueError as e:
            print(f"Intl Input: {p:15} | Expected Error: {e} | PASS")

    # Case 3: Schema defaults
    print("\n--- Testing Schema Defaults ---")
    try:
        req = OTPRequest(phone_number="712345678")
        print(f"OTPRequest default CC: {req.country_code}")
        
        verify = OTPVerify(phone_number="712345678", otp_code="123456")
        print(f"OTPVerify default CC: {verify.country_code}")
        
        if req.country_code == verify.country_code == "+255":
            print("Schema consistency check: PASS")
        else:
            print("Schema consistency check: FAIL")
    except Exception as e:
        print(f"Schema test failed: {e}")

    # Case 4: Enforce +255 only in schemas
    print("\n--- Testing Schema Enforcement (+255 only) ---")
    try:
        OTPRequest(phone_number="712345678", country_code="+1")
        print("OTPRequest with +1: FAIL (Should have raised ValidationError)")
    except ValidationError:
        print("OTPRequest with +1: PASS (Raised ValidationError)")

if __name__ == "__main__":
    test_enforcement()
