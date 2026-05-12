
from typing import Optional
from passlib.context import CryptContext

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

# Configure Passlib to use Argon2 for hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class PasswordService:
    """
    Service for managing passwords.
    """
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    # Function to verify a password
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
