from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.utils.logger import logger
from app.db.mongo import db_manager
import uvicorn
from app.api.v1.endpoints import chat, user, payment, download
import time

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "An internal server error occurred.", "detail": str(exc)}
    )

# Middleware for response timing and logging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.4f}s)")
    return response

# Include Routers
app.include_router(chat.router, prefix=settings.API_V1_STR + "/chat", tags=["chat"])
app.include_router(user.router, prefix=settings.API_V1_STR + "/user", tags=["user"])
app.include_router(payment.router, prefix=settings.API_V1_STR + "/payment", tags=["payment"])
app.include_router(download.router, prefix=settings.API_V1_STR + "/download", tags=["download"])

@app.on_event("startup")
async def startup_db_client():
    logger.info("Starting up MongoDB client...")
    db_manager.get_client()

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down MongoDB client...")
    db_manager.get_client().close()

@app.get("/")
async def root():
    return {"message": "Wonder Home Loan Bot API is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
