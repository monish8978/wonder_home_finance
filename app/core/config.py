import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Wonder Home Loan Bot"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB
    MONGO_URL: str = "mongodb+srv://mongodb:mongodb@cluster0.1nfoz.mongodb.net/?retryWrites=true&w=majority"
    DATABASE_NAME: str = "whatsapp_bot"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # External APIs
    OTP_GENERATE_URL: str = "https://api.wonderhfl.com/OmniFinServices/restServices/userService/otp/generate"
    OTP_VALIDATE_URL: str = "https://api.wonderhfl.com/OmniFinServices/restServices/userService/otp/validate"
    LOAN_DETAILS_URL: str = "https://uat-api.wonderhfl.com/gateway-service/omnifin-los-lms-api/dsaDealerWSServices/getLoanDetails"
    AUTH_TOKEN_URL: str = "https://uat-api.wonderhfl.com/gateway-service/authServices/oauth/token"
    WHATSAPP_API_URL: str = "https://partnersV1.pinbot.ai/v3/742406742288776/messages"
    WHATSAPP_API_KEY: str = "6e90b3a8-7f1e-11f0-98fc-02c8a5e042bd"
    
    # Credentials
    PERFIOS_AUTH_KEY: str = "yehitufubQfhvUw"
    TU_USERNAME: str = "HF6411GO01_UAT001"
    TU_PASSWORD: str = "Wonder#20252026"
    
    # Storage
    PDF_STORAGE_PATH: str = "/Czentrix/apps/wonder_homes_loan_bot/documents"
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = 1000
    MAX_ATTEMPTS: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
