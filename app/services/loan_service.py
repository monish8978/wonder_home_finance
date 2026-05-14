import httpx
from app.core.config import settings
from app.db.mongo import db_manager
from app.utils.logger import logger
from app.db.redis_client import redis_client
import json

class LoanService:
    @staticmethod
    async def get_oauth_token():
        # Check cache first
        token = redis_client.get("loan_oauth_token")
        if token:
            return token

        data = {
            "username": "ADMIN",
            "password": "0cc175b9c0f1b6a831c399e269772661",
            "grant_type": "password",
            "client_id": "mobile"
        }
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic bW9iaWxlOm1vYmlsZQ==",
            "clinetName": "mobile",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(settings.AUTH_TOKEN_URL, headers=headers, data=data)
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data["access_token"]
                # Cache token for 1 hour (adjust as per expiry)
                redis_client.setex("loan_oauth_token", 3600, access_token)
                return access_token
            except Exception as e:
                logger.error(f"Failed to get OAuth token: {e}")
                return None

    @staticmethod
    async def get_loan_details(phone_no: str):
        # Cache check for loan details
        cached_data = redis_client.get(f"loan_details:{phone_no}")
        if cached_data:
            return json.loads(cached_data)

        access_token = await LoanService.get_oauth_token()
        if not access_token:
            return None

        headers = {
            "Authorization": f"bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"phoneNo": phone_no}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(settings.LOAN_DETAILS_URL, headers=headers, json=payload)
                response.raise_for_status()
                loan_data = response.json()

                # Save to MongoDB as per original logic
                db = db_manager.get_db()
                collection = db[phone_no]
                await collection.replace_one(
                    {"phoneNo": phone_no},
                    loan_data,
                    upsert=True
                )

                # Cache for 10 minutes
                redis_client.setex(f"loan_details:{phone_no}", 600, json.dumps(loan_data))
                
                return loan_data
            except Exception as e:
                logger.error(f"Failed to fetch loan details for {phone_no}: {e}")
                return None

    @staticmethod
    def format_loans_for_whatsapp(data):
        loans = data.get("customerLoanDetails", [])
        if not loans:
            return "❌ No loan details found.", None

        seen = set()
        message = "📄 *Your Loan Details*\n\n"
        customer_name = "Customer"

        for loan in loans:
            loan_key = (loan["customerName"], loan["loanNumber"])
            if loan_key in seen:
                continue
            seen.add(loan_key)
            customer_name = loan["customerName"]

            message += (
                "━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Customer Name*: {loan['customerName']}\n"
                f"💳 *Loan No*: {loan['loanNumber']}\n"
                f"💰 *Loan Amount*: ₹{int(loan['loanAmount'])}\n"
                f"📆 *Next Due Date*: {loan['nextPaymentDueDate']}\n"
                f"💵 *EMI*: ₹{int(loan['emiAndPreEmi'])}\n"
                f"🏢 *Branch*: {loan['branchName']}\n"
                f"📞 *Branch Phone*: {loan['branchPhoneNo']}\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
            )

        return message.strip(), customer_name

    @staticmethod
    def extract_loan_details(api_data):
        rows = api_data.get("customerLoanDetails", [])
        clean_rows = []
        for r in rows:
            clean_rows.append({
                "customerName": r["customerName"],
                "loanAmount": float(r["loanAmount"]),
                "emi": float(r["emiAndPreEmi"]),
                "loanNumber": r["loanNumber"],
                "nextPaymentDueDate": r["nextPaymentDueDate"],
                "branchName": r["branchName"],
                "branchPhoneNo": r["branchPhoneNo"]
            })
        return clean_rows

    @staticmethod
    async def validate_loan_with_crm(mobile: str, loan_last_5: str):
        db = db_manager.get_db()
        loan_collection = db[mobile]
        
        pipeline = [
            {"$unwind": "$customerLoanDetails"},
            {
                "$addFields": {
                    "lastFiveDigits": {
                        "$substr": [
                            "$customerLoanDetails.loanNumber",
                            {"$subtract": [{"$strLenCP": "$customerLoanDetails.loanNumber"}, 5]},
                            5
                        ]
                    }
                }
            },
            {"$match": {"lastFiveDigits": loan_last_5}},
            {
                "$group": {
                    "_id": "$lastFiveDigits",
                    "loanData": {"$first": "$customerLoanDetails"}
                }
            }
        ]
        
        cursor = loan_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        if result:
            loan = result[0]["loanData"]
            return {
                "status": "MATCH",
                "customer_name": loan["customerName"],
                "branch": loan["branchName"],
                "loan_number": loan["loanNumber"]
            }
        return {"status": "NOT_MATCH"}

    @staticmethod
    async def verify_pan(pan: str):
        url = "https://hub.perfios.com/api/kyc/v2/pan"
        headers = {
            "Content-Type": "application/json",
            "x-auth-key": settings.PERFIOS_AUTH_KEY  # Move to settings
        }
        payload = {
            "consent": "Y",
            "pan": pan,
            "clientData": {"caseId": "123456"}
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                return response.json()
            except Exception as e:
                logger.error(f"PAN verification failed: {e}")
                return {"error": str(e)}

    @staticmethod
    async def generate_transunion_token():
        url = "https://www.test.transuniondecisioncentre.co.in/DC/TUcl/TU.DE.Pont/Token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "grant_type": "password",
            "username": settings.TU_USERNAME,
            "password": settings.TU_PASSWORD
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, data=payload)
                token_data = response.json()
                return token_data.get("access_token")
            except Exception as e:
                logger.error(f"TU Token error: {e}")
                return None
