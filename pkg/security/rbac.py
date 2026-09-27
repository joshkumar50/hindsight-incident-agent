from functools import wraps
from fastapi import HTTPException, status

ROLES = {
    "Administrator": 4,
    "SRE_Engineer": 3,
    "Developer": 2,
    "Read_Only": 1
}

def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Assumes 'user_payload' is injected by a dependency
            user_payload = kwargs.get('user_payload')
            if not user_payload:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            
            user_role = user_payload.get('role', 'Read_Only')
            
            req_level = ROLES.get(required_role, 0)
            user_level = ROLES.get(user_role, 0)
            
            if user_level < req_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail=f"Insufficient permissions. Required: {required_role}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
