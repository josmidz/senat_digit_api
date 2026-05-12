
import hashlib
import base64
from fastapi import Request

from app.modules.core.services.debug.debug_service import DebugService

class HashService:
    
    @staticmethod
    def generate_hash(input_string: str, length: int = 64, algorithm: str = "sha256") -> str:
        """
        Generate a secure hash for a given input string.

        Args:
            input_string (str): The string to hash (with special characters intact).
            length (int): The length of the final hash string (default is 64 for SHA-256).
            algorithm (str): The hash algorithm to use (default is "sha256").

        Returns:
            str: The shortened hash string.
        """
        # Normalize the input string (e.g., lowercase, strip spaces)
        normalized_input = input_string.lower().strip()

        # Create a hash object using the specified algorithm
        hash_object = hashlib.new(algorithm)
        hash_object.update(normalized_input.encode('utf-8'))

        # Convert to hex digest (full hash) and truncate to the desired length
        full_hash = hash_object.hexdigest()
        return full_hash[:length]


    @staticmethod
    def generate_base64_hash(input_string: str, length: int = 32) -> str:
        normalized_input = input_string.lower().strip()
        sha256_hash = hashlib.sha256(normalized_input.encode('utf-8')).digest()
        base64_hash = base64.urlsafe_b64encode(sha256_hash).decode('utf-8')[:length]
        return base64_hash


    @staticmethod
    async def get_hashed_device_id(request: Request) -> str:
        # Extract the user-agent and device_id from headers
        user_agent = request.headers.get('user-agent', '')
        DebugService.app_debug_print(f"user_agent : {user_agent}")
        device_id = request.headers.get('device_id', '')
        print(f"device_id : {device_id}")
        # Determine the source (mobile device or browser user-agent)
        if user_agent.lower() == "mobile" and device_id:
            device_identifier = device_id  # Mobile device ID
        else:
            device_identifier = user_agent  # Browser user-agent

        # Hash the device identifier
        hashed_device_id = HashService.generate_base64_hash(device_identifier)
        DebugService.app_debug_print(f" hashed_device_id : {hashed_device_id}")
        return hashed_device_id