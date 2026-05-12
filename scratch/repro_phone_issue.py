import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append("/home/techinvestor/Documents/projects/safenest-backend")

from app.utils.validators import clean_tanzania_phone
from app.schemas.auth import OTPRequest, OTPVerify

def test_collision():
    print("--- Testing Phone Normalization Collision ---")
    
    # Case 1: US number that looks like TZ local part
    # +1 615 765 170
    us_phone_part = "615765170"
    us_cc = "+1"
    
    try:
        cleaned_us = clean_tanzania_phone(us_phone_part)
        print(f"US Phone Part: {us_phone_part} | Cleaned: {cleaned_us} (SUCCESS - COLLISION!)")
    except Exception as e:
        print(f"US Phone Part: {us_phone_part} | Error: {e}")

    # Case 2: Inconsistent Schemas
    print("\n--- Testing Schema Inconsistency ---")
    
    req = OTPRequest(phone_number=us_phone_part, country_code=us_cc)
    print(f"OTPRequest: phone_number={req.phone_number}, country_code={req.country_code}")
    
    verify = OTPVerify(phone_number=us_phone_part, otp_code="123456")
    print(f"OTPVerify: phone_number={verify.phone_number}, country_code={verify.country_code}")
    
    if req.country_code != verify.country_code:
        print("ALERT: country_code mismatch between Request and Verify defaults!")

if __name__ == "__main__":
    test_collision()
