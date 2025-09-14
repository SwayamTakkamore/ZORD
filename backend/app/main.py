from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv

from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.v1 import api_router
from app.middleware.log_requests import RequestLoggingMiddleware
from app.exceptions import global_exception_handler, http_exception_handler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting up Crypto Compliance Copilot Backend")
    await connect_to_mongo()
    logger.info("MongoDB connection established and indexes created")
    yield
    # Shutdown
    logger.info("Shutting down Crypto Compliance Copilot Backend")
    await close_mongo_connection()


# Create FastAPI app
app = FastAPI(
    title="Crypto Compliance Copilot API",
    description="Automated compliance checking with MongoDB and blockchain anchoring",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware, log_level="INFO")

# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {"status": "healthy", "service": "compliance-copilot-backend"}


# Debug endpoint to check MongoDB users
@app.get("/debug/mongodb-users")
async def debug_mongodb_users():
    """Debug endpoint to see what users are stored in MongoDB"""
    from app.db.mongo import get_database
    
    try:
        db = await get_database()
        users_collection = db.users
        
        # Get all users from MongoDB
        users_cursor = users_collection.find({}, {"password_hash": 0})  # Exclude password hashes
        users_list = []
        
        async for user in users_cursor:
            user["_id"] = str(user["_id"])  # Convert ObjectId to string
            users_list.append(user)
        
        return {
            "mongodb_users_count": len(users_list),
            "users": users_list
        }
        
    except Exception as e:
        return {"error": f"Failed to query MongoDB: {str(e)}"}


# Include API routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
