import os
import json
import base64
import requests
import ast
from datetime import datetime
from app.core.config import settings
from app.utils.logger import logger

# Constants from legacy config
PDF_STORAGE_PATH = settings.PDF_STORAGE_PATH
OTP_GENERATE_URL = "https://api.wonderhfl.com/OmniFinServices/restServices/userService/otp/generate"
OTP_VALIDATE_URL = "https://api.wonderhfl.com/OmniFinServices/restServices/userService/otp/validate"

COMMON_CREDENTIALS = {
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
}

async def generate_otp(mobile: str):
    payload = {
        "mobileNumber": mobile,
        "workingUserId": "admin",
        "userCredentials": COMMON_CREDENTIALS,
        "businessDate": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    try:
        response = requests.post(OTP_GENERATE_URL, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"OTP generation failed: {e}")
        return {"operationStatus": "0", "error": str(e)}

async def validate_otp(sms_record_id: str, otp: str):
    payload = {
        "smsRecordId": sms_record_id,
        "smsOTP": otp,
        "userCredentials": COMMON_CREDENTIALS
    }
    try:
        response = requests.post(OTP_VALIDATE_URL, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"OTP validation failed: {e}")
        return {"operationStatus": "0", "error": str(e)}

def verify_pan(pan: str):
    url = "https://hub.perfios.com/api/kyc/v2/pan"
    headers = {
        "Content-Type": "application/json",
        "x-auth-key": "yehitufubQfhvUw"
    }
    payload = {
        "consent": "Y",
        "pan": pan,
        "clientData": {"caseId": "123456"}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"PAN verification failed: {e}")
        return {"error": str(e)}

def get_loan_oauth_token():
    url = "https://uat-api.wonderhfl.com/gateway-service/authServices/oauth/token"
    headers = {
        "Accept": "application/json",
        "Authorization": "Basic bW9iaWxlOm1vYmlsZQ==",
        "clinetName": "mobile",
        "Cookie": "Path=/gateway-service"
    }
    data = {
        "username": "ADMIN",
        "password": "0cc175b9c0f1b6a831c399e269772661",
        "grant_type": "password",
        "client_id": "mobile"
    }
    response = requests.post(url, headers=headers, data=data, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]

def get_loan_details(phone_no: str):
    try:
        access_token = get_loan_oauth_token()
        url = "https://uat-api.wonderhfl.com/gateway-service/omnifin-los-lms-api/dsaDealerWSServices/getLoanDetails"
        headers = {
            "Authorization": f"bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {"phoneNo": phone_no}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get loan details: {e}")
        return None

def generate_transunion_token():
    url = "https://www.test.transuniondecisioncentre.co.in/DC/TUcl/TU.DE.Pont/Token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "grant_type": "password",
        "username": "HF6411GO01_UAT001",
        "password": "Wonder#20252026"
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"TransUnion token error: {e}")
        return None

# Placeholder user_data for CIBIL application
CIBIL_USER_DATA_TEMPLATE = {
    "RequestInfo": {"SolutionSetName": "Go_WONDERHOME_AGSS", "ExecuteLatestVersion": "true"},
    "Fields": {
        "Applicants": {
            "Applicant": {
                "ApplicantType": "Main",
                "ApplicantFirstName": "YASH",
                "ApplicantMiddleName": "",
                "ApplicantLastName": "BANSAL",
                "DateOfBirth": "24042000",
                "Gender": "M",
                "Identifiers": {"Identifier": [{"IdNumber": "DVWPB4941P", "IdType": "01"}, {"IdNumber": "315260054706", "IdType": "06"}]},
                "Telephones": {"Telephone": [{"TelephoneExtension": "", "TelephoneNumber": "8646456566", "TelephoneType": "01"}]},
                "Addresses": {"Address": {"AddressType": "02", "AddressLine1": "S/O VIVEK BANSAL 23 HANUMAN ROAD CHAUBEY", "AddressLine2": "KA BAGH NEAR CHHOTE HANUMAN FIROZABAD", "AddressLine3": "FIROZABAD UTTAR PRADESH 283203", "AddressLine4": "", "AddressLine5": "", "City": "Firozabad", "PinCode": "283203", "ResidenceType": "02", "StateCode": "09"}},
                "Services": {"Service": {"Id": "CORE", "Operations": {"Operation": [{"Name": "ConsumerCIR", "Params": {"Param": [{"Name": "CibilBureauFlag", "Value": "false"}, {"Name": "Amount", "Value": "1000000"}, {"Name": "Purpose", "Value": "40"}, {"Name": "ScoreType", "Value": "08"}, {"Name": "MemberCode", "Value": "HF64117777_MUATC2CNPE"}, {"Name": "Password", "Value": "niu@gtlsEra7tsfxjnz"}, {"Name": "FormattedReport", "Value": "true"}, {"Name": "GSTStateCode", "Value": "09"}]}}, {"Name": "IDV", "Params": {"Param": [{"Name": "IDVerificationFlag", "Value": "false"}, {"Name": "ConsumerConsentForUIDAIAuthentication", "Value": "N"}, {"Name": "GSTStateCode", "Value": "09"}]}}, {"Name": "FIWaiver", "Params": {"Param": [{"Name": "FIWaiver", "Value": "false"}]}}]}}}
            }
        },
        "ApplicationData": {"GSTStateCode": "09", "Services": {"Service": {"Id": "CORE", "Skip": "N", "Consent": "true"}}}
    }
}

def submit_cibil_application(access_token: str, pan: str, last_name: str):
    url = "https://www.test.transuniondecisioncentre.co.in/DC/TUCL/TU.DE.Pont/Applications"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    # Update template with user info
    data = CIBIL_USER_DATA_TEMPLATE.copy()
    data["Fields"]["Applicants"]["Applicant"]["ApplicantLastName"] = last_name
    data["Fields"]["Applicants"]["Applicant"]["Identifiers"]["Identifier"][0]["IdNumber"] = pan
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        result = response.json()
        
        # Extract document ID (logic from legacy)
        document_id = None
        services = result.get('Fields', {}).get('Applicants', {}).get('Applicant', {}).get('Services', {}).get('Service', {})
        
        if isinstance(services, list):
            for service in services:
                operations = service.get('Operations', {}).get('Operation', [])
                for operation in operations:
                    doc = operation.get('Data', {}).get('Response', {}).get('RawResponse', {}).get('Document')
                    if doc and 'Id' in doc:
                        document_id = doc['Id']
                        break
        elif isinstance(services, dict):
            operations = services.get('Operations', {}).get('Operation', [])
            for operation in operations:
                doc = operation.get('Data', {}).get('Response', {}).get('RawResponse', {}).get('Document')
                if doc and 'Id' in doc:
                    document_id = doc['Id']
                    break
                    
        return document_id
    except Exception as e:
        logger.error(f"CIBIL submission error: {e}")
        return None
