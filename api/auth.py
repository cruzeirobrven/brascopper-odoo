from fastapi import Request, HTTPException, status

from api.config import settings


async def verificar_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key invalida ou ausente",
        )
