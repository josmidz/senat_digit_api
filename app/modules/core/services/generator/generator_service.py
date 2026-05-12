

import secrets
import string
from typing import Optional
import base64
from bson import ObjectId
import random
from datetime import datetime, timedelta, timezone
import qrcode
import io
import pyotp
import time
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.enums.type_enum import EOTPSettings
from cryptography.fernet import Fernet
import uuid

class GeneratorService:
    """
    Service for generating code snippets based on input parameters.
    """
    
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language

    @staticmethod
    def generate_composed_id():
        # Generate a UUID
        unique_id = uuid.uuid4()
        
        # Get current timestamp in ISO format
        # timestamp = datetime.now(timezone.utc).isoformat()
        
        # Combine them (you can adjust the format as needed)
        composed_id = f"{unique_id}"
        # composed_id = f"{unique_id}-{timestamp}"
        
        return composed_id
    
    @staticmethod
    def generate_random_golden_numbers(size=3):
        numbers = []
        for _ in range(size):
            instructionId = GeneratorService.generate_encryption_key()
            numbers.append({
                "number": str(random.randint(10, 99)),  # Random number between 10 and 99
                "instruction_id": instructionId  # Random unique ID
                # "instructionId": str(uuid.uuid4()).replace("-", "")  # Random unique ID
            })
        return numbers
        
    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generates a secure encryption key for use with Fernet.

        Returns:
            str: A base64 encoded encryption key.
        """
        key = Fernet.generate_key()
        return key.decode()

    @staticmethod
    def generate_jwt_secret_key() -> str:
        """
        Generates a secure secret key for use with JWT.

        Returns:
            str: A 64-character hexadecimal secret key.
        """
        key = secrets.token_hex(32)  # Generate a 32-byte (256-bit) secure random key
        return key
    
    @staticmethod
    def generate_base32_secret(object_id_str: str) -> str:
        # Create an ObjectId instance from the string.
        obj_id = ObjectId(object_id_str)
        # Get the binary representation (12 bytes) of the ObjectId.
        binary_data = obj_id.binary
        # Encode the binary data using Base32.
        # This returns a bytes object, so decode it to a string.
        base32_secret = base64.b32encode(binary_data).decode('utf-8')
        return base32_secret

    @staticmethod
    def generate_totp_secret() -> str:
        # Generate 10 random bytes (80 bits)
        random_bytes = secrets.token_bytes(10)
        # Encode the random bytes in Base32
        secret = base64.b32encode(random_bytes).decode('utf-8')
        return secret

    @staticmethod
    def _ensure_base32_secret(secret: str) -> str:
        """
        Ensure the secret is valid base32 for pyotp.
        If it looks like base64/base64url (e.g. a Fernet key), decode
        the raw bytes and re-encode as base32.
        """
        import re
        # Valid base32 uses only A-Z, 2-7, = (case-insensitive)
        if re.fullmatch(r'[A-Za-z2-7=]+', secret):
            return secret.upper()
        # Likely base64 or base64url — convert to base32
        try:
            # Handle both standard and URL-safe base64
            raw = base64.urlsafe_b64decode(secret)
            return base64.b32encode(raw).decode('utf-8')
        except Exception:
            # Last resort: return as-is and let pyotp raise
            return secret

    @staticmethod
    def verify_totp_code(secret: str, user_code: str) -> bool:
        safe_secret = GeneratorService._ensure_base32_secret(secret)
        totp = pyotp.TOTP(safe_secret, interval=30)
        expected = totp.now()
        print("Expected TOTP:", expected)  # Debug output
        print("User provided:", user_code)
        # Optionally, show codes for the previous and next time windows.
        previous = totp.at(int(time.time()) - 30)
        next_code = totp.at(int(time.time()) + 30)
        print("Previous window TOTP:", previous)
        print("Next window TOTP:", next_code)
        return totp.verify(user_code, valid_window=1)

    @staticmethod
    def otpauth_to_qrcode(otpauth_uri: str) -> str:
        """
        Convert an OTPAuth URI to a QR code image (Base64-encoded PNG).
        
        Args:
            otpauth_uri (str): The OTPAuth URI string.
            
        Returns:
            str: A data URL containing the Base64-encoded QR code image.
        """
        # Create a QRCode instance with desired parameters.
        qr = qrcode.QRCode(
            version=1,  # use version=1 or use fit=True for automatic sizing
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # Add the OTPAuth URI data.
        qr.add_data(otpauth_uri)
        qr.make(fit=True)
        
        # Create an image from the QR Code instance.
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save the image to a bytes buffer.
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        # Encode the image bytes as Base64.
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        
        # Return a data URL (useful for embedding in HTML <img src="...">)
        return f"data:image/png;base64,{img_base64}"

    @staticmethod
    def generate_otp(length: int = EOTPSettings.OTP_LENGTH) -> str:
        """
        Generate a random OTP (One-Time Password) with the specified length.
        
        Args:
            length (int): The length of the OTP (default: 6).
        
        Returns:
            str: The generated OTP.
        """
        otp = ''.join(random.choices(EOTPSettings.OTP_CHARACTERS, k=length))
        return otp

    @staticmethod
    def get_otp_expiration(validity_minutes: int = EOTPSettings.OTP_VALIDITY_MINUTES) -> datetime:
        """
        Get the expiration time for the OTP.
        
        Args:
            validity_minutes (int): Number of minutes the OTP is valid (default: 5 minutes).
        
        Returns:
            datetime: Expiration time for the OTP.
        """
        return datetime.now() + timedelta(minutes=validity_minutes)
    
    @staticmethod
    def strong_password_generator(length: int = 12) -> str:
        if length < 8:
            raise ValueError("Password length must be at least 8 characters.")
        
        # Define character sets for each category.
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*(),.?\":{}|<>"

        # Ensure at least one character from each required set.
        password_chars = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]

        # Create a pool with all allowed characters.
        all_chars = uppercase + lowercase + digits + special

        # Fill the remaining length of the password.
        for _ in range(length - 4):
            password_chars.append(secrets.choice(all_chars))

        # Shuffle the list to randomize character positions.
        secrets.SystemRandom().shuffle(password_chars)

        # Join the list to form the final password string.
        return ''.join(password_chars)
