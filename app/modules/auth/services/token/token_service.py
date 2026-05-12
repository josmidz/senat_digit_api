

from fastapi import Depends, HTTPException, Header, Request, WebSocket,status
from jose import JWTError,ExpiredSignatureError
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.enums.type_enum import EJWTTokenType, OutputDataType
from app.modules.core.configs.config import settings
from jose import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.response.response_service import ResponseService



class TokenService(ResponseService):
    """
    Service for managing API tokens and their expiration dates.
    """
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language=accept_language)
        super().__init__(accept_language)

    async def get_user_account_socket_hash_from_params(self,websocket: WebSocket):
        query_params = websocket.query_params
        user_account_socket_hash = query_params.get("user_account_socket_hash", None)
        return user_account_socket_hash

    async def _safe_websocket_close(self, websocket: WebSocket, code: int = 1000, reason: str = ""):
        """
        Safely close a WebSocket connection, handling cases where it's already closed.

        Args:
            websocket: The WebSocket connection to close
            code: The close code (default: 1000 for normal closure)
            reason: The reason for closing
        """
        try:
            # Check if the connection is still open before attempting to close
            if websocket.client_state.value == 0:  # 0 = CONNECTING, 1 = CONNECTED, 2 = DISCONNECTING, 3 = DISCONNECTED
                await websocket.close(code=code, reason=reason)
        except RuntimeError as e:
            # Connection is already closed, which is fine
            if "Cannot call" not in str(e):
                # Re-raise if it's a different RuntimeError
                DebugService.app_debug_print(f"Error closing WebSocket: {str(e)}", True)
        except Exception as e:
            # Log other exceptions but don't raise them
            DebugService.app_debug_print(f"Unexpected error closing WebSocket: {str(e)}", True)
        
    async def get_decoded_header_token(self,request: Request,expected_type:EJWTTokenType,accept_language:str) -> str:
        authorization_header = request.headers.get("authorization")
        if not authorization_header or not authorization_header.startswith("Bearer "):
            message = ResponseService.get_response_message(MessageCategory.COMMON, "MISSING_DATA", accept_language, meta="Bearer token")
            raise HTTPException(status_code=401, detail=message)
        
        token = authorization_header.split(" ")[1]
        # Handle token decoding
        try:
            decoded_token = self.decode_and_verify_token(token, expected_type=expected_type)
        except JWTError as e:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        
        return decoded_token
    
    async def decode_and_get_user_from_token(
        self,
        request: Request,
        expected_type: EJWTTokenType = EJWTTokenType.LOGIN  # Default token type
    ):
        """
        Decode and return user info from the given JWT token, ensuring the type matches the expected purpose.
        The token is expected to be in the `Authorization` header as a Bearer token.
        """
        accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()  # Extract language dynamically
        try:
            authorization = request.headers.get("authorization")
            DebugService.app_debug_print("\n >> Authorization header missing or invalid, : {authorization} \n",False)
            if not authorization or not authorization.startswith("Bearer "):
                message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "HEADER_TOKEN_MISSING", accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message,
                )
            endpoint_url = request.url.path
            DebugService.app_debug_print(f"endpoint_url : {endpoint_url}",False)
            # Extract the token from the Authorization header (it should be prefixed with "Bearer ")
            token = authorization.split(" ")[1]  # Get the token part after 'Bearer'
            # Decode the token
            decoded_token = self.decode_and_verify_token(
                token=token,
                expected_type=expected_type,
            ) 

            DebugService.app_debug_print(f"decoded_token {decoded_token}",False)
            # Validate the token type
            if decoded_token.get("type") != expected_type.value:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_TOKEN_TYPE", accept_language)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message,
                )
            
            # Fetch user details from the database
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": decoded_token["sub"]},  # Ensure `sub` is present in the token
            )
            
            
            
            if not user_details:
                message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "USER_NOT_FOUND", accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message,
                )
            DebugService.app_debug_print(f"user_details retrieved >>>>>> : {user_details}",False)
            return user_details

        except IndexError as e:
            DebugService.app_debug_print(f"ERROR - {e}")
            # Malformed Authorization header
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MALFORMED_AUTH_HEADER", accept_language)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        except ExpiredSignatureError as e:
            DebugService.app_debug_print(f"ERROR 2 - {e}")
            # Token has expired
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message,
            )
        except JWTError as e:
            DebugService.app_debug_print(f"ERROR 3 - {e}")
            # General JWT decoding error
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_INVALID", accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message,
            ) 
    
  
    async def decode_and_get_user_from_socket_token(self,websocket: WebSocket):
        """
        Decode and return user info from the given JWT token, ensuring the type matches the expected purpose.
        The token is expected to be in the query parameters.
        """
        query_params = websocket.query_params
        accept_language = query_params.get("accept_language", None)
        accept_language = accept_language if accept_language else websocket.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
        try:
            token = query_params.get("token", None)
            authorization = websocket.headers.get("authorization", None)

            # Try to get token from query params first, then from authorization header
            if not token and authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]  # Get the token part after 'Bearer'

            if not token:
                message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "HEADER_TOKEN_MISSING", accept_language)
                DebugService.app_debug_print(f"WebSocket token missing - query token: {token}, auth header: {authorization}", True)
                await self._safe_websocket_close(websocket, code=1008, reason="Token missing")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message,
                )
            DebugService.app_debug_print(f" WebSocket token: {token}",True)
            # Decode and verify the token
            decoded_token = self.decode_and_verify_token(
                token=token,
                expected_type=EJWTTokenType.LOGIN,
            )

            # Validate the token type
            if decoded_token.get("type") != EJWTTokenType.LOGIN.value:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_TOKEN_TYPE", accept_language)
                await self._safe_websocket_close(websocket, code=1008, reason=message)
                return None

            # Fetch user details from the database
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": decoded_token["sub"]},
            )

            if not user_details:
                message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "USER_NOT_FOUND", accept_language)
                await self._safe_websocket_close(websocket, code=1008, reason=message)
                return None

            # Accept the WebSocket connection after successful validation
            # await websocket.accept()
            return user_details

        except ExpiredSignatureError:
            DebugService.app_debug_print(f"WebSocket token EXPIRED for connection", True)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", accept_language)
            await self._safe_websocket_close(websocket, code=1008, reason=message)
        except JWTError as e:
            DebugService.app_debug_print(f"WebSocket token INVALID (JWTError): {str(e)}", True)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOKEN", accept_language)
            await self._safe_websocket_close(websocket, code=1008, reason=message)
        except Exception as e:
            DebugService.app_debug_print(f"WebSocket token validation EXCEPTION: {type(e).__name__}: {str(e)}", True)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
            await self._safe_websocket_close(websocket, code=1011, reason=f"{message}: {str(e)}")
           
            
    async def get_user_api_consumer_from_params(self,websocket: WebSocket):
        """
        Decode and return user info from the given JWT token, ensuring the type matches the expected purpose.
        The token is expected to be in the query parameters.
        """
        query_params = websocket.query_params
        api_consumer = query_params.get("socket_api_consumer", None)
        accept_language = query_params.get("accept_language", None)
        accept_language = accept_language if accept_language else websocket.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
        try:
            return api_consumer

        except ExpiredSignatureError:
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", accept_language)
            await self._safe_websocket_close(websocket, code=1008, reason=message)
        except JWTError:
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOKEN", accept_language)
            await self._safe_websocket_close(websocket, code=1008, reason=message)
        except Exception as e:
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
            await self._safe_websocket_close(websocket, code=1011, reason=f"{message}: {str(e)}")
    async def decode_and_get_user_from_angular_socket_token(self,websocket: WebSocket):
        """
        Decode and return user info from the given JWT token, ensuring the type matches the expected purpose.
        The token is expected to be in the query parameters.
        """
        # Extract token and language from query parameters
        query_params = websocket.query_params
        token = query_params.get("token")
        accept_language = query_params.get("accept_language", DEFAULT_LANGUAGE).split(",")[0].strip()

        if not token:
            await self._safe_websocket_close(websocket, code=1008, reason="Token missing")
            return None

        try:
            # Decode and verify the token
            decoded_token = self.decode_and_verify_token(
                token=token,
                expected_type=EJWTTokenType.LOGIN,
            )

            # Validate the token type
            if decoded_token.get("type") != EJWTTokenType.LOGIN.value:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_TOKEN_TYPE", accept_language)
                await self._safe_websocket_close(websocket, code=1008, reason=message)
                return None

            # Fetch user details from the database
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": decoded_token["sub"]},
            )

            if not user_details:
                message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "USER_NOT_FOUND", accept_language)
                await self._safe_websocket_close(websocket, code=1008, reason=message)
                return None

            # Accept the WebSocket connection after successful validation
            # await websocket.accept()
            return user_details

        except ExpiredSignatureError:
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", accept_language)
            await self._safe_websocket_close(websocket, code=1008, reason=message)
        except JWTError:
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOKEN", accept_language)
            await self._safe_websocket_close(websocket, code=1008, reason=message)
        except Exception as e:
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
            await self._safe_websocket_close(websocket, code=1011, reason=f"{message}: {str(e)}")
            
    def decode_and_verify_token(self,token: str, expected_type: EJWTTokenType,by_pass_exception:bool = False):
        """
        Decode and verify the JWT token, ensuring the type matches the expected purpose.
        """
        try:
            decoded_token = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                audience=f"{expected_type.value}_token"
            )
            
            if decoded_token.get("type") != expected_type.value:
                if by_pass_exception :
                    return None
                message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message
                )
            return decoded_token

        except ExpiredSignatureError as e:  # Token has expired
            print(f"ERROR 2 - {e}")
            if by_pass_exception :
                return None
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )

        except JWTError as e:  # Invalid token
            print(f"ERROR 3 - {e}")
            if by_pass_exception :
                return None
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_INVALID", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
 
    # Generate a JWT token
    
    # def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    @staticmethod
    def create_access_token(data: dict, token_type: EJWTTokenType, expires_delta: Union[timedelta, None] = None) -> str:
        """
        Generate a JWT token with an explicit token type (purpose).
        
        Args:
            data (dict): Payload data for the token.
            token_type (EJWTTokenType): Type of the token (e.g., LOGIN, PASSWORD_RESET, MFA_VERIFICATION).
            expires_delta (timedelta): Expiration time for the token.
        
        Returns:
            str: Encoded JWT token.
        """
        to_encode = data.copy()
        
        # Expiration time
        expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
        
        # print(f"payload : {to_encode}")
        # print(f"settings.JWT_SECRET_KEY : {settings.JWT_SECRET_KEY}")
        # print(f"settings.JWT_ALGORITHM : {settings.JWT_ALGORITHM}")
        # Update token with expiration and type
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": token_type.value,  # Add token type as a string (from Enum)
            "aud": f"{token_type.value}_token",  # Set audience claim based on token type
            "device_id_str": data.get("device_id_str", None)
        })
        
        token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token