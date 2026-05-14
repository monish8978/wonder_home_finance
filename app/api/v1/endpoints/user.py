from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.mongo import db_manager

router = APIRouter()

class UserCheckRequest(BaseModel):
    mobile: str

@router.post("/exist-number")
async def exist_number(req: UserCheckRequest):
    db = db_manager.get_db()
    users = db["chat_state"]
    
    number = str(req.mobile).strip()
    if number.startswith("91") and len(number) == 12:
        number = number[2:]

    existing_user = await users.find_one({"mobile": number})
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
