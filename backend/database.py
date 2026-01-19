import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from config import get_settings

settings = get_settings()

client: AsyncIOMotorClient = None
db = None


async def connect_to_mongo():
    global client, db
    print(f"MongoDB URI: {settings.mongodb_uri[:50]}...")  # Print first 50 chars
    client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        tlsCAFile=certifi.where(),
    )
    db = client[settings.mongodb_database]
    # Test connection
    try:
        await client.admin.command('ping')
        print(f"Connected to MongoDB: {settings.mongodb_database}")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")


async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")


def get_database():
    return db
