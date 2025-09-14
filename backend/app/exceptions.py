"""
Application-wide exception handlers
"""
import json
import logging
import traceback
import uuid
from datetime import datetime

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler that catches all unhandled exceptions
    and returns a structured JSON response with trace ID.
    """
    # Generate trace ID (use existing one if available)
    trace_id = getattr(request.state, 'trace_id', str(uuid.uuid4()))
    
    # Log the exception with full traceback
    logger.error(
        f"Unhandled exception - trace_id: {trace_id}, "
        f"method: {request.method}, url: {request.url}, "
        f"exception: {type(exc).__name__}: {str(exc)}, "
        f"traceback: {traceback.format_exc()}"
    )
    
    # Return structured error response
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "status_code": 500,
                "detail": "Internal server error",
                "timestamp": datetime.utcnow().isoformat(),
                "trace_id": trace_id,
                "path": str(request.url.path)
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for HTTP exceptions (4xx errors)
    """
    # Generate trace ID (use existing one if available)
    trace_id = getattr(request.state, 'trace_id', str(uuid.uuid4()))
    
    # Log HTTP exceptions
    logger.warning(
        f"HTTP exception - trace_id: {trace_id}, "
        f"method: {request.method}, url: {request.url}, "
        f"status_code: {exc.status_code}, detail: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "detail": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "trace_id": trace_id,
                "path": str(request.url.path)
            }
        }
    )