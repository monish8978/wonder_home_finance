import httpx
from datetime import datetime
from app.core.config import settings
from app.utils.logger import logger

class OTPService:
    @staticmethod
    async def generate_otp(mobile: str):
        payload = {
            "mobileNumber": mobile,
            "workingUserId": "admin",
            "userCredentials": {
                "userId": "APPUSER",
                "userPassword": "a18b22ba81f1a4cb6b1884ccff5e04d4",
                "source": "MOBILE",
                "sourceId": "e3712a79edeabcad",
                "initiatedBy": "admin",
                "deviceName": "RMX3581",
                "deviceVersion": "30",
                "sourceVersion": "6.0.0.5",
                "latitude": "28.6077002",
                "longitude": "77.3617263",
                "address": ""
            },
            "businessDate": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(settings.OTP_GENERATE_URL, json=payload, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"OTP Generation failed: {e}")
                return None

    @staticmethod
    async def validate_otp(sms_record_id: str, otp: str):
        payload = {
            "smsRecordId": sms_record_id,
            "smsOTP": otp,
            "userCredentials": {
                 "userId": "APPUSER",
                 "userPassword": "a18b22ba81f1a4cb6b1884ccff5e04d4",
                 "source": "MOBILE",
            }
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(settings.OTP_VALIDATE_URL, json=payload, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"OTP Validation failed: {e}")
                return None
