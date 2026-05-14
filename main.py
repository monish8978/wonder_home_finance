from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request, Query
from pymongo import MongoClient
from datetime import datetime, timedelta
from fastapi.responses import FileResponse
import ast
import requests
import json
import pdfkit
import base64
import os
import time

app = FastAPI()

# =====================================================
# CONFIG
# =====================================================
SESSION_TIMEOUT = timedelta(minutes=1000)
MAX_ATTEMPTS = 3

# =====================================================
# OTP API CONFIG
# =====================================================
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


CRITICAL_ISSUES_WHATSAPP_BUTTONS = [
    "FCL / SOA / LOD Request",
    "EMI / Pre-EMI Related",
    "Refund",
    "Cibil related",
    "ROI/Tenure Miscomm",
    "Amount Taken in Emp. A/C"
]

WHATSAPP_DOC_BUTTONS = [
    "Others",
]

CRITICAL_ISSUE_MAPPING = {
    "FCL / SOA / LOD Request": "FCL/SOA/LOD Request (out of TAT)",
    "EMI/ Pre-EMI Related": "EMI/ Pre-EMI Related (payment updation)",
    "Refund": "Refund (advance payment or excess payment)",
    "ROI/Tenure Miscomm": "Employee misconduct and ROI/tenure miscommunication.",
    "Cibil related": "Cibil related",
    "Amount Taken in Emp. A/C": "Amount taken by Employee in his bank account",
}


NON_CRITICAL_ISSUE_MAPPING = {
    "Others": "Others",
}

# =====================================================
# DATABASE
# =====================================================
client = MongoClient("mongodb+srv://mongodb:mongodb@cluster0.1nfoz.mongodb.net/?retryWrites=true&w=majority")
db = client["whatsapp_bot"]
users = db["chat_state"]
payment_collection = db["payment_logs"]

PDF_STORAGE_PATH = "/Czentrix/apps/wonder_homes_loan_bot/documents"
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)


def normalize(text):
    return text.lower().strip().replace("  ", " ")

def check_critical_issue(msg):
    msg_norm = normalize(msg)
    for wa_text, internal_issue in CRITICAL_ISSUE_MAPPING.items():
        if normalize(wa_text) == msg_norm:
            return internal_issue

    return None


def check_non_critical_issue(msg):
    msg_norm = normalize(msg)

    for wa_text, internal_issue in NON_CRITICAL_ISSUE_MAPPING.items():
        if normalize(wa_text) == msg_norm:
            return internal_issue   # matched

    return None


def download_interest_certificate(loan_number, from_date, to_date):
    url = "https://uat-api.wonderhfl.com/OmniFinServices/restServices/customerServiceController/fetchInterestCertificate"

    headers = {
        "Content-Type": "application/json",
        "Cookie": "JSESSIONID=GtwdUoEThWz70a32S7_Uk_T6sEVstpqm5p8KHaJl.win-dop26btmo11; JSESSIONID=y_PLqxAGkBLdf5-EA3yRjb9gENJU8_d-boL8pRsn.win-dop26btmo11"
    }

    payload = {
        "userCredentials": {
            "userId": "appuser",
            "userPassword": "a18b22ba81f1a4cb6b1884ccff5e04d4"
        },
        "loanNumber": loan_number,
        "fromDate": from_date,
        "toDate": to_date
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        return {"error": "API Failed", "details": response.text}

    data = response.json()

    if data.get("operationStatus") != "1":
        return {"error": data.get("operationMessage")}

    base64_pdf = data["interestCertificateStream"]

    # Decode Base64 → PDF
    pdf_bytes = base64.b64decode(base64_pdf)

    # Folder
    os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

    filename = f"Interest_Certificate_{loan_number}.pdf"
    filepath = os.path.join(PDF_STORAGE_PATH, filename)

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    return {
        "status": "success",
        "message": "Interest Certificate Generated",
        "file": filepath
    }



def download_welcome_letter(loan_number):
    url = "https://uat-api.wonderhfl.com/OmniFinServices/restServices/customerServiceController/fetchWelcomeLetterReport"

    headers = {
        "Content-Type": "application/json",
        "Cookie": "JSESSIONID=GtwdUoEThWz70a32S7_Uk_T6sEVstpqm5p8KHaJl.win-dop26btmo11"
    }

    payload = {
        "userCredentials": {
            "userId": "appuser",
            "userPassword": "a18b22ba81f1a4cb6b1884ccff5e04d4"
        },
        "loanNumber": loan_number
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        return {"error": "API Failed", "details": response.text}

    data = response.json()

    if data.get("operationStatus") != "1":
        return {"error": data.get("operationMessage")}

    base64_pdf = data["welcomeLetterReportStream"]

    # Decode Base64 → PDF
    pdf_bytes = base64.b64decode(base64_pdf)

    # Folder
    os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

    filename = f"welcome_letter_{loan_number}.pdf"
    filepath = os.path.join(PDF_STORAGE_PATH, filename)

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    return {
        "status": "success",
        "message": "Welcome Letter Generated",
        "file": filepath
    }


def send_whatsapp_cta_template(to_number,template_name):
    url = "https://partnersV1.pinbot.ai/v3/742406742288776/messages"

    headers = {
        "apikey": "6e90b3a8-7f1e-11f0-98fc-02c8a5e042bd",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "en"
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        return response.json()

    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        }


def fetch_repayment_schedule(loan_number):
    url = "https://uat-api.wonderhfl.com/OmniFinServices/restServices/customerServiceController/repaymentSchedule"

    headers = {
        "Content-Type": "application/json",
        "Cookie": "JSESSIONID=GtwdUoEThWz70a32S7_Uk_T6sEVstpqm5p8KHaJl.win-dop26btmo11; JSESSIONID=bILhxzVwJTNPo2v5kMgnJ4PAkaq5YMdoP132L4mW.win-dop26btmo11"
    }

    payload = {
        "userCredentials": {
            "userId": "appuser",
            "userPassword": "a18b22ba81f1a4cb6b1884ccff5e04d4"
        },
        "loanNumber": loan_number
    }

    r = requests.post(url, headers=headers, json=payload, timeout=20)

    if r.status_code != 200:
        return None

    return r.json()

def extract_main_fields(api_data):
    rows = api_data.get("crRepayschDtlList", [])

    clean_rows = []
    for r in rows:
        clean_rows.append({
            "date": r["instlDate"],
            "emi": float(r["instlAmount"]),
            "principal": float(r["prinComp"]),
            "interest": float(r["intComp"]),
            "balance": float(r["prinOs"])
        })

    return clean_rows

def extract_loan_details(api_data):

    # 🔹 Step 1: Convert string to dict
    if isinstance(api_data, str):
        api_data = ast.literal_eval(api_data)

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


def create_emi_pdf(loan_no, emi_rows, file_path):
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph(f"Loan Repayment Schedule<br/>Loan No: {loan_no}", styles["Title"])
    elements.append(title)

    data = [
        ["Date", "EMI (₹)", "Principal (₹)", "Interest (₹)", "Balance (₹)"]
    ]

    for r in emi_rows:
        data.append([
            r["date"],
            f"{r['emi']:,.0f}",
            f"{r['principal']:,.0f}",
            f"{r['interest']:,.0f}",
            f"{r['balance']:,.0f}"
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), "#DDDDDD"),
        ("GRID", (0,0), (-1,-1), 1, "#000000"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ]))

    elements.append(table)

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    doc.build(elements)


def create_loan_details_pdf(loan_rows, file_path):
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title = Paragraph("Customer Loan Details Report", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 0.3 * inch))

    data = [[
        "Customer Name",
        "Loan Amount (₹)",
        "EMI (₹)",
        "Loan Number",
        "Next Due Date",
        "Branch Name",
        "Branch Phone"
    ]]

    for loan in loan_rows:
        data.append([
            loan.get("customerName", ""),
            f"{loan.get('loanAmount', 0):,.0f}",
            f"{loan.get('emi', 0):,.0f}",   # ✅ FIXED
            loan.get("loanNumber", ""),
            loan.get("nextPaymentDueDate", ""),
            loan.get("branchName", ""),
            loan.get("branchPhoneNo", "")
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    elements.append(table)

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    doc.build(elements)


def send_cibil_pdf_whatsapp(to, pdf_url,filename):
    url = "https://omniqa.c-zentrix.com/whatsappApi_v2/OUT/outgoing.php"

    payload = {
        "token": "6e90b3a8-7f1e-11f0-98fc-02c8a5e042bd",
        "auth_token": "6e90b3a8-7f1e-11f0-98fc-02c8a5e042bd",
        "accountId": "6e90b3a8-7f1e-11f0-98fc-02c8a5e042bd",
        "mobile_no": to,
        "type": "document",
        "tag": "BotTvt",
        "licenseId": "d62ceab4ea4e5eb537453fb9d5cddd65",
        "api_type": "pinnacle",
        "media_url": pdf_url,
        "messageBody": filename,
        "mime_type": "application/pdf"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()
    except Exception as e:
        print("Error:", str(e))
        return None


# =====================================================
# HELPERS
# =====================================================
def get_user(wa):
    return users.find_one({"wa": wa})

def reset_flow(wa, clear_mobile=False):
    """
    Resets the flow.
    If clear_mobile is True, it wipes everything.
    Otherwise, it preserves the 'mobile' number if it exists.
    """
    user = get_user(wa)
    existing_mobile = user.get("mobile") if user else None

    # Delete old state
    users.delete_one({"wa": wa})

    # New state
    new_state = {
        "wa": wa,
        "step": "LANG",
        "attempt": 0,
        "createdAt": datetime.utcnow(),
        "lastInteractionAt": datetime.utcnow()
    }

    # Preserve mobile if we don't want to clear it
    if not clear_mobile and existing_mobile:
        new_state["mobile"] = existing_mobile

    users.insert_one(new_state)

def save_user(wa, data):
    users.update_one(
        {"wa": wa},
        {"$set": {**data, "lastInteractionAt": datetime.utcnow()}},
        upsert=True
    )

def attempt_failed(user, wa):
    attempt = user.get("attempt", 0) + 1
    if attempt >= MAX_ATTEMPTS:
        reset_flow(wa) # Keep mobile, just reset steps
        return True
    save_user(wa, {"attempt": attempt})
    return False

def is_session_expired(user):
    last = user.get("lastInteractionAt")
    return not last or datetime.utcnow() - last > SESSION_TIMEOUT

# =====================================================
# OTP FUNCTIONS
# =====================================================
def generate_otp(mobile):
    payload = {
        "mobileNumber": mobile,
        "workingUserId": "admin",
        "userCredentials": COMMON_CREDENTIALS,
        "businessDate": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    res = requests.post(OTP_GENERATE_URL, json=payload, timeout=10).json()
    return res

def validate_otp(sms_record_id, otp):
    payload = {
        "smsRecordId": sms_record_id,
        "smsOTP": otp,
        "userCredentials": COMMON_CREDENTIALS
    }
    return requests.post(OTP_VALIDATE_URL, json=payload, timeout=10).json()


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

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()

    token_data = response.json()
    return token_data["access_token"]


def get_loan_details(phone_no):
    access_token = get_loan_oauth_token()

    url = "https://uat-api.wonderhfl.com/gateway-service/omnifin-los-lms-api/dsaDealerWSServices/getLoanDetails"

    headers = {
        "Authorization": f"bearer {access_token}",
        "Content-Type": "application/json",
        "Cookie": "Path=/gateway-service; Path=/gateway-service"
    }

    payload = {
        "phoneNo": phone_no
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    loan_data = response.json()

    # MongoDB upsert
    collection = db[phone_no]
    collection.replace_one(
        {"phoneNo": phone_no},   # filter
        loan_data,               # new document
        upsert=True
    )

    return loan_data


# =====================================================
# BUSINESS LOGIC (DUMMY)
# =====================================================
def validate_loan_with_crm(mobile, loan_last_5):
    loan_collection = db[mobile]
    pipeline = [
        {"$unwind": "$customerLoanDetails"},

        {
            "$addFields": {
                "lastFiveDigits": {
                    "$substr": [
                        "$customerLoanDetails.loanNumber",
                        {"$subtract": [
                            {"$strLenCP": "$customerLoanDetails.loanNumber"}, 5
                        ]},
                        5
                    ]
                }
            }
        },

        {
            "$match": {
                "lastFiveDigits": loan_last_5
                # "mobile": mobile
            }
        },

        {
            "$group": {
                "_id": "$lastFiveDigits",
                "loanData": {"$first": "$customerLoanDetails"}
            }
        }
    ]

    result = list(loan_collection.aggregate(pipeline))

    if result:
        loan = result[0]["loanData"]
        return {
            "status": "MATCH",
            "customer_name": loan["customerName"],
            "branch": loan["branchName"],
            "loan_number": loan["loanNumber"]
        }

    return {"status": "NOT_MATCH"}


def get_all_loan(mobile):
    loan_collection = db[mobile]
    data = loan_collection.find_one(
        {},
        {"_id": 0}
    )
    return data

def format_loans_for_whatsapp(data):
    loans = data.get("customerLoanDetails", [])

    if not loans:
        return "❌ No loan details found."

    seen = set()
    message = "📄 *Your Loan Details*\n\n"

    for loan in loans:
        loan_key = (loan["customerName"], loan["loanNumber"])
        if loan_key in seen:
            continue
        seen.add(loan_key)

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

    customerName = loan['customerName']

    return message.strip(),customerName


def verify_pan(pan: str):
    url = "https://hub.perfios.com/api/kyc/v2/pan"

    headers = {
        "Content-Type": "application/json",
        "x-auth-key": "yehitufubQfhvUw"
    }

    payload = {
        "consent": "Y",
        "pan": pan,
        "clientData": {
            "caseId": "123456"
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raises error for 4xx/5xx

        return response.json()  # API response as dict

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def generate_transunion_token():
    url = "https://www.test.transuniondecisioncentre.co.in/DC/TUcl/TU.DE.Pont/Token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {
        "grant_type": "password",
        "username": "HF6411GO01_UAT001",
        "password": "Wonder#20252026"
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()

        token_data = response.json()
        return token_data.get("access_token")   # ✅ Only access_token return

    except requests.exceptions.RequestException as e:
        print("Token Error:", str(e))
        return None


user_data = {"RequestInfo":{"SolutionSetName":"Go_WONDERHOME_AGSS","ExecuteLatestVersion":"true"},"Fields":{"Applicants":{"Applicant":{"ApplicantType":"Main","ApplicantFirstName":"YASH","ApplicantMiddleName":"","ApplicantLastName":"BANSAL","DateOfBirth":"24042000","Gender":"M","Identifiers":{"Identifier":[{"IdNumber":"DVWPB4941P","IdType":"01"},{"IdNumber":"315260054706","IdType":"06"}]},"Telephones":{"Telephone":[{"TelephoneExtension":"","TelephoneNumber":"8646456566","TelephoneType":"01"}]},"Addresses":{"Address":{"AddressType":"02","AddressLine1":"S\/O VIVEK BANSAL 23 HANUMAN ROAD CHAUBEY","AddressLine2":"KA BAGH NEAR CHHOTE HANUMAN FIROZABAD","AddressLine3":"FIROZABAD UTTAR PRADESH 283203","AddressLine4":"","AddressLine5":"","City":"Firozabad","PinCode":"283203","ResidenceType":"02","StateCode":"09"}},"Services":{"Service":{"Id":"CORE","Operations":{"Operation":[{"Name":"ConsumerCIR","Params":{"Param":[{"Name":"CibilBureauFlag","Value":"false"},{"Name":"Amount","Value":"1000000"},{"Name":"Purpose","Value":"40"},{"Name":"ScoreType","Value":"08"},{"Name":"MemberCode","Value":"HF64117777_MUATC2CNPE"},{"Name":"Password","Value":"niu@gtlsEra7tsfxjnz"},{"Name":"FormattedReport","Value":"true"},{"Name":"GSTStateCode","Value":"09"}]}},{"Name":"IDV","Params":{"Param":[{"Name":"IDVerificationFlag","Value":"false"},{"Name":"ConsumerConsentForUIDAIAuthentication","Value":"N"},{"Name":"GSTStateCode","Value":"09"}]}},{"Name":"FIWaiver","Params":{"Param":[{"Name":"FIWaiver","Value":"false"}]}}]}}}}},"ApplicationData":{"GSTStateCode":"09","Services":{"Service":{"Id":"CORE","Skip":"N","Consent":"true"}}}}}


def submit_cibil_application(access_token: str):
    url = "https://www.test.transuniondecisioncentre.co.in/DC/TUCL/TU.DE.Pont/Applications"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.post(url, headers=headers, json=user_data)
        response.raise_for_status()
        result = response.json()

        ApplicantLastName = user_data["Fields"]["Applicants"]["Applicant"]["ApplicantLastName"]
        PanNumber = user_data["Fields"]["Applicants"]["Applicant"]["Identifiers"]["Identifier"][0]["IdNumber"]

        # Document ID extract
        document_id = None
        try:
            services = result['Fields']['Applicants']['Applicant']['Services']['Service']

            # Service can be list or dict
            if isinstance(services, list):
                for service in services:
                    operations = service.get('Operations', {}).get('Operation', [])
                    for operation in operations:
                        document = operation.get('Data', {}).get('Response', {}).get('RawResponse', {}).get('Document')
                        if document and 'Id' in document:
                            document_id = document['Id']
                            break
                    if document_id:
                        break
            elif isinstance(services, dict):
                operations = services.get('Operations', {}).get('Operation', [])
                for operation in operations:
                    document = operation.get('Data', {}).get('Response', {}).get('RawResponse', {}).get('Document')
                    if document and 'Id' in document:
                        document_id = document['Id']
                        break

        except KeyError:
            document_id = None

        # Return original response + extracted document id
        return document_id,ApplicantLastName,PanNumber

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def get_value(soup, label):
    cell = soup.find("td", string=lambda x: x and label.lower() in x.lower())
    if not cell:
        return None
    return cell.find_next_sibling("td").get_text(strip=True)


def delete_pdf_file(filename):
    """
    Deletes a file from /Czentrix/apps/wonder_homes_loan_bot/documents
    """

    try:
        # Security: remove any path traversal
        safe_filename = os.path.basename(filename)

        file_path = os.path.join(PDF_STORAGE_PATH, safe_filename)

        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": "File not found",
                "file": safe_filename
            }

        os.remove(file_path)

        return {
            "status": "success",
            "message": "File deleted successfully",
            "file": safe_filename
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to delete file",
            "details": str(e)
        }

def fetch_transunion_report_pdf(document_id, access_token,output_pdf_file):
    TU_URL = f"https://www.test.transuniondecisioncentre.co.in/DC/TUcl/TU.DE.Pont/documents/{document_id}"

    HEADERS = {
        "Authorization": f"Bearer {access_token}"
    }

    # Create folder if not exists
    os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

    output_pdf = os.path.join(PDF_STORAGE_PATH, f"{output_pdf_file}")

    r = requests.get(TU_URL, headers=HEADERS, timeout=60)
    r.raise_for_status()

    html_content = r.text

    # ---------- Fix UTF-16 / XML encoding ----------
    if html_content.startswith("<?xml"):
        html_content = html_content.encode("utf-8", "ignore").decode("utf-8")

    # ---------- Save temp HTML ----------
    temp_html = f"/tmp/tu_{document_id}.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    # ---------- wkhtmltopdf options ----------
    options = {
        'page-size': 'A4',
        'margin-top': '10mm',
        'margin-right': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
        'disable-smart-shrinking': ''
    }

    # ---------- Convert to PDF ----------
    pdfkit.from_file(temp_html, output_pdf, options=options)

    os.remove(temp_html)

    return output_pdf

@app.get("/download/cibil")
def download_cibil_report(file: str = Query(...)):
    # security: no folder traversal
    safe_file = os.path.basename(file)

    file_path = os.path.join(PDF_STORAGE_PATH, safe_file)

    if not os.path.exists(file_path):
        return {
            "status": "error",
            "message": "Documents not found"
        }

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_file
    )

# =====================================================
# MAIN API
# =====================================================
@app.post("/chat/process")
async def chat_process(req: Request):
    body = await req.json()
    wa_no = body.get("wa_numer")
    msg = body.get("message", "").strip()
    extraParms = body.get("extraParms")
    csid_data = json.loads(extraParms)
    wa = csid_data.get("identifier")
    cmd = msg.upper()

    print(msg,"============",type(msg))

    if isinstance(msg, str) and "screen_0_Name_0" in msg:
        save_user(wa, {"name": msg, "step": "REFER_FRND"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "You’re all set!\n\nYour details have been successfully submitted to our verification team. Our experts will review your information and connect with you shortly to guide you through the next steps.\n\n📞 Please keep your phone handy—you’ll be hearing from us soon!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload



    # -------- GLOBAL COMMANDS --------
    if cmd == "RESTART":
        reset_flow(wa, clear_mobile=True) # Full reset including mobile
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Welcome to Wonder Home Finance Limited.\n\nThis is Citra, your personal virtual assistant. Our Home Loan products are designed to meet your specific needs. To ensure you get the best experience, please select the below language to start."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                        "id": "English",
                        "title": "English",
                        "value": "English"
                        },
                        {
                        "id": "Hindi",
                        "title": "Hindi",
                        "value": "Hindi"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    user = get_user(wa)

    if user and is_session_expired(user):
        reset_flow(wa) # Preserve mobile, reset steps
        user = get_user(wa)

    if not user:
        reset_flow(wa, clear_mobile=True)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Welcome to Wonder Home Finance Limited.\n\nThis is Citra, your personal virtual assistant. Our housing finance products are designed to meet your specific needs. To ensure you get the best experience, please select the below language to start."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "English",
                            "title": "English",
                            "value": "English"
                        },
                        {
                            "id": "Hindi",
                            "title": "Hindi",
                            "value": "Hindi"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload

    step = user["step"]

    try:
        tmp_step = user["tmp_step"]
    except:
        tmp_step = ""

    print(msg,"+++++++++",step,"=============",tmp_step)
    existing_mobile = user.get("mobile") if user else None

    if step == "LANG" and msg.lower() in ["hii", "hi", "hey", "hello","Root","root","start","Start"]:
        reset_flow(wa)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Welcome to Wonder Home Finance Limited.\n\nThis is Citra, your personal virtual assistant. Our Home Loan products are designed to meet your specific needs. To ensure you get the best experience, please select the below language to start."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "English",
                            "title": "English",
                            "value": "English"
                        },
                        {
                            "id": "Hindi",
                            "title": "Hindi",
                            "value": "Hindi"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload


    if not existing_mobile and msg.lower() in ["hii", "hi", "hey", "hello","Root","root","start","Start"] and msg:
        reset_flow(wa)  # No mobile to preserve

        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Welcome to Wonder Home Finance Limited.\n\nThis is Citra, your personal virtual assistant. Our Home Loan products are designed to meet your specific needs. To ensure you get the best experience, please select the below language to start."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "English",
                            "title": "English",
                            "value": "English"
                        },
                        {
                            "id": "Hindi",
                            "title": "Hindi",
                            "value": "Hindi"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload



    if step == "LANG" and msg == "Branch Locator":
        reset_flow(wa)
        data = send_whatsapp_cta_template(
            wa,
            "branchlocator"
        )
        time.sleep(4)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    existing_smsRecordId = user.get("smsRecordId") if user else None
    if existing_mobile and msg.lower() in ["hii", "hi", "hey", "hello","Root","root","start","Start"] and msg:
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0,"tmp_step": ""})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "REFER_FRND" and msg == "Back To Menu":
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        print("==============================",customerName)
        save_user(wa, {"name": msg, "step": "EC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For Top Up Loan",
                            "title": "Apply For Top Up Loan",
                            "value": "Apply For Top Up Loan"
                        },
                        {
                            "id": "My Loans",
                            "title": "My Loans",
                            "value": "My Loans"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Documents",
                            "title": "Documents",
                            "value": "Documents"
                        },
                        {
                            "id": "Install WHFL App",
                            "title": "Install WHFL App",
                            "value": "Install WHFL App"
                        },
                        {
                            "id": "Pay EMI Now",
                            "title": "Pay EMI Now",
                            "value": "Pay EMI Now"
                        },
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Refer a Friend",
                            "title": "Refer a Friend",
                            "value": "Refer a Friend"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload

    if step == "EXISTING_DOC_MENU" and msg == "Back To Menu":
        save_user(wa, {"step": "DOC_MENU", "tmp_step": ""})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Please choose the type of document you would like to download from the list below."
                },
                {
                    "type": "Button",
                    "id": "Documents",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Interest Certificate",
                            "title": "Interest Certificate",
                            "value": "Interest Certificate"
                        },
                        {
                            "id": "Repayment Schedule",
                            "title": "Repayment Schedule",
                            "value": "Repayment Schedule"
                        },
                        {
                            "id": "Welcome Letter",
                            "title": "Welcome Letter",
                            "value": "Welcome Letter"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "DOC_MENU" and msg == "Contact Us":
        save_user(wa, {"step": "EXISTING_DOC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for reaching out.\n\nFor assistance with this request, please contact our customer support team at 1800 102 1002 or email us at hello@wonderhfl.com.\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload


    if msg in CRITICAL_ISSUES_WHATSAPP_BUTTONS and step != "DOC_MENU":
        critical_issue = check_critical_issue(msg)
        if critical_issue:
            save_user(wa, {"step": "MAIN_MENU"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Hi 👋\n\nWe are connecting you to a live agent.\n\nPlease wait for a moment while we transfer your chat.\n\nThank you for your patience 😊"
                    },

                ],
                "actions": [

                ]
            }
            return payload


    if msg == "Main Menu":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    if msg == "Calculators" and step == "MAIN_MENU":
        data = send_whatsapp_cta_template(
            wa,
            "calculators"
        )
        time.sleep(4)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    if msg == "Track Loan Status" and step == "NEW_LOAN_MENU":
        reset_flow(wa)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                "type": "TextBlock",
                "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                "type": "TextBlock",
                "text": "Tap the Visit Website button below to view the branch nearest to your location."
                },
                {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {
                    "id": "Visit website",
                    "title": "Visit website",
                    "value": "Visit website"
                    },
                    {
                    "id": "Back To Menu",
                    "title": "Back To Menu",
                    "value": "Back To Menu"
                    },
                    {
                    "id": "Main Menu",
                    "title": "Main Menu",
                    "value": "Main Menu"
                    }
                ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    if msg == "Back To Menu" and step == "EC_MENU" and tmp_step == "MY_LOAN":
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        save_user(wa, {"step": "EC_MENU", "tmp_step": "MY_LOAN"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For Top Up Loan",
                            "title": "Apply For Top Up Loan",
                            "value": "Apply For Top Up Loan"
                        },
                        {
                            "id": "My Loans",
                            "title": "My Loans",
                            "value": "My Loans"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Documents",
                            "title": "Documents",
                            "value": "Documents"
                        },
                        {
                            "id": "Install WHFL App",
                            "title": "Install WHFL App",
                            "value": "Install WHFL App"
                        },
                        {
                            "id": "Pay EMI Now",
                            "title": "Pay EMI Now",
                            "value": "Pay EMI Now"
                        },
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Refer a Friend",
                            "title": "Refer a Friend",
                            "value": "Refer a Friend"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload


    if msg == "Back To Menu" and step == "LANG":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "MAIN_MENU":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "NP_PAN" and msg == "Back To Menu":
        save_user(wa, {"step": "MAIN_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "By providing your information, you consent to Wonder Home Finance to be contacted via SMS or Whatsapp or Email or phone calls for marketing and information purposes."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Proceed",
                            "title": "Proceed",
                            "value": "Proceed"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload



    if step == "NEW_LOAN_MENU" and msg == "Back To Menu":
        save_user(wa, {"step": "MAIN_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "MAIN_MENU":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "EC_MENU":
        save_user(wa, {"step": "MAIN_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "Contact_Us":
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        save_user(wa, {"step": "EC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For Top Up Loan",
                            "title": "Apply For Top Up Loan",
                            "value": "Apply For Top Up Loan"
                        },
                        {
                            "id": "My Loans",
                            "title": "My Loans",
                            "value": "My Loans"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Documents",
                            "title": "Documents",
                            "value": "Documents"
                        },
                        {
                            "id": "Install WHFL App",
                            "title": "Install WHFL App",
                            "value": "Install WHFL App"
                        },
                        {
                            "id": "Pay EMI Now",
                            "title": "Pay EMI Now",
                            "value": "Pay EMI Now"
                        },
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Refer a Friend",
                            "title": "Refer a Friend",
                            "value": "Refer a Friend"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload

    if msg == "Back To Menu" and step == "DOC_MENU" and tmp_step == "DOC_TYPE" :
        save_user(wa, {"step": "DOC_MENU", "tmp_step": ""})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Please choose the type of document you would like to download from the list below."
                },
                {
                    "type": "Button",
                    "id": "Documents",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Interest Certificate",
                            "title": "Interest Certificate",
                            "value": "Interest Certificate"
                        },
                        {
                            "id": "Repayment Schedule",
                            "title": "Repayment Schedule",
                            "value": "Repayment Schedule"
                        },
                        {
                            "id": "Welcome Letter",
                            "title": "Welcome Letter",
                            "value": "Welcome Letter"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "DOC_MENU":
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        save_user(wa, {"step": "EC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For Top Up Loan",
                            "title": "Apply For Top Up Loan",
                            "value": "Apply For Top Up Loan"
                        },
                        {
                            "id": "My Loans",
                            "title": "My Loans",
                            "value": "My Loans"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Documents",
                            "title": "Documents",
                            "value": "Documents"
                        },
                        {
                            "id": "Install WHFL App",
                            "title": "Install WHFL App",
                            "value": "Install WHFL App"
                        },
                        {
                            "id": "Pay EMI Now",
                            "title": "Pay EMI Now",
                            "value": "Pay EMI Now"
                        },
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Refer a Friend",
                            "title": "Refer a Friend",
                            "value": "Refer a Friend"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload

    if msg == "Back To Menu" and step == "CRITCAL_CASE":
        data = send_whatsapp_cta_template(
            wa,
            "fqa_wonder_home"
        )
        time.sleep(4)
        save_user(wa, {"step": "CUSTOMER_SUPPORT"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Do you need any further assistance?\n\nPlease select an option below:"
                },
                {
                    "type": "Button",
                    "id": "faqCategory",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Yes",
                            "title": "Yes",
                            "value": "Yes"
                        },
                        {
                            "id": "No",
                            "title": "No",
                            "value": "No"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if msg == "Customer Support" and step != "Back To Menu":
        data = send_whatsapp_cta_template(
            wa,
            "fqa_wonder_home"
        )
        time.sleep(4)
        save_user(wa, {"step": "CUSTOMER_SUPPORT"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Do you need any further assistance?\n\nPlease select an option below:"
                },
                {
                    "type": "Button",
                    "id": "faqCategory",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Yes",
                            "title": "Yes",
                            "value": "Yes"
                        },
                        {
                            "id": "No",
                            "title": "No",
                            "value": "No"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if step == "CUSTOMER_SUPPORT" and msg == "No":
        save_user(wa, {"step": "CRITCAL_CASE"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    if step == "LANG" and  msg == "No":
        reset_flow(wa)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    # =====================================================
    # LANGUAGE / START
    # =====================================================
    existing_smsRecordId = user.get("smsRecordId") if user else None
    if not existing_smsRecordId:
        if step == "LANG":
            if msg in ["English", "Hindi"]:
                save_user(wa, {"step": "ASK_MOBILE", "attempt": 0})
                payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                        }
                    ],
                    "actions": [
                    ]
                }
                return payload

            payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                        }

                    ],
                    "actions": [
                    ]
            }
            return payload


        if msg == "Change Number" and step == "OTP_FAILED_MENU":
            save_user(wa, {"step": "ASK_MOBILE", "attempt": 0})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                    }
                ],
                "actions": [
                ]
            }

            return payload

    if step == "OTP" and msg == "Change Number":
        save_user(wa, {"step": "ASK_MOBILE", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                }
            ],
            "actions": []
        }

        return payload

    if step == "OTP" and msg == "RESEND OTP":
        stored_mobile = user.get("mobile")
        if stored_mobile:
            otp_res = generate_otp(stored_mobile)
            if otp_res.get("operationStatus") == "1":
                save_user(wa, {
                    "smsRecordId": otp_res.get("smsRecordId"),
                    "step": "OTP",
                    "attempt": 0
                })
                payload = payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Your One-Time Password (OTP) has been resent successfully on your provided number Please enter the valid OTP to proceed.\n\nIf you have entered an incorrect mobile number, you can change it, or you can request to resend the OTP."
                        },
                        {
                            "type": "Button",
                            "id": "serviceType",
                            "style": "expanded",
                            "choices": [
                                {
                                    "id": "Change Number",
                                    "title": "Change Number",
                                    "value": "Change Number"
                                },
                                {
                                    "id": "RESEND OTP",
                                    "title": "RESEND OTP",
                                    "value": "RESEND OTP"
                                }
                            ]
                        }
                    ],
                    "actions": []
                }
                return payload

        if attempt_failed(user, wa):
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                    }
                ],
                "actions": [
                ]
            }

            return payload
        return {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Invalid response. Please choose from the options shared below."
                    }
                ],
                "actions": [
                ]
            }

    # =====================================================
    # MOBILE COLLECTION
    # =====================================================
    if step == "ASK_MOBILE":
        if msg.isdigit() and len(msg) == 10:
            otp_res = generate_otp(msg)
            if otp_res.get("operationStatus") == "1":
                save_user(wa, {"mobile": msg, "smsRecordId": otp_res.get("smsRecordId"), "step": "OTP", "attempt": 0})
                payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Your One-Time Password (OTP) has been sent successfully on your provided number Please enter the valid OTP to proceed.\n\nIf you have entered an incorrect mobile number, you can change it, or you can request to resend the OTP."
                        },
                        {
                            "type": "Button",
                            "id": "serviceType",
                            "style": "expanded",
                            "choices": [
                                {
                                    "id": "Change Number",
                                    "title": "Change Number",
                                    "value": "Change Number"
                                },
                                {
                                    "id": "RESEND OTP",
                                    "title": "RESEND OTP",
                                    "value": "RESEND OTP"
                                }
                            ]
                        }
                    ],
                    "actions": []
                }
                return payload


        if attempt_failed(user, wa):
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                    }
                ],
                "actions": [
                ]
            }

            return payload

        return {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Invalid response. Please choose from the options shared below."
                    }
                ],
                "actions": [
                ]
            }

    elif step == "OTP_FAILED_MENU" and msg == "RESEND OTP":
        stored_mobile = user.get("mobile")
        if stored_mobile:
            otp_res = generate_otp(stored_mobile)
            if otp_res.get("operationStatus") == "1":
                save_user(wa, {
                    "smsRecordId": otp_res.get("smsRecordId"),
                    "step": "OTP",
                    "attempt": 0
                })
                payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Your One-Time Password (OTP) has been resent successfully on your provided number Please enter the valid OTP to proceed.\n\nIf you have entered an incorrect mobile number, you can change it, or you can request to resend the OTP."
                        },
                        {
                            "type": "Button",
                            "id": "serviceType",
                            "style": "expanded",
                            "choices": [
                                {
                                    "id": "Change Number",
                                    "title": "Change Number",
                                    "value": "Change Number"
                                },
                                {
                                    "id": "RESEND OTP",
                                    "title": "RESEND OTP",
                                    "value": "RESEND OTP"
                                }
                            ]
                        }
                    ],
                    "actions": []
                }
                return payload

        if attempt_failed(user, wa):
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
                    }
                ],
                "actions": [
                ]
            }

            return payload
        return {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Invalid response. Please choose from the options shared below."
                    }
                ],
                "actions": [
                ]
            }

    # =====================================================
    # OTP VERIFICATION
    # =====================================================
    if step == "OTP":
        res = validate_otp(user["smsRecordId"], msg)
        if res.get("operationStatus") == "1":
            save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Thanks’ For Submitting the OTP!\n\nI'll be glad to assist you, please select the option from below."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Apply For New Loan",
                                "title": "Apply For New Loan",
                                "value": "Apply For New Loan"
                            },
                            {
                                "id": "Existing Customer",
                                "title": "Existing Customer",
                                "value": "Existing Customer"
                            },
                            {
                                "id": "Branch Locator",
                                "title": "Branch Locator",
                                "value": "Branch Locator"
                            },
                            {
                                "id": "Calculators",
                                "title": "Calculators",
                                "value": "Calculators"
                            },
                            {
                                "id": "Customer Support",
                                "title": "Customer Support",
                                "value": "Customer Support"
                            }
                        ]
                    }
                ],
                "actions": [

                ]
            }
            return payload

        if attempt_failed(user, wa):
            save_user(wa, {"step": "OTP_FAILED_MENU", "attempt": 0})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "You have entered an incorrect OTP three times. You can request a new OTP to try again, or update your mobile number if you wish to use a different one."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Change Number",
                                "title": "Change Number",
                                "value": "Change Number"
                            },
                            {
                                "id": "RESEND OTP",
                                "title": "RESEND OTP",
                                "value": "RESEND OTP"
                            }
                        ]
                    }
                ],
                "actions": [
                ]
            }

            return payload


        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Invalid OTP entered. For secure verification, please re-enter the correct OTP."
                }
            ],
            "actions": [
            ]
        }

        return payload


    if step == "Apply_For_Top_Up_Loan" and msg == "Back To Menu":
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        save_user(wa, {"step": "EC_MENU", "tmp_step": ""})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For Top Up Loan",
                            "title": "Apply For Top Up Loan",
                            "value": "Apply For Top Up Loan"
                        },
                        {
                            "id": "My Loans",
                            "title": "My Loans",
                            "value": "My Loans"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Documents",
                            "title": "Documents",
                            "value": "Documents"
                        },
                        {
                            "id": "Install WHFL App",
                            "title": "Install WHFL App",
                            "value": "Install WHFL App"
                        },
                        {
                            "id": "Pay EMI Now",
                            "title": "Pay EMI Now",
                            "value": "Pay EMI Now"
                        },
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Refer a Friend",
                            "title": "Refer a Friend",
                            "value": "Refer a Friend"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "Apply_For_Top_Up_Loan":
        save_user(wa, {"name": msg, "step": "Apply_For_Top_Up_Loan"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "You’re all set!\n\nYour details have been successfully submitted to our verification team. Our experts will review your information and connect with you shortly to guide you through the next steps.\n\n📞 Please keep your phone handy—you’ll be hearing from us soon!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload

    if step == "EC_MENU" and msg == "Apply For Top Up Loan":
        save_user(wa, {"name": msg, "step": "Apply_For_Top_Up_Loan"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Enter the top-up loan amount you want to apply for."
                }
            ],
            "actions": []
        }
        return payload

    if step == "EC_MENU" and msg == "Refer a Friend":
        save_user(wa, {"name": msg, "step": "EC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "flow",
                    "id": "referfriend",
                    "style": "expanded",
                    "flow": {
                        "name": "refer_friend",
                        "language": {
                        "code": "en"
                        },
                        "components": [
                        {
                            "type": "button",
                            "sub_type": "flow",
                            "index": "0",
                            "parameters": [
                            {
                                "type": "action",
                                "action": {
                                "flow_token": "123"
                                }
                            }
                            ]
                        }
                        ]
                    }
                }
            ],
            "actions": []
        }
        return payload


    # =====================================================
    # MAIN MENU
    # =====================================================

    if step == "MAIN_MENU":
        if msg == "Apply For New Loan":
            save_user(wa, {"step": "NEW_LOAN_MENU"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "By providing your information, you consent to Wonder Home Finance to be contacted via SMS or Whatsapp or Email or phone calls for marketing and information purposes."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Proceed",
                                "title": "Proceed",
                                "value": "Proceed"
                            }
                        ]
                    }
                ],
                "actions": []
            }
            return payload


        if msg == "Existing Customer":
            filename = "existing-loan-details-8076893187.pdf"
            file_path = f"{PDF_STORAGE_PATH}/{filename}"
            loan_data = get_loan_details("8076893187")
            loan_rows = extract_loan_details(loan_data)

            create_loan_details_pdf(loan_rows, file_path)

            pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file={filename}"
            tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,filename)
            print(tmp_data,"ttttttttttttt")
            loan_data = {
                    "operationStatus": "1"
            }
            if loan_data["operationStatus"] == "1":
                res = get_all_loan("8076893187")
                reply_text,customerName = format_loans_for_whatsapp(res)
                save_user(wa, {"step": "EC_LOAN"})
                payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Hi {customerName}, please find below the summary of your active home loan account with us.\n\n{reply_text} \n\nEnter the last 5 digits of your loan account number for more details."
                        }
                    ],
                    "actions": [
                    ]
                }
                return payload
            else:
                payload = {
                    "type": "adaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Based on the information provided, there is currently no existing loan associated with your profile in our records. If you require any further assistance or clarification, please feel free to reach out."
                        },
                        {
                            "type": "Button",
                            "id": "serviceType",
                            "style": "expanded",
                            "choices": [
                                {
                                    "id": "Main Menu",
                                    "title": "Main Menu",
                                    "value": "Main Menu"
                                },
                                {
                                    "id": "Back To Menu",
                                    "title": "Back To Menu",
                                    "value": "Back To Menu"
                                }
                            ]
                        }
                    ],
                    "actions": [
                    ]
                }
                return payload

        if msg == "Branch Locator":
            reset_flow(wa)
            data = send_whatsapp_cta_template(
                wa,
                "branchlocator"
            )
            time.sleep(4)
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Customer Support",
                                "title": "Customer Support",
                                "value": "Customer Support"
                            },
                            {
                                "id": "Back To Menu",
                                "title": "Back To Menu",
                                "value": "Back To Menu"
                            },
                            {
                                "id": "Main Menu",
                                "title": "Main Menu",
                                "value": "Main Menu"
                            }
                        ]
                    }
                ],
                "actions": [
                ]
            }
            return payload

    if step == "CRITCAL_CASE" and msg == "Contact Us":
        save_user(wa, {"step": "CRITCAL_CASE"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for reaching out.\n\nFor assistance with this request, please contact our customer support team at 1800 102 1002 or email us at hello@wonderhfl.com.\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload

    if step == "CRITCAL_CASE" and msg == "Others":
        save_user(wa, {"step": "CRITCAL_CASE"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for reaching out.\n\nFor assistance with this request, please contact our customer support team at 1800 102 1002 or email us at hello@wonderhfl.com.\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Misconduct by WHFL",
                            "title": "Misconduct by WHFL",
                            "value": "Misconduct by WHFL"
                        },
                        {
                            "id": "Miscommunication",
                            "title": "Miscommunication",
                            "value": "Miscommunication"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload

    if step == "CUSTOMER_SUPPORT" and msg == "Yes":
        save_user(wa, {"step": "CRITCAL_CASE"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Welcome to Wonder Home Finance Customer Support.\n\nPlease select the service request that best matches your concern. Our support team will assist you accordingly."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "FCL/SOA/LOD Request",
                            "title": "FCL / SOA / LOD Request",
                            "value": "FCL / SOA / LOD Request"
                        },
                        {
                            "id": "EMI/ Pre-EMI Related",
                            "title": "EMI / Pre-EMI Related",
                            "value": "EMI/ Pre-EMI Related"
                        },
                        {
                            "id": "Refund",
                            "title": "Refund",
                            "value": "Refund"
                        },
                        {
                            "id": "ROI/Tenure Miscomm",
                            "title": "ROI/Tenure Miscomm",
                            "value": "ROI/Tenure Miscomm"
                        },
                        {
                            "id": "Cibil related",
                            "title": "CIBIL Related",
                            "value": "Cibil related"
                        },
                        {
                            "id": "Amount Taken in Emp. A/C",
                            "title": "Amount Taken in Emp. A/C",
                            "value": "Amount Taken in Emp. A/C"
                        },
                        {
                            "id": "Others",
                            "title": "Others",
                            "value": "Others"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload


    if msg in ["Balance Transfer","Home Construction Loan","Home Extension Loan","Home Loan General","Home Renovation Loan"] and step == "CUSTOMER_SUPPORT":
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"We hope your query has been addressed.\n\nIf you need any further assistance, please select *Yes*.\n\nThank you for choosing Wonder Home Finance."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Yes",
                            "title": "Yes",
                            "value": "Yes"
                        },
                        {
                            "id": "No",
                            "title": "No",
                            "value": "No"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if msg == "Main_Menu" and step == "NP_LOAN_TYPE":
        save_user(wa, {"step": "MAIN_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    # =====================================================
    # NEW LOAN FLOW
    # =====================================================
    if step == "NEW_LOAN_MENU" or msg != "Back To Menu":
        if msg == "Proceed":
            save_user(wa, {"step": "NP_NAME"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                    "type": "TextBlock",
                    "text": "Please enter your full name."
                    }
                ],
                "actions": [
                ]
            }
            return payload

        if msg == "BACK TO MENU":
            save_user(wa, {"step": "MAIN_MENU"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "I'll be glad to assist you, please select the option from below."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Apply For New Loan",
                                "title": "Apply For New Loan",
                                "value": "Apply For New Loan"
                            },
                            {
                                "id": "Existing Customer",
                                "title": "Existing Customer",
                                "value": "Existing Customer"
                            },
                            {
                                "id": "Branch Locator",
                                "title": "Branch Locator",
                                "value": "Branch Locator"
                            },
                            {
                                "id": "Calculators",
                                "title": "Calculators",
                                "value": "Calculators"
                            },
                            {
                                "id": "Customer Support",
                                "title": "Customer Support",
                                "value": "Customer Support"
                            }
                        ]
                    }
                ],
                "actions": [

                ]
            }
            return payload

    if step == "NP_NAME":
        save_user(wa, {"name": msg, "step": "NP_PAN"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Thanks, {msg}! Which of these loan options would you like to explore today?"
                },
                {
                    "type": "Button",
                    "id": "loanType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Home Purchase Loan",
                            "title": "Home Purchase Loan",
                            "value": "Home Purchase Loan"
                        },
                        {
                            "id": "Plot Pur. + Construction",
                            "title": "Plot Pur. + Construction",
                            "value": "Plot Pur. + Construction"
                        },
                        {
                            "id": "Home Renovation Loan",
                            "title": "Home Renovation Loan",
                            "value": "Home Renovation Loan"
                        },
                        {
                            "id": "Home Extension Loan",
                            "title": "Home Extension Loan",
                            "value": "Home Extension Loan"
                        },
                        {
                            "id": "Loan Against Property",
                            "title": "Loan Against Property",
                            "value": "Loan Against Property"
                        },
                        {
                            "id": "Balance Transfer",
                            "title": "Balance Transfer",
                            "value": "Balance Transfer"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if step == "NP_PAN":
        save_user(wa, {"name": msg, "step": "NP_FLOW"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "flow",
                    "id": "loanApplication",
                    "style": "expanded",
                    "flow": {
                        "name": "apply_loan_application",
                        "language": {
                        "code": "en"
                        },
                        "components": [
                        {
                            "type": "button",
                            "sub_type": "flow",
                            "index": "0",
                            "parameters": [
                            {
                                "type": "action",
                                "action": {
                                "flow_token": "123"
                                }
                            }
                            ]
                        }
                        ]
                    }
                }
            ],
            "actions": []
        }
        return payload

    if step == "NP_FLOW":
        if isinstance(msg, str):
            msg = json.loads(msg)
            print(msg,"llllllllllllllllll")

        pan = msg.get("screen_0_Enter_Pan_No_1")
        response = verify_pan(pan)
        status_code = response.get("status-code")
        if status_code == "101":
            user_data = get_user(wa)
            access_token = generate_transunion_token()
            document_id,ApplicantLastName,PanNumber = submit_cibil_application(access_token)
            cibil_report = "cibil_report_" + ApplicantLastName + "_" + PanNumber +".pdf"
            fetch_transunion_report_pdf(document_id,access_token,cibil_report)
            pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file={cibil_report}"
            tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,cibil_report)

            save_user(wa, {"step": "MAIN_MENU"})
            time.sleep(4)
            # delete_pdf_file(cibil_report)
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": f"Dear {ApplicantLastName},\n\n"
                        f"Thank you for applying for a loan with Wonder Homes Finance.\n\n"
                        f"Your application details have been successfully submitted to our verification team. Our experts will review your information and contact you shortly regarding the next steps in the loan process.\n\n"
                        f"📞 Please keep your phone handy — our team may reach out soon.\n\n"
                        f"Your CIBIL report and eligibility update will be shared with you on WhatsApp shortly.\n\n"
                        f"Regards,\n"
                        f"Wonder Homes Finance Team"
                    },
                    {
                        "type": "Button",
                        "id": "postApplicationOptions",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Customer Support",
                                "title": "Customer Support",
                                "value": "Customer Support"
                            },
                            {
                                "id": "Back To Menu",
                                "title": "Back To Menu",
                                "value": "Back To Menu"
                            },
                            {
                                "id": "Main Menu",
                                "title": "Main Menu",
                                "value": "Main Menu"
                            }
                        ]
                    }
                ],
                "actions": [
                ]
            }
            return payload
        else:
            data = send_whatsapp_cta_template(
                wa,
                "pan_verify_wonder_home"
            )
            time.sleep(4)
            save_user(wa, {"name": msg, "step": "NP_FLOW"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Oops! It looks like there’s a small error with the PAN Number. Could you please double check the details and try again? We want to make sure your application is perfect."
                    },
                    {
                        "type": "flow",
                        "id": "loanApplication",
                        "style": "expanded",
                        "flow": {
                            "name": "apply_loan_application",
                            "language": {
                            "code": "en"
                            },
                            "components": [
                            {
                                "type": "button",
                                "sub_type": "flow",
                                "index": "0",
                                "parameters": [
                                {
                                    "type": "action",
                                    "action": {
                                    "flow_token": "123"
                                    }
                                }
                                ]
                            }
                            ]
                        }
                    }
                ],
                "actions": []
            }
            return payload


    if step == "MAIN_MENU" and msg == "Customer Support":
        data = send_whatsapp_cta_template(
            wa,
            "fqa_wonder_home"
        )
        time.sleep(4)
        save_user(wa, {"step": "CUSTOMER_SUPPORT"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Do you need any further assistance?\n\nPlease select an option below:"
                },
                {
                    "type": "Button",
                    "id": "faqCategory",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Yes",
                            "title": "Yes",
                            "value": "Yes"
                        },
                        {
                            "id": "No",
                            "title": "No",
                            "value": "No"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if step == "MAIN_MENU" and msg == "Main Menu":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "EC_MENU" and msg == "Customer Support":
        data = send_whatsapp_cta_template(
            wa,
            "fqa_wonder_home"
        )
        time.sleep(4)
        save_user(wa, {"step": "CUSTOMER_SUPPORT"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Do you need any further assistance?\n\nPlease select an option below:"
                },
                {
                    "type": "Button",
                    "id": "faqCategory",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Yes",
                            "title": "Yes",
                            "value": "Yes"
                        },
                        {
                            "id": "No",
                            "title": "No",
                            "value": "No"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload


    if step == "EC_MENU" and msg == "Main Menu":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "EC_MENU" and msg == "My Loans":
        filename = "existing-loan-details-8076893187.pdf"
        file_path = f"{PDF_STORAGE_PATH}/{filename}"
        loan_data = get_loan_details("8076893187")
        loan_rows = extract_loan_details(loan_data)

        create_loan_details_pdf(loan_rows, file_path)

        pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file={filename}"
        tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,filename)
        res = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res)
        save_user(wa, {"tmp_step": "MY_LOAN"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"{reply_text}"
                },
                {
                    "type": "Button",
                    "id": "interestcertificate",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if step == "EC_MENU" and msg == "Branch Locator":
        save_user(wa, {"step": "MAIN_MENU"})
        data = send_whatsapp_cta_template(
            wa,
            "branchlocator"
        )
        time.sleep(4)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload

    if step == "EC_LOAN" and msg == "Contact Us":
        save_user(wa, {"step": "Contact_Us"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📞 Call us at 1800-102-1002\n\n📧 Email us at hello@wonderhfl.com\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload


    if step == "NEW_LOAN_MENU" and msg == "Contact Us":
        save_user(wa, {"step": "Contact_Us"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📞 Call us at 1800-102-1002\n\n📧 Email us at hello@wonderhfl.com\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [
            ]
        }
        return payload


    if step == "CUSTOMER_SUPPORT" and msg == "Contact Us":
        save_user(wa, {"step": "Contact_Us"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📞 Call us at 1800-102-1002\n\n📧 Email us at hello@wonderhfl.com\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    if step == "EC_MENU" and msg == "Contact Us":
        save_user(wa, {"step": "Contact_Us"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📞 Call us at 1800-102-1002\n\n📧 Email us at hello@wonderhfl.com\n\nOur team will be happy to help you."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Documents" and step == "EC_MENU":
        save_user(wa, {"step": "DOC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Please choose the type of document you would like to download from the list below."
                },
                {
                    "type": "Button",
                    "id": "Documents",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Interest Certificate",
                            "title": "Interest Certificate",
                            "value": "Interest Certificate"
                        },
                        {
                            "id": "Repayment Schedule",
                            "title": "Repayment Schedule",
                            "value": "Repayment Schedule"
                        },
                        {
                            "id": "Welcome Letter",
                            "title": "Welcome Letter",
                            "value": "Welcome Letter"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload


    if msg == "Pay EMI Now" and step == "EC_MENU":
        save_user(wa, {"step": "EC_LOAN"})
        data = send_whatsapp_cta_template(
            wa,
            "payemi"
        )
        time.sleep(4)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload


    if msg == "Install WHFL App" and step == "EC_MENU":
        save_user(wa, {"step": "EC_LOAN"})
        data = send_whatsapp_cta_template(
            wa,
            "whfl_app"
        )
        time.sleep(4)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload


    if msg == "Back To Menu" and step == "DOC_MENU":
        save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thanks’ For Submitting the OTP!\n\nI'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "EC_LOAN":
        save_user(wa, {"step": "EC_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if msg == "Back To Menu" and step == "EC_MENU" and tmp_step == "TOP_UP":
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        save_user(wa, {"step": "EC_LOAN", "tmp_step": ""})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For Top Up Loan",
                            "title": "Apply For Top Up Loan",
                            "value": "Apply For Top Up Loan"
                        },
                        {
                            "id": "My Loans",
                            "title": "My Loans",
                            "value": "My Loans"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Documents",
                            "title": "Documents",
                            "value": "Documents"
                        },
                        {
                            "id": "Install WHFL App",
                            "title": "Install WHFL App",
                            "value": "Install WHFL App"
                        },
                        {
                            "id": "Pay EMI Now",
                            "title": "Pay EMI Now",
                            "value": "Pay EMI Now"
                        },
                        {
                            "id": "Contact Us",
                            "title": "Contact Us",
                            "value": "Contact Us"
                        },
                        {
                            "id": "Refer a Friend",
                            "title": "Refer a Friend",
                            "value": "Refer a Friend"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }

        return payload

    if msg == "Back To Menu" and step == "EC_LOAN":
        save_user(wa, {"step": "EC_MENU", "attempt": 0})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "I'll be glad to assist you, please select the option from below."
                },
                {
                    "type": "Button",
                    "id": "serviceType",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Apply For New Loan",
                            "title": "Apply For New Loan",
                            "value": "Apply For New Loan"
                        },
                        {
                            "id": "Existing Customer",
                            "title": "Existing Customer",
                            "value": "Existing Customer"
                        },
                        {
                            "id": "Branch Locator",
                            "title": "Branch Locator",
                            "value": "Branch Locator"
                        },
                        {
                            "id": "Calculators",
                            "title": "Calculators",
                            "value": "Calculators"
                        },
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    # =====================================================
    # EXISTING CUSTOMER FLOW
    # =====================================================
    if step == "EC_LOAN":
        res = validate_loan_with_crm("8076893187", msg)
        res_1 = get_all_loan("8076893187")
        reply_text,customerName = format_loans_for_whatsapp(res_1)
        print("==============================",customerName)
        if res["status"] == "MATCH":
            save_user(wa, {"step": "EC_MENU"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": f"Hi {customerName}, I'll be glad to assist you, please select the option from below."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Apply For Top Up Loan",
                                "title": "Apply For Top Up Loan",
                                "value": "Apply For Top Up Loan"
                            },
                            {
                                "id": "My Loans",
                                "title": "My Loans",
                                "value": "My Loans"
                            },
                            {
                                "id": "Branch Locator",
                                "title": "Branch Locator",
                                "value": "Branch Locator"
                            },
                            {
                                "id": "Documents",
                                "title": "Documents",
                                "value": "Documents"
                            },
                            {
                                "id": "Install WHFL App",
                                "title": "Install WHFL App",
                                "value": "Install WHFL App"
                            },
                            {
                                "id": "Pay EMI Now",
                                "title": "Pay EMI Now",
                                "value": "Pay EMI Now"
                            },
                            {
                                "id": "Contact Us",
                                "title": "Contact Us",
                                "value": "Contact Us"
                            },
                            {
                                "id": "Refer a Friend",
                                "title": "Refer a Friend",
                                "value": "Refer a Friend"
                            },
                            {
                                "id": "Back To Menu",
                                "title": "Back To Menu",
                                "value": "Back To Menu"
                            }
                        ]
                    }
                ],
                "actions": [

                ]
            }

            return payload
        else:
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "We are unable to verify the loan number with the registered mobile number. Kindly update your mobile number at the nearest branch or raise a request through the WHFL Mobile App for assistance."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Main Menu",
                                "title": "Main Menu",
                                "value": "Main Menu"
                            },
                            {
                                "id": "Back To Menu",
                                "title": "Back To Menu",
                                "value": "Back To Menu"
                            }
                        ]
                    }
                ],
                "actions": [

            ]
            }

            return payload

    if step == "DOC_MENU" and msg == "Mini SOA":
        pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file=cibil_report_BANSAL_DVWPB4941P.pdf"
        tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,"Interest_Certificate_LN29003HP22-23010778.pdf")
        save_user(wa, {"step": "DOC_MENU"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance! If you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "interestcertificate",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "DOC_MENU" and msg == "Interest Certificate":
        data = download_interest_certificate("LN29003HP22-23010778", "01-04-2024", "31-03-2025")

        pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file=Interest_Certificate_LN29003HP22-23010778.pdf"
        tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,"Interest_Certificate_LN29003HP22-23010778.pdf")
        time.sleep(4)
        # delete_pdf_file("Interest_Certificate_LN29003HP22-23010778.pdf")

        save_user(wa, {"step": "DOC_MENU", "tmp_step": "DOC_TYPE"})
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance! If you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "interestcertificate",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": [

            ]
        }
        return payload

    if step == "DOC_MENU" and msg == "Repayment Schedule":
        repayment_data = fetch_repayment_schedule("LN29003HP22-23010778")
        status = repayment_data["operationStatus"]
        if status == "1":
            emi_rows  = extract_main_fields(repayment_data)
            file_path = f"{PDF_STORAGE_PATH}/EMI_Schedule_LN29003HP22-23010778.pdf"
            create_emi_pdf("LN29003HP22-23010778", emi_rows, file_path)
            pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file=EMI_Schedule_LN29003HP22-23010778.pdf"
            tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,"EMI_Schedule_LN29003HP22-23010778.pdf")

            # delete_pdf_file("welcome_letter_LN29003HP22-23010778.pdf")

            save_user(wa, {"step": "DOC_MENU", "tmp_step": "DOC_TYPE"})
            time.sleep(4)
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Thank you for connecting with Wonder Home Finance! If you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                    },
                    {
                        "type": "Button",
                        "id": "interestcertificate",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Customer Support",
                                "title": "Customer Support",
                                "value": "Customer Support"
                            },
                            {
                                "id": "Back To Menu",
                                "title": "Back To Menu",
                                "value": "Back To Menu"
                            },
                            {
                                "id": "Main Menu",
                                "title": "Main Menu",
                                "value": "Main Menu"
                            }
                        ]
                    }
                ],
                "actions": []
            }
            return payload
        else:
            save_user(wa, {"step": "DOC_MENU", "tmp_step": "DOC_TYPE"})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "We are unable to fetch your Repayment Schedule at the moment due to a system authentication issue. Please try again after some time or contact customer support for assistance."
                    },
                    {
                        "type": "Button",
                        "id": "interestcertificate",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Contact Us",
                                "title": "Contact Us",
                                "value": "Contact Us"
                            },
                            {
                                "id": "Back To Menu",
                                "title": "Back To Menu",
                                "value": "Back To Menu"
                            },
                            {
                                "id": "Main Menu",
                                "title": "Main Menu",
                                "value": "Main Menu"
                            }
                        ]
                    }
                ],
                "actions": [

            ]
            }
            return payload

    if step == "DOC_MENU" and msg == "Welcome Letter":
        download_welcome_letter("LN29003HP22-23010778")
        pdf_url = f"https://api-retriever-bitnet.c-zentrix.com/download/cibil?file=welcome_letter_LN29003HP22-23010778.pdf"
        tmp_data = send_cibil_pdf_whatsapp(wa, pdf_url,"welcome_letter_LN29003HP22-23010778.pdf")

        # delete_pdf_file("welcome_letter_LN29003HP22-23010778.pdf")

        save_user(wa, {"step": "DOC_MENU", "tmp_step": "DOC_TYPE"})
        time.sleep(4)
        payload = {
            "type": "adaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Thank you for connecting with Wonder Home Finance! If you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
                },
                {
                    "type": "Button",
                    "id": "interestcertificate",
                    "style": "expanded",
                    "choices": [
                        {
                            "id": "Customer Support",
                            "title": "Customer Support",
                            "value": "Customer Support"
                        },
                        {
                            "id": "Back To Menu",
                            "title": "Back To Menu",
                            "value": "Back To Menu"
                        },
                        {
                            "id": "Main Menu",
                            "title": "Main Menu",
                            "value": "Main Menu"
                        }
                    ]
                }
            ],
            "actions": []
        }
        return payload

    if existing_mobile:
        if msg == "English" or msg == "english":
            save_user(wa, {"step": "MAIN_MENU", "attempt": 0})
            payload = {
                "type": "adaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "I'll be glad to assist you, please select the option from below."
                    },
                    {
                        "type": "Button",
                        "id": "serviceType",
                        "style": "expanded",
                        "choices": [
                            {
                                "id": "Apply For New Loan",
                                "title": "Apply For New Loan",
                                "value": "Apply For New Loan"
                            },
                            {
                                "id": "Existing Customer",
                                "title": "Existing Customer",
                                "value": "Existing Customer"
                            },
                            {
                                "id": "Branch Locator",
                                "title": "Branch Locator",
                                "value": "Branch Locator"
                            },
                            {
                                "id": "Calculators",
                                "title": "Calculators",
                                "value": "Calculators"
                            },
                            {
                                "id": "Customer Support",
                                "title": "Customer Support",
                                "value": "Customer Support"
                            }
                        ]
                    }
                ],
                "actions": [

                ]
            }
            return payload


    save_user(wa, {"step": "MAIN_MENU"})
    payload = {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "I'll be glad to assist you, please select the option from below."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {
                        "id": "Apply For New Loan",
                        "title": "Apply For New Loan",
                        "value": "Apply For New Loan"
                    },
                    {
                        "id": "Existing Customer",
                        "title": "Existing Customer",
                        "value": "Existing Customer"
                    },
                    {
                        "id": "Branch Locator",
                        "title": "Branch Locator",
                        "value": "Branch Locator"
                    },
                    {
                        "id": "Calculators",
                        "title": "Calculators",
                        "value": "Calculators"
                    },
                    {
                        "id": "Customer Support",
                        "title": "Customer Support",
                        "value": "Customer Support"
                    }
                ]
            }
        ],
        "actions": [

        ]
    }
    return payload


@app.post("/api/exist-number")
async def exist_number(req: Request):
    body = await req.json()
    number = body.get("mobile")

    if not number:
        return {"success": False, "message": "Mobile number is required"}

    number = str(number)

    # Remove country code 91
    if number.startswith("91") and len(number) == 12:
        number = number[2:]

    existing_user = users.find_one({"mobile": number})

    if existing_user:
        return {
            "exists": True,
            "data": {
                "wa": existing_user.get("wa"),
                "step": existing_user.get("step"),
                "mobile": existing_user.get("mobile"),
                "name": existing_user.get("name")
            }
        }

    return {"exists": False}


@app.post("/payment-callback")
async def payment_callback(data: dict):

    mobile = str(data.get("mobile", "")).strip()
    message = str(data.get("message", "")).strip()

    # Validation
    if not mobile:
        return {
            "status": False,
            "message": "mobile missing"
        }

    if not message:
        return {
            "status": False,
            "message": "msg missing"
        }

    # Dynamic collection name
    collection_name = f"pay-{mobile}"

    collection = db[collection_name]

    # Update if exists, else insert
    collection.update_one(
        {"mobile": mobile},
        {
            "$set": {
                "mobile": mobile,
                "message": message,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return {
        "status": True,
        "message": "Data saved successfully",
        "collection": collection_name
    }


@app.get("/get-payment-message/{mobile}")
async def get_payment_message(mobile: str):

    mobile = str(mobile).strip()

    if not mobile:
        return {
            "status": False,
            "message": "mobile missing"
        }

    # Dynamic collection name
    collection_name = f"pay-{mobile}"

    collection = db[collection_name]

    # Find document
    data = collection.find_one(
        {"mobile": mobile},
        {"_id": 0}
    )

    if not data:
        return {
            "status": False,
            "message": "No payment message found"
        }

    # Get message
    payment_message = data.get("message", "")

    # Delete collection after fetch
    db.drop_collection(collection_name)

    return {
        "status": True,
        "mobile": mobile,
        "message": payment_message
    }




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9010)


