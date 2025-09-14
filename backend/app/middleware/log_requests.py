import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests and their responses"""
    
    # Fields to redact for privacy
    SENSITIVE_FIELDS = {"aadhar", "pan", "ssn", "password", "secret", "token"}
    
    def __init__(self, app, log_level: str = "INFO"):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate trace ID for this request
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        
        # Record start time
        start_time = time.time()
        
        # Read request body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            
        # Log request
        await self._log_request(request, body, trace_id)
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration = time.time() - start_time
            logger.error(
                f"Request failed - trace_id: {trace_id}, "
                f"method: {request.method}, url: {request.url}, "
                f"duration: {duration:.3f}s, error: {str(e)}"
            )
            raise
        
        # Log response
        duration = time.time() - start_time
        await self._log_response(request, response, duration, trace_id)
        
        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id
        
        return response
    
    async def _log_request(self, request: Request, body: bytes, trace_id: str):
        """Log incoming request details"""
        if not logger.isEnabledFor(self.log_level):
            return
            
        # Parse body if JSON
        body_data = None
        if body:
            try:
                body_str = body.decode('utf-8')
                body_data = json.loads(body_str)
                # Redact sensitive fields
                body_data = self._redact_sensitive_data(body_data)
            except (UnicodeDecodeError, json.JSONDecodeError):
                body_data = f"<binary or invalid json: {len(body)} bytes>"
        
        # Extract relevant headers
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() in {"content-type", "user-agent", "authorization"}
        }
        
        log_data = {
            "type": "request",
            "trace_id": trace_id,
            "method": request.method,
            "url": str(request.url),
            "headers": headers,
            "body": body_data,
            "client": request.client.host if request.client else None
        }
        
        logger.log(self.log_level, f"Request: {json.dumps(log_data)}")
    
    async def _log_response(self, request: Request, response: Response, duration: float, trace_id: str):
        """Log response details"""
        if not logger.isEnabledFor(self.log_level):
            return
            
        log_data = {
            "type": "response", 
            "trace_id": trace_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration": f"{duration:.3f}s"
        }
        
        logger.log(self.log_level, f"Response: {json.dumps(log_data)}")
    
    def _redact_sensitive_data(self, data):
        """Recursively redact sensitive fields from data"""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if key.lower() in self.SENSITIVE_FIELDS:
                    redacted[key] = "<REDACTED>"
                else:
                    redacted[key] = self._redact_sensitive_data(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        else:
            return data