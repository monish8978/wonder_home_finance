import os
import time
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.utils.logger import logger
from app.services.financial_service import (
    verify_pan, 
    generate_transunion_token, 
    submit_cibil_application
)
from app.tasks.whatsapp_tasks import send_whatsapp_template_task, send_whatsapp_document_task

@celery_app.task(name="tasks.verify_pan_and_check_cibil")
def verify_pan_and_check_cibil_task(wa_id: str, pan: str, full_name: str):
    logger.info(f"Starting CIBIL process for {full_name} ({wa_id}), PAN: {pan}")
    
    try:
        # 1. Verify PAN
        pan_res = verify_pan(pan)
        if pan_res.get("status-code") != "101":
            logger.warning(f"PAN verification failed for {wa_id}: {pan_res}")
            send_whatsapp_template_task.delay(wa_id, "pan_verify_wonder_home")
            return {"status": "pan_failed"}

        # 2. Get TransUnion Token
        token = generate_transunion_token()
        if not token:
            logger.error(f"Failed to get TransUnion token for {wa_id}")
            return {"status": "token_error"}

        # 3. Submit CIBIL Application
        document_id = submit_cibil_application(token, pan, full_name)
        if not document_id:
            logger.error(f"Failed to get Document ID for {wa_id}")
            return {"status": "submission_error"}

        # 4. Fetch and Send PDF (Placeholder for actual fetch logic)
        # In a real scenario, you'd download the HTML and convert to PDF as in main.py
        logger.info(f"CIBIL Document ID: {document_id}")
        
        # Simulate final message
        message = f"CIBIL check for {full_name} completed. Document ID: {document_id}"
        logger.info(message)
        
        return {"status": "success", "document_id": document_id}

    except Exception as e:
        logger.error(f"CIBIL process failed for {wa_id}: {e}")
        return {"status": "error", "error": str(e)}
