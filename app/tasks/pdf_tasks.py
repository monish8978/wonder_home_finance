import os
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.utils.logger import logger
from app.services.financial_service import get_loan_details
from app.utils.pdf_generator import create_loan_details_pdf
from app.tasks.whatsapp_tasks import send_whatsapp_document_task

@celery_app.task(name="tasks.generate_loan_summary_pdf")
def generate_loan_summary_pdf_task(wa_id: str):
    logger.info(f"Generating loan summary PDF for {wa_id}")
    
    try:
        # 1. Fetch loan details
        loan_data = get_loan_details(wa_id)
        if not loan_data:
            logger.error(f"No loan data found for {wa_id}")
            return {"status": "no_data"}
        
        loan_rows = loan_data.get("customerLoanDetails", [])
        if not loan_rows:
            logger.error(f"No customer loan details found for {wa_id}")
            return {"status": "no_details"}

        # 2. Generate PDF
        filename = f"loan_summary_{wa_id}.pdf"
        file_path = os.path.join(settings.PDF_STORAGE_PATH, filename)
        
        create_loan_details_pdf(loan_rows, file_path)
        
        # 3. Send to WhatsApp
        pdf_url = f"{settings.BASE_URL}/download/cibil?file={filename}" # Using existing download endpoint
        send_whatsapp_document_task.delay(wa_id, pdf_url, filename)
        
        return {"status": "success", "file": file_path}
        
    except Exception as e:
        logger.error(f"Failed to generate loan summary PDF: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="tasks.generate_interest_certificate")
def generate_interest_certificate_task(wa_id: str, doc_type: str):
    logger.info(f"Generating {doc_type} for {wa_id}")
    # Placeholder for actual certificate generation logic from main.py
    # In legacy, it calls download_interest_certificate etc.
    return {"status": "success"}
