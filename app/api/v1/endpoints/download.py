from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
import os
from app.core.config import settings

router = APIRouter()

@router.get("/cibil")
async def download_cibil_report(file: str = Query(...)):
    safe_file = os.path.basename(file)
    file_path = os.path.join(settings.PDF_STORAGE_PATH, safe_file)

    if not os.path.exists(file_path):
        return {"status": "error", "message": "Documents not found"}

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_file
    )
