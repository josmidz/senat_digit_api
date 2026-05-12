# app/core/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from app.modules.core.configs.config import settings
from app.modules.core.utils.common.helpers import hash_password,verify_password


# Initialize Basic Authentication
security = HTTPBasic()


# Optional: Hashing configuration
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = hash_password(settings.BASIC_PASSWORD)

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = credentials.username == settings.BASIC_USERNAME
    correct_password = verify_password(credentials.password, hashed_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
