import requests
import json

base_url = "http://127.0.0.1:8000/api/v1"

def test_flow():
    print("Testing OTP Flow...")
    
    phone = "615765170"
    
    # 1. Request OTP
    req_data = {
        "phone_number": phone,
        "country_code": "+255"
    }
    print(f"Requesting OTP for {phone}")
    r1 = requests.post(f"{base_url}/auth/request-otp", json=req_data)
    print(f"Request OTP status: {r1.status_code}")
    print(f"Response: {r1.text}")
    
    # We can't easily get the OTP from the API response in production,
    # but the logs show it in the terminal or dev response
    resp_json = r1.json()
    otp = resp_json.get("dev_otp")
    if not otp:
        print("dev_otp not found in response, cannot proceed with automated verification.")
        return
        
    print(f"Extracted dev_otp: {otp}")
    
    # 2. Verify OTP
    ver_data = {
        "phone_number": phone,
        "otp_code": otp,
        # Intentionally omitting country_code to test default behavior
    }
    print(f"Verifying OTP {otp} for {phone}")
    r2 = requests.post(f"{base_url}/auth/verify-otp", json=ver_data)
    print(f"Verify OTP status: {r2.status_code}")
    print(f"Response: {r2.text}")

if __name__ == "__main__":
    test_flow()
