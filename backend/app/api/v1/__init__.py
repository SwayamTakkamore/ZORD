"""
API v1 Router

Includes all v1 API endpoints
"""

from fastapi import APIRouter
from .transactions import router as transactions_router
from .zk_proofs import router as zk_proofs_router
from .anchor import router as anchor_router
from app.routes.user import router as user_router
from app.routes.simple_auth import router as simple_auth_router

# Create main v1 router
api_router = APIRouter(prefix="/v1")

# Include routers
api_router.include_router(
    transactions_router,
    tags=["transactions"]
)

api_router.include_router(
    zk_proofs_router,
    prefix="/zk",
    tags=["zk-proofs"]
)

api_router.include_router(
    anchor_router,
    prefix="/anchor",
    tags=["anchor"]
)

api_router.include_router(
    user_router,
    prefix="/users",
    tags=["authentication"]
)

# Add simple auth for debugging
api_router.include_router(
    simple_auth_router,
    prefix="/debug",
    tags=["debug-auth"]
)
