
from app.modules.core.utils.common.async_runner import AsyncExecutor
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any
from fastapi import FastAPI

from app.modules.core.configs.config import settings

class MongoDB:
    def __init__(self):
        """Initialize MongoDB client and database."""
        mongo_uri = settings.MONGO_URI
        database_name = settings.MONGO_DB_NAME
        if not mongo_uri or not database_name:
            raise ValueError("MongoDB URI and database name must be provided via environment variables.")

        try:
            # Increased connection pool settings to prevent blocking under concurrent load
            self.client = AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=200,  # Increased from default 100
                minPoolSize=10,   # Keep minimum connections ready
                maxIdleTimeMS=30000,  # 30 seconds idle timeout
                waitQueueTimeoutMS=10000,  # 10 second wait queue timeout
            )
            self.db = self.client[database_name]
        except Exception as e:
            raise ConnectionError(f"MongoDB connection failed: {e}")

    async def test_connection(self):
        """Test MongoDB connection using ping."""
        try:
            # Performing ping command to test connection
            await self.db.command("ping")
            print(f"Connected to MongoDB database: {settings.MONGO_DB_NAME}")
        except Exception as e:
            raise ConnectionError(f"MongoDB connection failed: {e}")

    def get_read_only_collection(self, name: str):
        """Get the corresponding view for a collection."""
        if not name:
            raise ValueError("Collection name must be provided.")
        view_name = f"view_{name}"  # Use the view instead of the collection
        return self.db[view_name]
    
    def get_collection(self, name: str) -> Any:
        """Retrieve a MongoDB collection."""
        if not name:
            raise ValueError("Collection name must be provided.")
        return self.db[name]

    async def close(self):
        """Close the MongoDB connection."""
        self.client.close()


# Create FastAPI app and MongoDB instance
app = FastAPI()
mongodb = MongoDB()

@app.on_event("startup")
async def startup_db():
    """Perform a MongoDB connection test on startup."""
    await mongodb.test_connection()
    
@app.on_event("startup")
async def startup_event():
    # Tune pools depending on workload
    AsyncExecutor.init_pools(max_threads=50, max_processes=4)


@app.on_event("shutdown")
async def shutdown_db():
    """Close MongoDB connection on shutdown."""
    await mongodb.close()

# Utility function to get collection
def get_collection(name: str) -> Any:
    """Convenience function to get a MongoDB collection."""
    return mongodb.get_collection(name)

def get_read_only_collection(name: str) -> Any:
    """Convenience function to get a MongoDB collection."""
    return mongodb.get_read_only_collection(name)

