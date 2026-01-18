import os
from typing import Union
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables from .env.local in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
load_dotenv(dotenv_path=dotenv_path)

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = "mchacks2026" # You might want to make this an env var too
PROJECTS_COLLECTION = "projects"

if not MONGO_URI:
    raise Exception("MONGODB_URI not found in environment variables")

class DB:
    client: Union[AsyncIOMotorClient, None] = None

db = DB()

async def get_database():
    if db.client is None:
        raise Exception("Database client not initialized")
    return db.client[DB_NAME]

async def connect_to_mongo():
    print("Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(MONGO_URI)
    print("MongoDB connected.")

async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("MongoDB connection closed.")

async def get_project(project_id: str):
    database = await get_database()
    projects_collection = database[PROJECTS_COLLECTION]
    # In python, ObjectId is imported from bson, not mongodb
    from bson.objectid import ObjectId
    project = await projects_collection.find_one({"_id": ObjectId(project_id)})
    return project

async def update_project_status(project_id: str, status: str, error: Union[str, None] = None):
    database = await get_database()
    projects_collection = database[PROJECTS_COLLECTION]
    from bson.objectid import ObjectId
    update = {"$set": {"status": status}}
    if error:
        update["$set"]["error"] = error
    await projects_collection.update_one({"_id": ObjectId(project_id)}, update)

async def update_project_completed(project_id: str, final_video_url: str, final_s3_key: str):
    database = await get_database()
    projects_collection = database[PROJECTS_COLLECTION]
    from bson.objectid import ObjectId
    await projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "status": "completed",
                "finalVideoUrl": final_video_url,
                "finalVideoS3Key": final_s3_key,
            }
        },
    )
