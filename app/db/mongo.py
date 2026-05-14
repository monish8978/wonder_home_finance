from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoClientManager:
    client: AsyncIOMotorClient = None

    @classmethod
    def get_client(cls):
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGO_URL)
        return cls.client

    @classmethod
    def get_db(cls):
        return cls.get_client()[settings.DATABASE_NAME]

db_manager = MongoClientManager()
