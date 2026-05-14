import requests
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.utils.logger import logger

@celery_app.task(name="tasks.send_whatsapp_template")
def send_whatsapp_template_task(to_number: str, template_name: str):
    url = settings.WHATSAPP_API_URL
    headers = {
        "apikey": settings.WHATSAPP_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"}
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send WhatsApp template {template_name} to {to_number}: {e}")
        return {"error": str(e)}

@celery_app.task(name="tasks.send_whatsapp_document")
def send_whatsapp_document_task(to_number: str, media_url: str, filename: str):
    # Using the second WhatsApp API URL from original code
    url = "https://omniqa.c-zentrix.com/whatsappApi_v2/OUT/outgoing.php"
    payload = {
        "token": settings.WHATSAPP_API_KEY,
        "auth_token": settings.WHATSAPP_API_KEY,
        "accountId": settings.WHATSAPP_API_KEY,
        "mobile_no": to_number,
        "type": "document",
        "tag": "BotTvt",
        "licenseId": "d62ceab4ea4e5eb537453fb9d5cddd65",
        "api_type": "pinnacle",
        "media_url": media_url,
        "messageBody": filename,
        "mime_type": "application/pdf"
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send WhatsApp document {filename} to {to_number}: {e}")
        return {"error": str(e)}
