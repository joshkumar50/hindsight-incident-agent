from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Payload Size Limit (e.g. 1MB)
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > 1048576:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
            
        # 2. Add Security Headers (Defense in depth beyond NGINX)
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
