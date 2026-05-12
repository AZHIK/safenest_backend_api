import asyncio
import sys

sys.path.append("/home/techinvestor/Documents/projects/safenest-backend")

from app.db.redis import redis_client, otp_storage
from app.core.config import settings

async def main():
    await redis_client.connect()
    
    # Store a test OTP
    phone = "+255615765170"
    otp = "123456"
    print(f"Storing OTP {otp} for {phone}")
    await otp_storage.store(phone, otp)
    
    # Check if it exists
    key = otp_storage._key(phone)
    val = await redis_client.get(key)
    print(f"Raw value in redis: {val}")
    
    # Try verifying
    res = await otp_storage.verify(phone, otp)
    print(f"Verify result: {res}")
    
    await redis_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
