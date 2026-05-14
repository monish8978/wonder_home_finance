from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from app.utils.logger import logger
from datetime import datetime
from app.services.chat_manager import ChatManager

router = APIRouter()

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    logger.info(f"Received webhook: {data}")
    
    try:
        # Compatibility with original format: body.get("wa_numer"), body.get("message"), extraParms
        # The user provided a specific format in the view_file (lines 838-846)
        wa_numer = data.get("wa_numer")
        msg = data.get("message", "").strip()
        extra_params_str = data.get("extraParms")
        
        if extra_params_str:
            import json
            extra_params = json.loads(extra_params_str)
            identifier = extra_params.get("identifier")
        else:
            identifier = wa_numer

        if not identifier:
            return {"status": "error", "message": "No identifier found"}

        response_payload = await ChatManager.process_message(identifier, msg)
        return {"success": True, "data": response_payload}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Failed to process message", "detail": str(e)}
        )

@router.get("/status")
async def get_status():
    return {"status": "active", "timestamp": datetime.utcnow()}
