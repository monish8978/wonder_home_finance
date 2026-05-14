from fastapi import APIRouter
from datetime import datetime
from app.db.mongo import db_manager

router = APIRouter()

@router.post("/callback")
async def payment_callback(data: dict):
    mobile = str(data.get("mobile", "")).strip()
    message = str(data.get("message", "")).strip()

    if not mobile or not message:
        return {"status": False, "message": "mobile or msg missing"}

    db = db_manager.get_db()
    collection_name = f"pay-{mobile}"
    collection = db[collection_name]

    await collection.update_one(
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
    return {"status": True, "message": "Data saved successfully"}

@router.get("/message/{mobile}")
async def get_payment_message(mobile: str):
    mobile = mobile.strip()
    db = db_manager.get_db()
    collection_name = f"pay-{mobile}"
    collection = db[collection_name]

    data = await collection.find_one({"mobile": mobile}, {"_id": 0})
    if not data:
        return {"status": False, "message": "No payment message found"}

    payment_message = data.get("message", "")
    await db.drop_collection(collection_name)

    return {
        "status": True,
        "mobile": mobile,
        "message": payment_message
    }
