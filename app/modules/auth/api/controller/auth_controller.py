

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json 
import random
import secrets
import string
import time

from typing import Any, Dict, Optional
import uuid

from pydantic import ValidationError
from app.modules.core.utils.common.async_runner import AsyncExecutor
from bson import ObjectId
from fastapi import Body, Form, HTTPException, File, UploadFile, Query, Request, status, BackgroundTasks
from app.modules.auth.enums.auth import ELoginStatus
from app.modules.auth.enums.common import MessageCategory

from app.modules.auth.enums.mfa import MFaFlag

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService, CustomJSONResponseException
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.schemas.auth_schema import DeviceActivationTokenRequest, DevicePairingRequest, LoggedInUserPasswordValidationRequest, LoginAgentRequest, LoginRequest, OtpRequest, PasswordInitRequest, PasswordResetRequest, PasswordResetTokenRequest, PhoneNumberLoginRequest, TOtpRequest, UserPhoneNumberRegistrationRequest, UserRegistrationAuthConfigRequest
from app.modules.core.services.generator.generator_service import GeneratorService
import httpx

from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.response.response_service import ResponseService

from app.modules.core.enums.type_enum import AccountStatusFlag, EGender, EJWTTokenType, ELoginResetPasswordFailStatus, ERegistrationOrigin, EUserDeviceStatus, EWalletType, OutputDataType
from app.modules.core.configs.config import settings
from app.modules.core.utils.common.helpers import mask_email_or_phone_util
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.schemas.user_schema import UserInfoValidation
from app.modules.core.enums.access_level import EUserInfoValidationFlag
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.enums.profiles_enum import  ESysProfilSuperUserRoleFlag, ESysProfileFlag

from app.modules.core.models.sys_user.sys_user_model import SysUserModel

from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.services.system_country.system_country_service import SystemCountryService
from app.modules.core.services.credentialchecker.credential_checker_service import CredentialCheckerService




class AuthController(
    AuthenticatedService,
    DebugService,
    PasswordService,
    ResponseService,
    ConverterService,
    ModelService,):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.device.device_service import DeviceService
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
        from app.modules.core.services.sms.sms_service import SmsService

        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        self.login_service = LoginService(accept_language)
        self.generator_service = GeneratorService(accept_language)
        self.device_service = DeviceService(accept_language=accept_language)
        self.email_sender_service = EMailSenderService()
        self.sms_service = SmsService()
        super().__init__(accept_language)

    def _generate_cache_key(self, user_id: str, method_name: str, **params) -> str:
        """
        Generate a unique cache key based on user ID, method name, and parameters
        """
        # Create a string representation of all parameters
        param_str = json.dumps(params, sort_keys=True, default=str)

        # Create a hash of the parameters to keep key length manageable
        param_hash = hashlib.md5(param_str.encode()).hexdigest()

        # Format: static_cache:{user_id}:{method_name}:{param_hash}
        return f"static_cache:{user_id}:{method_name}:{param_hash}"

    async def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache with timing
        """
        start_time = time.time()
        try:
            cached_data = await AppRedisService.get_str_redis_value(cache_key, use_env_prefix=True)
            fetch_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds

            if cached_data:
                self.app_debug_print(f"🎯 Cache HIT for key: {cache_key} | Fetch time: {fetch_time}ms", True)
                return json.loads(cached_data)
            else:
                self.app_debug_print(f"❌ Cache MISS for key: {cache_key} | Check time: {fetch_time}ms", True)
                return None
        except Exception as e:
            fetch_time = round((time.time() - start_time) * 1000, 2)
            self.app_debug_print(f"⚠️ Cache retrieval error: {str(e)} | Time: {fetch_time}ms", True)
            return None

    async def _set_cached_data(self, cache_key: str, data: Dict[str, Any], ttl: int = 300) -> None:
        """
        Store data in cache with TTL and timing (default 5 minutes)
        """
        start_time = time.time()
        try:
            serialized_data = json.dumps(data, default=str)
            await AppRedisService.set_redis_value(cache_key, serialized_data, expiry=ttl, use_env_prefix=True)
            store_time = round((time.time() - start_time) * 1000, 2)
            data_size = len(serialized_data)
            self.app_debug_print(f"💾 Cache SET for key: {cache_key} | TTL: {ttl}s | Store time: {store_time}ms | Size: {data_size} bytes", True)
        except Exception as e:
            store_time = round((time.time() - start_time) * 1000, 2)
            self.app_debug_print(f"⚠️ Cache storage error: {str(e)} | Time: {store_time}ms", True)



    async def send_welcome_email(self, email: str, first_name: str, last_name: str):
        """Send welcome email to newly registered user"""
        try:
           

            # Construct email body with proper HTML formatting
            # html_content = f"""
            # <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            #     <h2>{greeting}</h2>
            #     <p>{welcome_message}</p>
            #     <p>{instructions}</p>
            #     <div style="margin-top: 30px;">
            #         <p>{signature}</p>
            #     </div>
            # </div>
            # """

            # Send the email using the email service
            # EMailSenderService
            await self.email_sender_service.send_email(
                to=email,
                subject="subject",
                html_content="html_content"
            )

            self.app_debug_print(f"Welcome email sent to {email}", True)

        except Exception as e:
            self.app_debug_print(f"Failed to send welcome email: {str(e)}", True)


 
    async def validate_logged_in_user_password(self,
    request, background_tasks, payload:LoggedInUserPasswordValidationRequest, accept_language: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """Register a new user with email for   Connection"""
        try:

            user_info = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            password = payload.password
            user_data = await SysUserModel.get(ObjectId(user_info['id']))
            ip_address = await AuthenticatedService.get_optional_api_address(request)
            if not user_info:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language,username="")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
            self.app_debug_print(f"\n\n\n\n user_info >>>: {user_info}\n\n\n",True)
            self.app_debug_print(f"\n\n\n\n device_hashed_id >>>: {device_hashed_id}\n\n\n",True)

            if not user_info:
                message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
                self.app_debug_print(f"message : {message}",)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Check if account is locked
            if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
                if user_info['login_locked_until'] and user_info['login_locked_until'] > datetime.now(timezone.utc):
                    message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=message
                    )
                else:
                    # Unlock the account if the lock period has passed
                    user_info['login_fail_attempt_count'] = 0
                    user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                    user_info['login_locked_until'] = None



            self.app_debug_print(f"\n\n\n\n beofore pass werif MFA: {self.accept_language}\n\n\n",False)
            # Verify password
            if not self.verify_password(password, user_data.password):
                incremented = user_info['login_fail_attempt_count'] + 1
                user_data = {
                    "login_fail_attempt_count":incremented,
                }
                if incremented >= 5:
                    user_data = {
                        "login_locked_until": datetime.now(timezone.utc) + timedelta(days=3),
                        "login_fail_status":ELoginResetPasswordFailStatus.LOCKED,
                        **user_data
                    }
                # UPDATE USER mfa
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_info['id'],
                    data=user_data
                )
                if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
                    message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=message
                    )
                else:
                    message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=message
                    )

            # Reset login failure attempts on successful login
            if user_info['login_fail_attempt_count'] > 0:
                user_info['login_fail_attempt_count'] = 0
                user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                user_info['login_locked_until'] = None
                user_data = {
                    "login_fail_attempt_count":0,
                    "login_locked_until":None,
                    "login_fail_status":ELoginResetPasswordFailStatus.NORMAL,
                }
                # UPDATE USER
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_info['id'],
                    data=user_data
                )
            # success response
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":{
                        "valid":True,
                    },
                    "message":"Password is valid",
                }
            )
        except HTTPException:
            raise
        except ValueError as e:
            self.app_debug_print(f"Registration error: {str(e)}", True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            self.app_debug_print(f"Registration error: {str(e)}", True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register user: {str(e)}"
            )


    async def ask_info_validation(self, request: Request, body: dict):
        """
        Validate user information (email or phone number) by sending verification code.

        Flow:
        1. Validate input data (email/phone_number and validation_type)
        2. Generate 6-digit verification code
        3. Create Redis cache key with 20-minute expiry
        4. Send verification code via email or SMS
        5. Return encrypted validation key for verification
        """
        try:
            # optional_user = await self.get_optional_user_info(request,self.accept_language)
            # api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # decoded_token = None
            # if not optional_user:
            #     decoded_token = await self.get_decoded_token(request,EJWTTokenType.REGISTRATION_PROCESS,self.accept_language)
            # if not decoded_token and not optional_user:
            #     message = self.get_response_message(MessageCategory.LOGIN, "TOKEN_INVALID", self.accept_language)
            #     raise HTTPException(status_code=400, detail=message)

            # Validate request body
            self.app_debug_print(f"\n\n body : {body} \n\n", True)
            formatted_body = UserInfoValidation.model_validate(body, context={"language": self.accept_language})

            # Import required services
            from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
            from app.modules.core.services.sms.sms_service import SmsService
            from app.modules.core.services.redis.redis_service import AppRedisService
            from app.modules.core.services.encryption.encryption_service import EncryptionService
            from app.modules.core.services.email.email_service import EmailService
            import random
            import string
            import uuid
            import json
            from datetime import datetime, timedelta

            # Extract validation data
            validation_type = formatted_body.validation_type
            email = formatted_body.email
            phone_number = formatted_body.phone_number
            app_signature = (body.get("app_signature") or "").strip()

            # Debug logging
            self.app_debug_print(f"\n\n validation_type: {validation_type} (type: {type(validation_type)}) \n\n", True)
            self.app_debug_print(f"\n\n EUserInfoValidationFlag.EMAIL.value: {EUserInfoValidationFlag.EMAIL.value} \n\n", True)
            self.app_debug_print(f"\n\n EUserInfoValidationFlag.PHONE_NUMBER.value: {EUserInfoValidationFlag.PHONE_NUMBER.value} \n\n", True)

            # Validate required fields based on validation type
            if validation_type == EUserInfoValidationFlag.EMAIL.value:
                if not email:
                    message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "EMAIL_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                # Validate email format
                email_service = EmailService(self.accept_language)
                if not email_service.is_valid_email(email):
                    message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_EMAIL_FORMAT", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                target_contact = email

            elif validation_type == EUserInfoValidationFlag.PHONE_NUMBER.value:
                if not phone_number:
                    message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "PHONE_NUMBER_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                target_contact = phone_number
            else:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_VALIDATION_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Generate 6-digit verification code
            verification_code = ''.join(random.choices(string.digits, k=6))

            # Generate unique validation key
            validation_key = str(uuid.uuid4())

            # verification_code
            self.app_debug_print(f"\n\n verification_code: {verification_code} \n\n", True)

            # Create validation data for Redis cache
            validation_data = {
                "verification_code": verification_code,
                "validation_type": validation_type,
                "target_contact": target_contact,
                # "user_id": user_details.get('id') if user_details else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
                "attempts": 0,
                "max_attempts": 3
            }

            # Store validation data in Redis with 20-minute expiry (1200 seconds)
            redis_key = f"user_validation:{validation_key}"
            await AppRedisService.set_redis_value(
                key=redis_key,
                value=json.dumps(validation_data),
                expiry=1200,  # 20 minutes
                use_env_prefix=True
            )

            # Send verification code
            if validation_type == EUserInfoValidationFlag.EMAIL.value:
                # Send email with verification code
                email_sender = EMailSenderService(self.accept_language)
                subject = self.get_response_message(MessageCategory.EMAIL_TEMPLATE, "VERIFICATION_CODE_SUBJECT", self.accept_language)

                # Create email content
                email_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333;">Verification Code</h2>
                    <p>Your verification code is:</p>
                    <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #007bff; font-size: 32px; margin: 0; letter-spacing: 5px;">{verification_code}</h1>
                    </div>
                    <p>This code will expire in 20 minutes.</p>
                    <p>If you didn't request this verification, please ignore this email.</p>
                </div>
                """

                # show on dev or prod env
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    await email_sender.send_mail_async(
                        to=email,
                        subject=subject,
                        html_content=email_content
                    )

                self.app_debug_print(f"Verification email sent to {email}  verification_code : {verification_code}", True)

            else:  # SMS validation
                # Send SMS with verification code
                sms_service = SmsService()
                if app_signature:
                    sms_message = f"<#> Votre code SenatDigit: {verification_code}\n{app_signature}"
                else:
                    sms_message = f"Your verification code is: {verification_code}. This code expires in 20 minutes."

                # show on dev or prod env
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # background_tasks.add_task(
                    #     sms_service.send_sms_background,
                    #     phone_number=phone_number,
                    #     message=sms_message
                    # )
                    await sms_service.lisoloo_send_sms(
                        phone_number=phone_number,
                        message=sms_message
                    )
                else:
                    await sms_service.lisoloo_send_sms(
                        phone_number=phone_number,
                        message=sms_message
                    )

                self.app_debug_print(f"Verification SMS sent to {phone_number} : verification_code : {verification_code}", True)

            # Encrypt the validation key for client
            encrypted_validation_key = EncryptionService.encrypt_text(validation_key)

            # Prepare response data
            response_data = {
                "validation_key": encrypted_validation_key,
                "validation_type": validation_type,
                "target_contact": target_contact,
                "expires_in_minutes": 20,
                "max_attempts": 3
            }

            message = self.get_response_message(MessageCategory.SUCCESS, "VERIFICATION_CODE_SENT", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success":True,
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": response_data
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def submit_info_otp_validation(self, request: Request, body: dict):
        """
        Verify the validation code sent by user.

        Flow:
        1. Decrypt the validation key from client
        2. Fetch validation data from Redis
        3. Compare verification codes
        4. Update attempts counter
        5. Return success/failure response
        """
        try:
            # Import required services
            from app.modules.core.services.redis.redis_service import AppRedisService
            from app.modules.core.services.encryption.encryption_service import EncryptionService
            import json
            from datetime import datetime

            optional_user = await self.get_optional_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            decoded_token = None
            if not optional_user:
                decoded_token = await self.get_decoded_token(request,EJWTTokenType.REGISTRATION_PROCESS,self.accept_language)
            if not decoded_token and not optional_user:
                message = self.get_response_message(MessageCategory.LOGIN, "TOKEN_INVALID", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Extract data from request body
            encrypted_validation_key = body.get('validation_key')
            submitted_code = body.get('verification_code')

            if not encrypted_validation_key or not submitted_code:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "MISSING_VALIDATION_DATA", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Decrypt the validation key
            try:
                validation_key = EncryptionService.decrypt_text(encrypted_validation_key)
            except Exception as e:
                self.app_debug_print(f"Failed to decrypt validation key: {e}", True)
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_VALIDATION_KEY", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Fetch validation data from Redis
            redis_key = f"user_validation:{validation_key}"
            validation_data_str = await AppRedisService.get_str_redis_value(redis_key, use_env_prefix=True)

            if not validation_data_str:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "VALIDATION_EXPIRED_OR_INVALID", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Parse validation data
            validation_data = json.loads(validation_data_str)

            # Check if validation has expired
            expires_at = datetime.fromisoformat(validation_data['expires_at'])
            if datetime.now(timezone.utc) > expires_at:
                # Clean up expired validation
                await AppRedisService.remove_redis_value(redis_key, use_env_prefix=True)
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "VALIDATION_CODE_EXPIRED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Check attempts limit
            current_attempts = validation_data.get('attempts', 0)
            max_attempts = validation_data.get('max_attempts', 3)

            if current_attempts >= max_attempts:
                # Clean up validation after max attempts
                await AppRedisService.remove_redis_value(redis_key, use_env_prefix=True)
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "MAX_ATTEMPTS_EXCEEDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Increment attempts counter
            validation_data['attempts'] = current_attempts + 1

            # Compare verification codes
            stored_code = validation_data['verification_code']
            if submitted_code.strip() != stored_code:
                # Update attempts in Redis
                await AppRedisService.set_redis_value(
                    key=redis_key,
                    value=json.dumps(validation_data),
                    expiry=1200,  # Keep same expiry
                    use_env_prefix=True
                )

                remaining_attempts = max_attempts - validation_data['attempts']
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_VERIFICATION_CODE", self.accept_language)

                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": message,
                        "data": {
                            "valid": False,
                            "remaining_attempts": remaining_attempts,
                            "attempts_used": validation_data['attempts']
                        }
                    }
                )

            # Verification successful - clean up Redis key
            await AppRedisService.remove_redis_value(redis_key, use_env_prefix=True)

            # Prepare success response
            response_data = {
                "valid": True,
                "validation_type": validation_data['validation_type'],
                "target_contact": validation_data['target_contact'],
                "verified_at": datetime.now(timezone.utc).isoformat()
            }

            message = self.get_response_message(MessageCategory.SUCCESS, "VERIFICATION_SUCCESSFUL", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success":True,
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": response_data
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def check_username_taken(self, request: Request, body: dict):
        """
        Verify the validation code sent by user.

        Flow:
        1. Decrypt the validation key from client
        2. Fetch validation data from Redis
        3. Compare verification codes
        4. Update attempts counter
        5. Return success/failure response
        """
        try:
            # Import required services
            from app.modules.core.services.redis.redis_service import AppRedisService
            from app.modules.core.services.encryption.encryption_service import EncryptionService
            import json
            from datetime import datetime
            api_Consumer = await self.get_api_consumer(request,self.accept_language)

            decoded_token = await self.get_decoded_token(request,EJWTTokenType.REGISTRATION_PROCESS,self.accept_language)
            if not decoded_token:
                message = self.get_response_message(MessageCategory.LOGIN, "TOKEN_INVALID", self.accept_language)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

            # Extract data from request body
            username_taken = body.get('username')
            if not username_taken:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "MISSING_VALIDATION_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

            username_taken = str(username_taken).strip().lower()
            user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__username":username_taken,'filter_ne__account_status':AccountStatusFlag.INACTIVE.value},
                _skip_rls=True,
            )
            if user:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "USERNAME_TAKEN", self.accept_language,username=username_taken)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            # Prepare success response
            response_data = {
                "valid": True,
                "username": username_taken
            }

            message = self.get_response_message(MessageCategory.SUCCESS, "VERIFICATION_SUCCESSFUL", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success":True,
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": response_data
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def init_customer_registration(self, request: Request, background_tasks: BackgroundTasks):
        try:
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)

            # DEVICE CHECKING
            device_hashed_id = getattr(request.state, "deviceHashedId", None)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # GENERATE UNIQUE REGISTRATION KEY TO SAVE IN REDIS
            registration_key = self.generator_service.generate_encryption_key()

            # SAVE IN REDIS
            cache_key = self._generate_cache_key(
                user_id=f"{registration_key}",
                method_name='registration_process',
            )

            # Prepare response data
            response_data = {
                "data": registration_key,
                "device_id_str":device_hashed_id,
                "api_consumer":api_Consumer['id']
            }
            print(f"\n\n\n\n\n\n registration_key response_data : {response_data}")

            # 2. Cache the response data (with verification)
            minutes = 60 * 1
            await self._set_cached_data(cache_key, response_data, ttl=minutes)

            system_country = await SystemCountryService(self.accept_language).get_registration_system_country()
            print(f">> system_country : {system_country}")
            registration_token = self.token_service.create_access_token(
                data={"sub": f"{cache_key}", "device_id_str":device_hashed_id, "type":EJWTTokenType.REGISTRATION_PROCESS},
                token_type=EJWTTokenType.REGISTRATION_PROCESS,
                expires_delta=timedelta(minutes=minutes)  # Expires after 40 minutes 400
            )
            formated_data = {
                "countries":system_country,
                "token":registration_token
            }
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success":True,
                        "status_code":status.HTTP_200_OK,
                        "data":formated_data
                    }
                )
        except Exception as e:
            self.app_debug_print(f"{e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )




    async def login(self,request: Request,payload: LoginRequest):
        try:
            """
            Authenticate a user and return their details.
            """
            # Fetch `Accept-Language` from headers, default to 'fr'
            # Initialize token expiration variables (will be updated later if needed)
            token_expiry_duration = timedelta(minutes=20)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()

            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)


            self.app_debug_print(f"\n\n\n\n usernamer: {payload.username}\n\n\n",True)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            ip_address = await self.get_optional_api_address(request,self.accept_language)
            locationInfo = await self.get_location_from_ip_secure(request,self.accept_language)
            # Get the device info from the request
            device_info = await self.get_optional_device_info(request,self.accept_language)

            username = str(payload.username).strip()
            password = str(payload.password).strip()
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__username":str(username).lower().strip()},
                _skip_rls=True,
            )
            # history
            self.app_debug_print(f"\n\n\n\n user_info >>>> login : {user_info}\n\n\n",True)
            self.app_debug_print(f"\n\n\n\n device_hashed_id >>>: {device_hashed_id}\n\n\n",True)

            if not user_info:
                message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
                self.app_debug_print(f"message : {message}",)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Check if account is locked
            if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
                if user_info['login_locked_until'] and user_info['login_locked_until'] > datetime.now(timezone.utc):
                    message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=message
                    )
                else:
                    # Unlock the account if the lock period has passed
                    user_info['login_fail_attempt_count'] = 0
                    user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                    user_info['login_locked_until'] = None



            self.app_debug_print(f"\n\n\n\n beofore pass werif MFA: {self.accept_language}\n\n\n",False)
            # Verify password
            if not self.verify_password(password, user_info['password']):
                incremented = user_info['login_fail_attempt_count'] + 1
                user_data = {
                    "login_fail_attempt_count":incremented,
                }
                if incremented >= 5:
                    user_data = {
                        "login_locked_until": datetime.now(timezone.utc) + timedelta(days=3),
                        "login_fail_status":ELoginResetPasswordFailStatus.LOCKED,
                        **user_data
                    }
                # UPDATE USER mfa
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_info['id'],
                    data=user_data
                )
                if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
                    message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=message
                    )
                else:
                    message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=message
                    )

            # Reset login failure attempts on successful login
            if user_info['login_fail_attempt_count'] > 0:
                user_info['login_fail_attempt_count'] = 0
                user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                user_info['login_locked_until'] = None
                user_data = {
                    "login_fail_attempt_count":0,
                    "login_locked_until":None,
                    "login_fail_status":ELoginResetPasswordFailStatus.NORMAL,
                }
                # UPDATE USER
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_info['id'],
                    data=user_data
                )

            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub": str(user_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.MFA_VERIFICATION},
                token_type=EJWTTokenType.MFA_VERIFICATION,
                expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
            )

            # Get MFA (Multi-factor Authentication) settings
            default_mfa = None
            mfas = await self.user_available_login_mfa(sys_user_id=user_info['id'],accept_language=self.accept_language)
            self.app_debug_print(f"\n\n\n\n IN MFA: {len(mfas)}\n\n\n",True)
            mfas_with_icon = [];
            for element in mfas:
                self.app_debug_print(f"\n\n mfa element :{element}",False)
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 1 >> {element['name']['display_value']} \n\n\n",True)
                icon_rel = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    output_data_type=OutputDataType.DATA_TABLE.value,
                    query={
                        "filter__targeted_id":element["id"]["display_value"]
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 2 {icon_rel['ref_icon_id']} \n\n\n",True)
                if icon_rel:
                    icon = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_ICON,
                        output_data_type=OutputDataType.DATA_TABLE.value,
                        query={
                            "filter___id":icon_rel["ref_icon_id"]["display_value"],
                        },
                        sort={"created_at": -1},
                        _skip_rls=True,
                    )
                    self.app_debug_print(f"\n\n\n\n IN MFA LOOP 3 \n\n\n",True)
                    if icon:
                        mfas_with_icon.append({
                            **element,
                            "icon":icon
                        })
                    else :
                        mfas_with_icon.append(element)
                    self.app_debug_print(f"\n\n\n\n IN MFA LOOP 4 \n\n\n",True)
                else :
                    mfas_with_icon.append(element)

            if len(mfas_with_icon) > 0 :
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 5 \n\n\n",True)
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 5 {len(mfas_with_icon)} \n\n\n",True)
                default_mfa = mfas_with_icon[0]
            self.app_debug_print(f"\n\n\n\n AFTER MFA: {len(mfas)}\n\n\n",True)
            # DEVICE CHECKING
            device_hashed_id = getattr(request.state, "deviceHashedId", None)
            list_of_user_devices = getattr(request.state, "listOfUserDevices", [])

            # filter by user id
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_info['id']) 
            self.app_debug_print(f"\n\n\n\n LAST STEP 1 USER DEVICE INFO : {user_device_info} \n\n\n",True)

            sys_organization_id = user_info['sys_organization_id']
            if not user_device_info:
                user_device_info = await self.device_service.create_new_user_device(
                    sys_user_id=user_info['id'],
                    device_id_str=device_hashed_id,
                    sys_organization_id=sys_organization_id,
                    device_info=device_info,
                    accept_language=self.accept_language
                )
            else :
                # CHECK IF DEVICE IS USED BY THE SAME USER
                if user_device_info['sys_user_id'] != user_info['id']:
                    user_device_info = await self.device_service.create_new_user_device(
                        sys_user_id=user_info['id'],
                        device_id_str=device_hashed_id,
                        sys_organization_id=sys_organization_id,
                        device_info=device_info,
                        accept_language=self.accept_language
                    )
                    # message = self.get_response_message(MessageCategory.COMMON, "DEVICE_ALREADY_USED_BY_ANOTHER_USER",self.accept_language,email=support_email)
                    # return CustomJSONResponse(
                    #     status_code=status.HTTP_401_UNAUTHORIZED,
                    #     content={
                    #         "message":message,
                    #         "support_email":support_email,
                    #         "is_device_related_issue":True
                    #     }
                    # )
            self.app_debug_print(f"\n\n\n\n LAST STEP 2 USER DEVICE CREATION : {user_device_info} \n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
            self.app_debug_print(f"\n\n\n\n LAST STEP 3\n\n\n",True)
            user_config_info = await self.device_service.create_or_get_user_config(
                sys_user_id=user_info['id'],
                accept_language=self.accept_language
            )
            self.app_debug_print(f"\n\n\n\n LAST STEP 4\n\n\n",True)
            if not user_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_CONFIG",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )

            allowed_device_count = user_config_info.get('allowed_device_count',0)
            self.app_debug_print(f"\n\n\n\n LAST STEP 5\n\n\n",True)
            # GET ALL ALLOWED DEVICES
            allowed_devices = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__sys_user_id":user_info['id'],
                    "filter__status":EUserDeviceStatus.ALLOWED.value
                },
                _skip_rls=True,
            )

            # GET COUNT LOGIN HISTORY WHERE session_actual_expiration DATE IS GREATER OR EQUAL TO NOW GROUP BY cfg_user_device_id
            # pipeline = [
            #     {
            #         "$match": {
            #             "sys_user_id": user_info['id'],
            #             "status":ELoginStatus.LOGGED_IN.value,
            #             "session_actual_expiration": {"$gte": datetime.now(timezone.utc)}
            #         }
            #     },
            #     {
            #         "$group": {
            #             "_id": "$cfg_user_device_id",
            #             "count": {"$sum": 1}
            #         }
            #     },
            #     {
            #         "$project": {
            #             "cfg_user_device_id": "$_id",
            #             "login_count": "$count",
            #             "_id": 0
            #         }
            #     }
            # ]

            # login_histories = await self.generic_service.fetch_native_aggregate_data_from_collection(
            #     collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
            #     all_data=True,
            #     output_data_type=OutputDataType.DEFAULT,
            #     pipeline=pipeline,
            # )

            # active_login_device_session_count = sum(login['login_count'] for login in login_histories)

            # CHECK IF DEVICE IS NOT ALLOWED
            self.app_debug_print(f"\n\n\n\n LAST STEP 6 : {user_device_info} \n\n\n",True)
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                self.app_debug_print(f"\n\n\n\n LAST STEP 7 : {user_device_info} \n\n\n",True)
                # CHECK IF DEVICE IS BLOCKED
                if user_device_info['status'] == EUserDeviceStatus.LOCKED.value:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 8 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_LOCKED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
                # CHECK IF DEVICE IS REVOQUED
                if user_device_info['status'] == EUserDeviceStatus.REVOQUED.value:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 9 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_REVOQUED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
                token = self.token_service.create_access_token(
                    data={"sub": str(user_device_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                    token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                    expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
                )
                # Initialize token expiration variables
                token_expiry_duration = timedelta(minutes=20)
                token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
                token_expires_in = token_expiry_duration.total_seconds()
                self.app_debug_print(f"\n\n\n\n LAST STEP 10 : {user_device_info} \n\n\n",True)
                # CHECK IF MAX DEVICE REACHED
                if len(allowed_devices) >= allowed_device_count:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 10 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.COMMON, "MAX_DEVICE_REACHED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )
                self.app_debug_print(f"\n\n\n\n LAST STEP 11 : {user_device_info} \n\n\n",True)
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )
            # 1. Check allowed platform
            # await check_allowed_platform(user_id=user.id, platform=platform, self.accept_language=self.accept_language)


            self.app_debug_print(f"\n\n\n\n AFTER DEVICE CREATION: {self.accept_language}\n\n\n",False)
            # Get current time in UTC
            await self.login_service.get_or_create_init_login_history_in_30_min(
                sys_user_id=user_info['id'],
                ip_address=ip_address,
                cfg_user_device_id=user_device_info.get("id",None) if user_device_info else None,
                sys_organization_id=user_info['sys_organization_id'],
                device_id_str=device_hashed_id,
                accept_language=self.accept_language
            )

            if 'user_account_hash' not in user_info:
                # TODO: UPDATE USER TO ADD user_account_hash login_fail_status
                user_account_hash = HashService.generate_hash(f"{user_info['id']}")
                data_update = {
                    "user_account_hash":user_account_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=user_info['id'], data=data_update)  # TODO: Update user to add user_account_hash
            if 'user_account_socket_hash' not in user_info:
                # TODO: UPDATE USER TO ADD user_account_socket_hash
                user_account_socket_hash = HashService.generate_hash(user_info['id'])
                data_update = {
                    "user_account_socket_hash":user_account_socket_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=user_info['id'], data=data_update)  # TODO: Update user to add user_account_socket_hash
            last = {
                "status_code":status.HTTP_200_OK,
                "redirect_to_mfa":True,

                "mfas":mfas_with_icon,
                "default_mfa":default_mfa,
                "access_token":token,
                "username":user_info['username'],
            }
            self.app_debug_print(f"\n\n\n\n LAST : {last}\n\n\n",False)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "redirect_to_mfa":True,

                        "mfas":mfas_with_icon,
                        "default_mfa":default_mfa,
                        "access_token":token,
                        "expires_in":token_expires_in,
                        "expires_at":token_expires_at,
                        "username":user_info['username'],
                    }
                )

        except Exception as e:
            format_error = format_exception(f"error login ",e)
            self.app_debug_print(f"\n\n\n format_error login : {format_error}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def get_specific_otp(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        mfa_type: str = Query(..., description="The type of MFA (e.g., email, phone)")
    ):
        try:

            # DECODE USER TOKEN
            self.app_debug_print(f"\n\n\n before get_user_info \n\n\n",True)
            user_details = await self.get_user_info_from_unsecured_path(request,self.accept_language,EJWTTokenType.MFA_VERIFICATION)
            self.app_debug_print(f"\n\n\n user_details get otp {user_details} \n\n\n",True)

            device_hashed_id = self.get_optional_device_hashed_id(request,self.accept_language)

            # user_details = await self.get_user_info(request=request,self.accept_language=accept_language)
            # api_Consumer = await self.get_api_consumer(request=request,self.accept_language=accept_language)
            # user_profil = await self.get_user_profil(request=request,self.accept_language=accept_language)

            # Get current time in UTC
            now = datetime.now(timezone.utc)

            # Calculate the time 30 minutes ago
            start_time = now - timedelta(minutes=10)

            # Query to fetch login history from the last 30 minutes
            login_history_query = {
                "sys_user_id": user_details['id'],
                "status": ELoginStatus.INIT_LOGIN.value,
                "device_id_str":device_hashed_id,
                "created_at": {"$gte": start_time, "$lt": now}
            }
            self.app_debug_print(f"login_history_query data query > :  {login_history_query}",True)

            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )
            self.app_debug_print(f"loginHistory >>> :  {loginHistory}",True)

            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            otp_code = GeneratorService.generate_otp(length=6)
            h_data = {
                "otp":f"{otp_code}"
            }
            # UPDATE OTP ON LOGIN HISTORY
            result_update = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=loginHistory['id'],
                data=h_data
            )
            self.app_debug_print(f"\n\n result_update : {result_update} \n\n",True)

            self.app_debug_print(f"\n\n otp_code : {otp_code} \n\n",True)

            if mfa_type == MFaFlag.EMAIL.value:
                email = user_details.get("email")
                if not email:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                mail_title_translated =  self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_TITLE", self.accept_language)
                # self.app_debug_print(f"mail_title_translated : {mail_title_translated}")
                mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_BODY", self.accept_language, otp_code=otp_code)
                # self.app_debug_print(f"mail_message_translated : {mail_message_translated}")
                second_mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_SECOND_MESSAGE", self.accept_language)
                # self.app_debug_print(f"second_mail_message_translated : {second_mail_message_translated}")
                mail_note_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_NOTE", self.accept_language)
                # self.app_debug_print(f"mail_note_translated : {mail_note_translated}")
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # Send email in background to avoid blocking the request
                    self.app_debug_print(f" current env : {env}",False)
                    # background_tasks.add_task(
                    #     self.email_sender_service.send_simple_email_background,
                    #     email_to=email,
                    #     subject=f"{otp_code} - OTP",
                    #     mail_title_translated=mail_title_translated,
                    #     mail_message_translated=mail_message_translated,
                    #     second_mail_message_translated=second_mail_message_translated,
                    #     mail_note_translated=mail_note_translated,
                    #     accept_language=self.accept_language
                    # )
                asyncio.create_task(asyncio.to_thread(
                    self.email_sender_service.send_simple_email_background,
                    email_to=email,
                    subject=f"{otp_code} - OTP",
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language
                ))

                # Return the formatted response message
                sms= self.get_response_message(MessageCategory.COMMON, "OTP_SENT_EMAIL", self.accept_language, email=email)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":sms
                    }
                )

            elif mfa_type == MFaFlag.PHONE_NUMBER.value:
                sms_service = SmsService()
                phone = user_details.get("phone_number")
                if not phone:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_PHONE_NOT_FOUND", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                # Get the translated SMS message
                sms_message = self.get_response_message(
                    MessageCategory.COMMON,
                    "OTP_SMS_MESSAGE",
                    self.accept_language,
                    otp_code=otp_code
                )

                env = settings.ENV.lower()
                if env == "production" or env == "development":
                # Send SMS in background to avoid blocking the request
                    pass 
                    # asyncio.create_task(
                    #     self.sms_service.lisoloo_send_sms(
                    #         phone_number=phone,
                    #         message=sms_message
                    #     )
                    # )
                asyncio.create_task(
                    self.sms_service.lisoloo_send_sms(
                        phone_number=phone,
                        message=sms_message
                    )
                )

                # Return the formatted response message
                message = self.get_response_message(MessageCategory.COMMON, "OTP_SENT_PHONE", self.accept_language, phone=phone)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

        except Exception as e:
            self.app_debug_print(f"Error sending OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def resend_otp(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        mfa_type: str = Query(..., description="The type of MFA (e.g., email, phone)")
    ):
        try:

            self.app_debug_print(f" RESET OTP accept_language :  {self.accept_language}",True)
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            device_hashed_id = self.get_optional_device_hashed_id(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            self.app_debug_print(f" RESET OTP now :  {now}",True)
            # Calculate the time 30 minutes ago
            start_time = now - timedelta(minutes=10)

            # Query to fetch login history from the last 30 minutes
            login_history_query = {
                "sys_user_id": user_details['id'],
                "status": ELoginStatus.INIT_LOGIN.value,
                "device_id_str":device_hashed_id,
                "created_at": {"$gte": start_time, "$lt": now}
            }
            # self.app_debug_print(f"login_history_query :  {login_history_query}")

            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )
            self.app_debug_print(f" RESET OTP loginHistory :  {loginHistory}",True)

            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            otp_code = loginHistory.get("otp")
            if not otp_code:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            self.app_debug_print(f"\n\n otp_code : {otp_code} \n\n",True)

            if mfa_type == MFaFlag.EMAIL.value:
                email = user_details.get("email")
                if not email:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND",self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                mail_title_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_TITLE",self.accept_language)
                # self.app_debug_print(f"mail_title_translated : {mail_title_translated}")
                mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_BODY",self.accept_language, otp_code=otp_code)
                # self.app_debug_print(f"mail_message_translated : {mail_message_translated}")
                second_mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_SECOND_MESSAGE",self.accept_language)
                # self.app_debug_print(f"second_mail_message_translated : {second_mail_message_translated}")
                mail_note_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_NOTE",self.accept_language)
                # self.app_debug_print(f"mail_note_translated : {mail_note_translated}")
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # Send email in background to avoid blocking the request
                    self.app_debug_print(f" current env : {env}",False)
                    # asyncio.create_task(asyncio.to_thread(
                    #     self.email_sender_service.send_simple_email_background,
                    #     email_to=email,
                    #     subject=f"{otp_code} - OTP",
                    #     mail_title_translated=mail_title_translated,
                    #     mail_message_translated=mail_message_translated,
                    #     second_mail_message_translated=second_mail_message_translated,
                    #     mail_note_translated=mail_note_translated,
                    #     accept_language=self.accept_language
                    # ))
                asyncio.create_task(asyncio.to_thread(
                    self.email_sender_service.send_simple_email_background,
                    email_to=email,
                    subject=f"{otp_code} - OTP",
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language
                )) 

                # Return the formatted response message
                sms= self.get_response_message(MessageCategory.COMMON, "OTP_SENT_EMAIL",self.accept_language, email=email)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":sms
                    }
                )

            elif mfa_type == MFaFlag.PHONE_NUMBER.value:
                phone = user_details.get("phone_number")
                if not phone:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_PHONE_NOT_FOUND",self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                # Get the translated SMS message
                sms_message = self.get_response_message(
                    MessageCategory.COMMON,
                    "OTP_SMS_MESSAGE",
                    self.accept_language,
                    otp_code=otp_code
                )
                self.app_debug_print(f" RESET OTP sms_message :  {sms_message}",True)
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    pass
                    # Send SMS in background to avoid blocking the request
                    # asyncio.create_task(
                    #     self.sms_service.lisoloo_send_sms(
                    #         phone_number=phone,
                    #         message=sms_message
                    #     )
                    # )
                asyncio.create_task(
                    self.sms_service.lisoloo_send_sms(
                        phone_number=phone,
                        message=sms_message
                    )
                )

                # Return the formatted response message
                message = self.get_response_message(MessageCategory.COMMON, "OTP_SENT_PHONE",self.accept_language, phone=phone)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE",self.accept_language)
                raise HTTPException(status_code=400, detail=message)

        except Exception as e:
            self.app_debug_print(f"Error sending OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def send_password_init_email(
        self,
        request: Request,
        payload:PasswordInitRequest,
        background_tasks: BackgroundTasks
    ):
        try:


            # DECODE USER TOKEN
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            # GET IP ADDRESS
            ip_address = await self.get_optional_api_address(request,self.accept_language)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)

            username = payload.username
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__username":str(username).lower().strip()},
                _skip_rls=True,
            )

            if not user_info:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "INVALID_CREDENTIALS",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # DEVICE CHECKING
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_info['id']) 
            # TODO: CHECK USER AGENT IN THE HEADER AND THE ONE SAVED IN DB

            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Get current time in UTC
            now = datetime.now(timezone.utc)
            end_of_validity = now - timedelta(minutes=30)

            # GENERATE OTP
            otp_code = GeneratorService.generate_otp(length=6)
            # self.app_debug_print(f"userInfo :  {user_id}")
            data_history_query = {
                "sys_user_id":user_info['id'],
                "otp":f"{otp_code}",
                "ip_address":ip_address,
                "cfg_user_device_id":user_device_info.get("id"),
                "status":ELoginStatus.INIT_PASSWORD_PROCESS.value,
            }
            self.app_debug_print(f" RESET PASSWORD data_history_query :  {data_history_query}")
            filter_history_query = {
                "filter__sys_user_id":user_info['id'],
                "filter__status":ELoginStatus.INIT_PASSWORD_PROCESS.value,
                "filter__device_id_str":device_hashed_id,
                "filter__created_at": {"$gte": end_of_validity}
            }

            resetPasswHistory = await self.login_service.get_or_create_init_with_data_history(data=data_history_query,filter_query=filter_history_query)
            self.app_debug_print(f"RESET PASSWORD History :  {resetPasswHistory}")

            if not resetPasswHistory:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "MISSING_PASSWORD_RESET_HISTORY",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            otp_code = resetPasswHistory["otp"]
            if not otp_code:
                # GENERATE OTP
                otp_code = GeneratorService.generate_otp(length=6)
                h_data = {
                    "otp":f"{otp_code}"
                }
                # UPDATE OTP ON LOGIN HISTORY
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    item_id=resetPasswHistory['id'],
                    data=h_data
                )

            self.app_debug_print(f"\n\n otp_code : {otp_code} \n\n")
            email = user_info['email']
            if not email:
                message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            mail_title_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "SUCCESS_PASSWORD_INIT_PROCESS_TITLE",self.accept_language)

            mail_message_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_BODY",self.accept_language, otp_code=otp_code)

            second_mail_message_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_SECOND_MESSAGE",self.accept_language,minutes=30)

            mail_note_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_NOTE",self.accept_language)


            reset_password_redirect_token = self.token_service.create_access_token(
                data={"sub": resetPasswHistory['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.PASSWORD_RESET_REDIRECTED},
                token_type=EJWTTokenType.PASSWORD_RESET_REDIRECTED,
                expires_delta=timedelta(minutes=30)  # Expires after 30 minutes
            )
            reset_password_redirect_url = f"{settings.FRONT_END_ANGULAR_BASE_URL}/gen-reset/{reset_password_redirect_token}"

            update_here_message = self.get_response_message(MessageCategory.PASSWORD_RESET, "CLICK_HERE_TO_UPDATE",self.accept_language)

            # Send email in background to avoid blocking the request
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.email_sender_service.send_email_background(
                    email_to=email,
                    subject=f"{otp_code} - {mail_title_translated}",
                    action_button_text=update_here_message,
                    action_button_url=reset_password_redirect_url,
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language
                )
            )

            # Return the formatted response message
            mask_email = mask_email_or_phone_util(email)
            sms = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_LINK_EMAIL_SENT",self.accept_language, email=mask_email)

            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub": str(resetPasswHistory['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.PASSWORD_INIT_PROCESS},
                token_type=EJWTTokenType.PASSWORD_INIT_PROCESS,
                expires_delta=timedelta(minutes=30)  # Expires after 30 minutes
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":sms,
                    "access_token":token,
                    "username":user_info['username'],
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error sending PASSWORD INIT EMAIL: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def resend_reset_password_email(
        self,
        request: Request,
        background_tasks: BackgroundTasks
    ):
        try:


            # CHECK API CONSUMER EXISTANCE
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            # DECODE USER TOKEN
            decoded_token = await self.token_service.get_decoded_header_token(request=request, expected_type=EJWTTokenType.PASSWORD_INIT_PROCESS,accept_language = self.accept_language)
            # DEVICE CHECKING
            user_device_info = await self.get_optional_device_info(request,self.accept_language)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)


            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Get current time in UTC
            now = datetime.now(timezone.utc)
            end_of_validity = now - timedelta(minutes=30)

            passw_reset_history_query = {
                "filter___id":decoded_token['sub'],
                "filter__status":ELoginStatus.INIT_PASSWORD_PROCESS.value,
                "filter__device_id_str":device_hashed_id,
                "filter__created_at": {"$gte": end_of_validity}
            }

            resetPasswHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=passw_reset_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )

            if not resetPasswHistory:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "MISSING_PASSWORD_RESET_HISTORY",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":resetPasswHistory['sys_user_id']},
                _skip_rls=True,
            )

            if not user_info:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "INVALID_CREDENTIALS",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": user_info['id']},
                _skip_rls=True,
            )

            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            email = user_details.get("email")
            if not email:
                message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            mail_title_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "SUCCESS_PASSWORD_INIT_PROCESS_TITLE",self.accept_language)

            mail_message_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_BODY",self.accept_language)

            second_mail_message_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_SECOND_MESSAGE",self.accept_language,minutes=30)

            mail_note_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_NOTE",self.accept_language)


            reset_password_redirect_token = self.token_service.create_access_token(
                data={"sub": str(resetPasswHistory['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.PASSWORD_RESET_REDIRECTED},
                token_type=EJWTTokenType.PASSWORD_RESET_REDIRECTED,
                expires_delta=timedelta(minutes=30)  # Expires after 30 minutes
            )
            reset_password_redirect_url = f"{settings.FRONT_END_ANGULAR_BASE_URL}/gen-reset/{reset_password_redirect_token}"

            update_here_message = self.get_response_message(MessageCategory.PASSWORD_RESET, "CLICK_HERE_TO_UPDATE",self.accept_language)
            # Send email in background to avoid blocking the request
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.email_sender_service.send_email_background(
                    email_to=email,
                    subject=f"{resetPasswHistory['otp']} - {mail_title_translated}",
                    action_button_text=update_here_message,
                    action_button_url=reset_password_redirect_url,
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language
                )
            )

            # Return the formatted response message
            mask_email = mask_email_or_phone_util(email)
            # self.app_debug_print(f" \n mask_email : {mask_email}")
            sms = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_LINK_EMAIL_SENT",self.accept_language, email=mask_email)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":sms,
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error sending PASSWORD INIT EMAIL: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def initiate_device_activation(
        self,
        request: Request,
        background_tasks: BackgroundTasks
    ):
        try:
            # CHECK API CONSUMER EXISTANCE
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            # DECODE USER TOKEN
            decoded_token = await self.token_service.get_decoded_header_token(request=request, expected_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,accept_language = self.accept_language)
            # DEVICE CHECKING
            user_device_info = await self.get_optional_device_info(request,self.accept_language)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)


            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            user_device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":decoded_token['sub']},
                _skip_rls=True,
            )

            print(f"\n\n\n user_device >>>> : {user_device}")

            if not user_device:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "INVALID_CREDENTIALS",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": user_device['sys_user_id']},
                _skip_rls=True,
            )

            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # email = user_details.get("email")
            # if not email:
            #     message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND",self.accept_language)
            #     raise HTTPException(status_code=400, detail=message)

            mail_title_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_VALIDATION_REQUEST_TITLE",self.accept_language)

            mail_message_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_EMAIL_BODY",self.accept_language,first_name=user_details['first_name'],last_name=user_details['last_name'],email=user_details['email'])

            second_mail_message_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_EMAIL_SECOND_MESSAGE",self.accept_language,minutes=60)

            mail_note_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_EMAIL_NOTE",self.accept_language)

            sms_message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_EMAIL_BODY",self.accept_language,first_name=user_details['first_name'],last_name=user_details['last_name'],email=user_details['email'])


            validate_device_redirect_token = self.token_service.create_access_token(
                data={"sub": str(user_device['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.REQUEST_DEVICE_ACTIVATION},
                token_type=EJWTTokenType.REQUEST_DEVICE_ACTIVATION,
                expires_delta=timedelta(minutes=60)  # Expires after 60 minutes
            )
            validate_device_redirect_url = f"{settings.FRONT_END_ANGULAR_BASE_URL}/activate-device/{validate_device_redirect_token}"
            update_here_message = self.get_response_message(MessageCategory.LOGIN, "CLICK_HERE_TO_ACTIVATE_DEVICE",self.accept_language)

            # CHECK IF DEVICE IS ALREADY ACTIVATED
            if user_device['status'] == EUserDeviceStatus.ALLOWED.value:
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ALREADY_ACTIVATED",self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )

            # CHECK IF DEVICE IS BLOCKED
            if user_device['status'] == EUserDeviceStatus.LOCKED.value:
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_LOCKED",self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )

            # CHECK IF DEVICE IS REVOQUED
            if user_device['status'] == EUserDeviceStatus.REVOQUED.value:
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_REVOQUED",self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )

            # CHECK IF DEVICE OWNER IS ORGANIZATION ADMIN, IF YES ACTIVATE DEVICE
            device_user_pipeline = [
                # join rbac_role
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_ROLE.model_name}",
                        "localField": "rbac_role_id",
                        "foreignField": "_id",
                        "as": f"unwind__{CollectionKey.RBAC_ROLE.model_name}"
                    }
                },
                # unwind rbac_role 
                {
                    "$unwind": f"$unwind__{CollectionKey.RBAC_ROLE.model_name}"
                },
                # match
                {
                    "$match": {
                        "_id": ObjectId(user_details['id']),
                        "is_activated": True,
                        f"unwind__{CollectionKey.RBAC_ROLE.model_name}.is_default":True,
                        # ADD FILTER WHERE ROLE FLAG  ENDS WITH _super_admin
                        f"unwind__{CollectionKey.RBAC_ROLE.model_name}.flag": {
                            "$regex": ".*_super_admin$"
                        }
                    }
                }
            ]
            device_user_is_admin = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                pipeline=device_user_pipeline,
            )
            if len(device_user_is_admin) > 0:
                # UPDATE USER DEVICE
                h_data = {
                    "status":EUserDeviceStatus.ALLOWED.value,
                }
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.CFG_USER_DEVICE,
                    item_id=user_device['id'],
                    data=h_data
                )
                # Get current time in UTC
                now = datetime.now(timezone.utc)
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_SUCCESS_MESSAGE",self.accept_language,name=user_details['first_name'],date=now.strftime("%d/%m/%Y"),time=now.strftime("%H:%M"))
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message,
                    },
                    headers={"Content-Type": "application/json"}
                )


            # GET ALL organization admin accounts where rbac_role flag ends with _admin and is_default == true
            pipeline = [
                # join rbac_role
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_ROLE.model_name}",
                        "localField": "rbac_role_id",
                        "foreignField": "_id",
                        "as": f"unwind__{CollectionKey.RBAC_ROLE.model_name}"
                    }
                },
                # unwind rbac_role
                {
                    "$unwind": f"$unwind__{CollectionKey.RBAC_ROLE.model_name}"
                },
                # match
                {
                    "$match": {
                        "sys_organization_id": ObjectId(user_details['sys_organization_id']),# user_details['sys_organization_id'],
                        "is_activated": True,
                        f"unwind__{CollectionKey.RBAC_ROLE.model_name}.is_default":True,
                        # ADD FILTER WHERE ROLE FLAG  ENDS WITH _super_admin
                        f"unwind__{CollectionKey.RBAC_ROLE.model_name}.flag": {
                            "$regex": ".*_super_admin$"
                        }
                    }
                },
                {
                    "$project": {
                        "email": 1,
                        "first_name": 1,
                        "last_name": 1,
                        "phone_number": 1,
                        "gender": 1,
                        "sys_organization_id": 1,
                        "rbac_role_id": 1,
                        "username": 1,

                    }
                }
            ]
            admin_users = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                pipeline=pipeline,
            )

            # 'email'
            self.app_debug_print(f"admin_users : {admin_users}",True)
            for admin_user in admin_users:
                self.app_debug_print(f"admin_user : {admin_user}",True)
                # send email to admin users in background
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda u=admin_user: self.email_sender_service.send_email_background(
                        email_to=u['email'],
                        subject=f"{user_device['identifier']} - {mail_title_translated}",
                        action_button_text=update_here_message,
                        action_button_url=validate_device_redirect_url,
                        mail_title_translated=mail_title_translated,
                        mail_message_translated=mail_message_translated,
                        second_mail_message_translated=second_mail_message_translated,
                        mail_note_translated=mail_note_translated,
                        accept_language=self.accept_language
                    )
                )
                # send sms to admin users in background
                # asyncio.create_task(
                #     self.sms_service.lisoloo_send_sms(
                #         phone_number=admin_user['phone_number'],
                #         message=sms_message
                #     )
                # )


            # Return the formatted response message sending_translated_email_with_redirect_button
            # mask_email = mask_email_or_phone_util(email)
            # self.app_debug_print(f" \n mask_email : {mask_email}")
            sms = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_LINK_EMAIL_SENT",self.accept_language)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":sms,
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error sending device validation EMAIL: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def check_reset_password_proceess_token(
        self,
        request: Request,
        payload:PasswordResetTokenRequest,
    ):
        try:

            self.app_debug_print(f"\n\n\n in check_reset_password_proceess_token \n\n\n",True)
            # CHECK API CONSUMER EXISTANCE
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            # DECODE USER PAYLOAD TOKEN
            self.app_debug_print(f"\n\n\n before decoded_token \n\n\n",True)
            decoded_token =  self.token_service.decode_and_verify_token(token=payload.token, expected_type=EJWTTokenType.PASSWORD_RESET_REDIRECTED)
            self.app_debug_print(f"\n\n\n after decoded_token \n\n\n",True)


            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n after saas_config_info \n\n\n",True)
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)

            # Get current time in UTC
            now = datetime.now(timezone.utc)
            end_of_validity = now - timedelta(minutes=30)

            passw_reset_history_query = {
                "filter___id":decoded_token['sub'],
                "filter__status":ELoginStatus.INIT_PASSWORD_PROCESS.value,
                "filter__device_id_str":device_hashed_id,
                "filter__created_at": {"$gte": end_of_validity}
            }

            resetPasswHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=passw_reset_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n step 2 \n\n\n",True)
            if not resetPasswHistory:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "MISSING_PASSWORD_RESET_HISTORY",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": resetPasswHistory['sys_user_id']},
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n step 3 \n\n\n",True)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # DEVICE CHECKING
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=resetPasswHistory['sys_user_id']) 
            self.app_debug_print(f"\n\n\n--user_device_info : {user_device_info}\n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub": str(resetPasswHistory['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.PASSWORD_RESET_PROCESS},
                token_type=EJWTTokenType.PASSWORD_RESET_PROCESS,
                expires_delta=timedelta(minutes=30)  # Expires after 30 minutes
            )
            self.app_debug_print(f"\n\n\n step 4 \n\n\n",True)
            sms = self.get_response_message(MessageCategory.PASSWORD_RESET, "RESET_PASSWORD_PROCESS_VALIDATED",self.accept_language)

            # UPDATE RESET PASSWORD HISTORY
            h_data = {
                "status":ELoginStatus.RESET_PASSWORD_PROCESS_VALIDATED.value,
            }
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=resetPasswHistory['id'],
                data=h_data
            )
            self.app_debug_print(f"\n\n\n step 5 \n\n\n",True)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":sms,
                    "access_token":token,
                },
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            self.app_debug_print(f"Error CHECKING PASSWORD PROCESS TOKEN: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def validate_device_activation(
        self,
        request: Request,
        payload:DeviceActivationTokenRequest,
    ):
        try:

            self.app_debug_print(f"\n\n\n in validate_device_activation \n\n\n",True)
            # CHECK API CONSUMER EXISTANCE
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            # DECODE USER PAYLOAD TOKEN
            self.app_debug_print(f"\n\n\n before decoded_token \n\n\n",True)
            decoded_token =  self.token_service.decode_and_verify_token(token=payload.token, expected_type=EJWTTokenType.REQUEST_DEVICE_ACTIVATION)
            self.app_debug_print(f"\n\n\n after decoded_token :{decoded_token} \n\n\n",True)

            logged_in_user = await self.get_user_info(request,self.accept_language)
            self.app_debug_print(f"\n\n\n after logged_in_user :{logged_in_user} \n\n\n",True)
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n after saas_config_info \n\n\n",True)
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)

            # DEVICE CHECKING
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=logged_in_user['sys_user_id']) 
            self.app_debug_print(f"\n\n\n--user_device_info : {user_device_info}\n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Get current time in UTC
            now = datetime.now(timezone.utc)
            end_of_validity = now - timedelta(minutes=30)

            user_device_query = {
                "filter___id":decoded_token['sub'],
            }

            user_device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query=user_device_query,
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n step 2 \n\n\n",True)
            if not user_device:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": user_device['sys_user_id']},
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n step 3 \n\n\n",True)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # CHECK IF DEVICE IS ALREADY ACTIVATED
            if user_device['status'] == EUserDeviceStatus.ALLOWED.value:
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ALREADY_ACTIVATED",self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # CHECK IF DEVICE IS BLOCKED
            if user_device['status'] == EUserDeviceStatus.LOCKED.value:
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_LOCKED",self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # CHECK IF DEVICE IS REVOQUED
            if user_device['status'] == EUserDeviceStatus.REVOQUED.value:
                message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_REVOQUED",self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # UPDATE USER DEVICE
            h_data = {
                "status":EUserDeviceStatus.ALLOWED.value,
            }
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                item_id=user_device['id'],
                data=h_data
            )

            # SEND EMAIL DEVICE USER AND RETURN SUCCESS MESSAGE
            mail_title_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_SUCCESS_TITLE",self.accept_language)

            mail_message_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_SUCCESS_MESSAGE",self.accept_language,name=user_details['first_name'],date=now.strftime("%d/%m/%Y"),time=now.strftime("%H:%M"))
            second_mail_message_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_SUCCESS_SECOND_MESSAGE_TO_USER",self.accept_language)
            mail_note_translated = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_SUCCESS_NOTE",self.accept_language,date=now.strftime("%d/%m/%Y"),time=now.strftime("%H:%M"))
            env = settings.ENV.lower()
            #second_mail_message_translated
            if env == "production" or env == "development":
                self.email_sender_service.sending_translated_email(
                    email_to=user_details['email'],
                    subject=f"{mail_title_translated}",
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    accept_language=self.accept_language
                )

            self.app_debug_print(f"\n\n\n step 4 \n\n\n",True) #minutes
            message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_ACTIVATION_SUCCESS_MESSAGE_TO_ADMIN",self.accept_language,admin_name=logged_in_user['first_name'],name=user_details['first_name'],date=now.strftime("%d/%m/%Y"),time=now.strftime("%H:%M"))
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":message,
                },
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            self.app_debug_print(f"Error CHECKING DEVICE ACTIVATION PROCESS TOKEN: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def refreshToken(
        self,
        request: Request,
    ):
        try:

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)

            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            # Check if device_hashed_id is a CustomJSONResponse (error case)
            # self.app_debug_print(f"\n\n\n device_hashed_id : {isinstance(device_hashed_id, CustomJSONResponse)} {device_hashed_id}\n\n\n", True)
            # self.app_debug_print(f"\n\n\n user_details : {user_details}\n\n\n",True)

            # Generate access token
            token_expires_in = 3600 * 24 * 4
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_expires_in)
            token = self.token_service.create_access_token(
                data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(seconds=token_expires_in)  # Expires after 2 days
            )
            self.app_debug_print(f"\n\n\n token : {token}\n\n\n",True)
            refresh_token = self.token_service.create_access_token(
                data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=7)  # Expires after 2 days
            )
            self.app_debug_print(f"\n\n\n refresh_token : {refresh_token}\n\n\n",True)
            user_mfas = await self.user_configured_mfa(sys_user_id=user_details['id'],accept_language= self.accept_language)

            user_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query={
                    "filter__sys_user_id":user_details['id'],
                    "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
                },
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n user_signature : {user_signature}\n\n\n",True)

            # Compute should_setup_totp dynamically
            should_setup_totp = False
            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value,
                },
                _skip_rls=True,
            )
            if ref_totp_mfa:
                cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        "filter__sys_user_id": user_details['id'],
                        "filter__ref_mfa_id": ref_totp_mfa['id'],
                    },
                    _skip_rls=True,
                )
                if not cfg_user_mfa:
                    should_setup_totp = True
                else:
                    is_disabled = cfg_user_mfa.get("is_disabled", False)
                    if not is_disabled:
                        is_configured = cfg_user_mfa.get("is_configured", False)
                        if not is_configured:
                            if self.check_mfa_setup_needed(cfg_user_mfa):
                                should_setup_totp = True

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,

                    "user":{
                        "id":f"{user_details['id']}",
                        "username":f"{user_details['username']}",
                        "first_name":f"{user_details['first_name']}",
                        "last_name":f"{user_details['last_name']}",
                        "gender":f"{user_details['gender']}",
                        "phone_number":f"{user_details['phone_number']}",
                        "email_address":f"{user_details['email']}",
                        "mfas":user_mfas,
                        "user_account_socket_hash":f"{user_details['user_account_socket_hash']}",
                        "should_setup_totp":should_setup_totp,
                        "should_update_password":user_details.get('should_update_password', False),
                    },
                    "signature":user_signature,
                }
            )
        except Exception as e:
            # Handle case where e might be a CustomJSONResponseException or other types
            if isinstance(e, CustomJSONResponseException):
                self.app_debug_print(f"Error refresh token: CustomJSONResponseException with status {e.response.status_code}",True)
                return e.response  # Return the CustomJSONResponse from the exception
            elif isinstance(e, CustomJSONResponse):
                self.app_debug_print(f"Error refresh token: CustomJSONResponse returned with status {e.status_code}",True)
                return e  # Return the CustomJSONResponse as-is
            elif hasattr(e, 'detail'):
                # Handle HTTPException and similar
                self.app_debug_print(f"Error refresh token: {e.detail}",True)
            else:
                # Handle regular exceptions
                self.app_debug_print(f"Error refresh token: {str(e)}",True)
            # Check if the exception is an HTTPException from get_user_info
            if isinstance(e, HTTPException):
                # If it's a user-related issue (account locked, device changed, etc.)
                # Return a CustomJSONResponse instead of re-raising
                if e.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_423_LOCKED]:
                    detail = e.detail
                    if isinstance(detail, dict):
                        return CustomJSONResponse(
                            status_code=e.status_code,
                            content=detail
                        )
                    else:
                        return CustomJSONResponse(
                            status_code=e.status_code,
                            content={"message": str(detail)}
                        )
                # For other HTTP exceptions, re-raise them
                raise e
            else:
                # Get translated message for unexpected errors
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def mobRefreshToken(
        self,
        request: Request,
        body: dict = Body(...),
    ):
        try:

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            # Check if user_details is a CustomJSONResponse (error case)
            if isinstance(user_details, CustomJSONResponse):
                self.app_debug_print(f"Error getting user info: returning error response", True)
                return user_details

            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # Check if api_Consumer is a CustomJSONResponse (error case)
            if isinstance(api_Consumer, CustomJSONResponse):
                self.app_debug_print(f"Error getting API consumer: returning error response", True)
                return api_Consumer
            # GET HASHED DEVICE ID
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)

            #refresh_token
            self.app_debug_print(f" refresh token body: {body}",True)
            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(days=2)  # Expires after 2 days
            )
            refresh_token = self.token_service.create_access_token(
                data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=2)  # Expires after 2 days
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":{
                        "token":token,
                        "refresh_token":refresh_token
                    }
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error refresh token: {e}")
            # Check if the exception is an HTTPException from get_user_info
            if isinstance(e, HTTPException):
                # If it's a user-related issue (account locked, device changed, etc.)
                # Return a CustomJSONResponse instead of re-raising
                if e.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_423_LOCKED]:
                    detail = e.detail
                    if isinstance(detail, dict):
                        return CustomJSONResponse(
                            status_code=e.status_code,
                            content=detail
                        )
                    else:
                        return CustomJSONResponse(
                            status_code=e.status_code,
                            content={"message": str(detail)}
                        )
                # For other HTTP exceptions, re-raise them
                raise e
            else:
                # Get translated message for unexpected errors
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def bearerRefreshToken(
        self,
        request: Request,
        body: dict = Body(...),
    ):
        """
        Bearer refresh token endpoint to match frontend token management service
        """
        try:
            self.app_debug_print(f"Bearer refresh token request body: {body}", True)

            # Extract refresh token from body
            refresh_token = body.get('refresh_token')
            if not refresh_token:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_DATA", self.accept_language, meta="refresh_token")
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": message}
                )

            # Verify refresh token
            try:
                decoded_token = self.token_service.decode_and_verify_token(
                    token=refresh_token,
                    expected_type=EJWTTokenType.REFRESH_TOKEN
                )
            except Exception as e:
                self.app_debug_print(f"Invalid refresh token: {e}", True)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOKEN", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"message": message}
                )

            # Get user details from decoded token
            user_id = decoded_token.get('sub')
            device_id_str = decoded_token.get('device_id_str')

            if not user_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOKEN", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"message": message}
                )

            # Fetch user details to ensure user still exists and is active
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": user_id},
                accept_language=self.accept_language,
                _skip_rls=True,
            )

            if not user_details:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "USER_NOT_FOUND", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"message": message}
                )

            # Generate new access token and refresh token
            token_expires_in = 3600 * 24 * 4  # 4 days
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_expires_in)

            new_access_token = self.token_service.create_access_token(
                data={"sub": user_id, "device_id_str": device_id_str, "type": EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(seconds=token_expires_in)
            )

            new_refresh_token = self.token_service.create_access_token(
                data={"sub": user_id, "device_id_str": device_id_str, "type": EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=7)  # 7 days for refresh token
            )

            # Get user MFAs and signature info
            user_mfas = await self.user_configured_mfa(sys_user_id=user_id, accept_language=self.accept_language)

            user_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_user_id": user_id,
                    "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id": '',
                },
                _skip_rls=True,
            )

            self.app_debug_print(f"Bearer refresh successful for user: {user_id}", True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "token_type": "Bearer",
                    "expires_in": token_expires_in,
                    "expires_at": token_expires_at.isoformat(),
                    "user": {
                        "id": str(user_details['id']),
                        "username": str(user_details['username']),
                        "first_name": str(user_details['first_name']),
                        "last_name": str(user_details['last_name']),
                        "gender": str(user_details['gender']),
                        "phone_number": str(user_details['phone_number']),
                        "email_address": str(user_details['email']),
                        "mfas": user_mfas,
                        "user_account_socket_hash": str(user_details['user_account_socket_hash']),
                    },
                    "signature": user_signature,
                }
            )

        except Exception as e:
            self.app_debug_print(f"Error in bearer refresh token: {e}", True)

            # Handle different types of exceptions
            if isinstance(e, CustomJSONResponseException):
                return e.response
            elif isinstance(e, CustomJSONResponse):
                return e
            elif isinstance(e, HTTPException):
                if e.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_423_LOCKED]:
                    detail = e.detail
                    if isinstance(detail, dict):
                        return CustomJSONResponse(
                            status_code=e.status_code,
                            content=detail
                        )
                    else:
                        return CustomJSONResponse(
                            status_code=e.status_code,
                            content={"message": str(detail)}
                        )
                raise e
            else:
                # Get translated message for unexpected errors
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"message": message}
                )

    async def verify_totp_validation(
        self,
        request: Request,
        payload:TOtpRequest, ):
        try:
            # Retrieve the user's secret; in production, fetch this from your secure store.
            self.app_debug_print(f"\n\n {payload}\n\n",False)

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            user_id =  user_details.get('id', None)


            mfa_query = {
                "filter__is_activated": True,
                "filter__flag": MFaFlag.SYCAMORE_2FA_APP,
            }
            mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        **mfa_query
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )

            mfa_id =  mfa.get('id', None)
            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_mfas_query = {
                "filter__is_activated": False,
                "filter__sys_user_id":user_id,
                "filter__ref_mfa_id":mfa_id,
            }
            user_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                accept_language=self.accept_language,
                query=user_mfas_query,
                _skip_rls=True,
            )
            if not user_mfa:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            secret = user_mfa.get('secret')
            self.app_debug_print(f"\n\n secret : {secret} \n\n",True)
            if not secret:
                raise HTTPException(status_code=404, detail="User not found")

            # Allow a valid window of 1 time-step before and after to account for clock skew.
            if GeneratorService.verify_totp_code(secret, payload.totp):
                message = self.get_response_message(MessageCategory.SUCCESS, "TOTP_ACTIVATED_SUCCESSFULLY",self.accept_language)

                new_doc = {
                    "is_activated": True,
                    "is_configured": True,
                    "sys_user_id": user_id,
                    "ref_mfa_id": mfa['id'],
                    "secret":secret
                }
                result = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    filter_data={"ref_mfa_id":new_doc['ref_mfa_id'],'sys_user_id':new_doc['sys_user_id']},
                    update_data=new_doc
                )
                self.app_debug_print(f"user mfa config updated : {result}",True)

                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message,
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOTP_CODE",self.accept_language)
                raise HTTPException(status_code=401, detail=message)
        except Exception as e:
            self.app_debug_print(f"Error refresh token: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def verify_totp_to_login(self,request: Request, payload:TOtpRequest, ):
        try:
            # Retrieve the user's secret; in production, fetch this from your secure store.
            self.app_debug_print(f"\n\n {payload}\n\n",False)

            # DECODE USER TOKEN
            user_details = await self.token_service.decode_and_get_user_from_token(
                request=request,
                expected_type=EJWTTokenType.MFA_VERIFICATION,
            )
            self.app_debug_print(f"\n\n\n [verify_totp_to_login] after user_details : {user_details} \n\n\n",True)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            # api_Consumer = await self.get_api_consumer(request,self.accept_language)
            # user_profil = await self.get_user_profil(request,self.accept_language)
            user_id =  user_details.get('id', None)
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n [verify_totp_to_login] after saas_config_info \n\n\n",True)
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message)


            mfa_query = {
                "filter__is_activated": True,
                "filter__flag": MFaFlag.SYCAMORE_2FA_APP,
            }
            mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        **mfa_query
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )

            mfa_id =  mfa.get('id', None)
            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_mfas_query = {
                "filter__is_activated": True,
                "filter__sys_user_id":user_id,
                "filter__ref_mfa_id":mfa_id,
            }
            user_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                accept_language=self.accept_language,
                query=user_mfas_query,
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n user_mfa : {user_mfa}",True)
            if not user_mfa:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            secret = user_mfa.get('secret')
            if not secret:
                raise HTTPException(status_code=404, detail="User not found")

            # Allow a valid window of 1 time-step before and after to account for clock skew.
            if GeneratorService.verify_totp_code(secret, payload.totp):
                message = self.get_response_message(MessageCategory.SUCCESS, "TOTP_ACTIVATED_SUCCESSFULLY",self.accept_language)

                support_email = await self.get_system_support_email(saas_config_info,self.accept_language)

                self.app_debug_print(f"message : {message}",True)
                user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_details['id']) 
                self.app_debug_print(f"\n\n\n after user_device_info : {user_device_info} \n\n\n",True)
                if not user_device_info:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
                    # raise HTTPException(status_code=404, detail=message)

                # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
                if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                    message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
                loginHistory = await self.login_service.get_today_init_login_history(
                    sys_user_id=user_details['id'],
                    cfg_user_device_id=user_device_info.get("id")
                )
                self.app_debug_print(f"\n\n\n after loginHistory : {loginHistory} \n\n\n",True)
                if not loginHistory:
                    message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)

                # Generate access token
                token = self.token_service.create_access_token(
                    data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                    token_type=EJWTTokenType.LOGIN,
                    expires_delta=timedelta(days=4)  # Expires after 2 days
                )
                refresh_token = self.token_service.create_access_token(
                    data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                    token_type=EJWTTokenType.REFRESH_TOKEN,
                    expires_delta=timedelta(days=7)  # Expires after 2 days
                )
                user_mfas = await self.user_configured_mfa(sys_user_id=user_details['id'],accept_language=self.accept_language)
                generated_session_id = GeneratorService.generate_base32_secret(str(loginHistory['id']))

                # 7 days expiration
                session_actual_expiration_date = datetime.now(timezone.utc) + timedelta(days=7)

                # update many login histories to logout where current device and user
                await self.generic_service.update_many_in_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    data={
                        "status":ELoginStatus.LOGGED_OUT.value,
                    },
                    filter_data={
                        "sys_user_id":user_details['id'],
                        "cfg_user_device_id":user_device_info['id'],
                        "status":ELoginStatus.LOGGED_IN.value,
                    }
                )

                update_data = {
                    "status":ELoginStatus.LOGGED_IN.value,
                    "session_last_activity":datetime.now(timezone.utc),
                    "session_id_str":generated_session_id,
                    "device_id_str":device_hashed_id,
                    "session_actual_expiration":session_actual_expiration_date
                }
                self.app_debug_print(f"\n\n update_data :  {update_data}\n\n")
                # UPDATE OTP ON LOGIN HISTORY
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    item_id=loginHistory['id'],
                    data=update_data
                )

                DebugService.app_debug_print(f"\n\n\nuser_details [user_details] >>>>>> : {user_details}\n\n\n",True)
                user_signature = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__sys_user_id":user_details['id'],
                        "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
                    },
                    _skip_rls=True,
                )



                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,

                        "user":{
                            "id":f"{user_details['id']}",
                            "username":f"{user_details['username']}",
                            "first_name":f"{user_details['first_name']}",
                            "last_name":f"{user_details['last_name']}",
                            "gender":f"{user_details['gender']}",
                            "phone_number":f"{user_details['phone_number']}",
                            "email_address":f"{user_details['email']}",
                            "mfas":user_mfas,
                            "user_account_socket_hash":f"{user_details['user_account_socket_hash']}",
                        },
                        "signature":user_signature,
                        "access_token":token,
                        "refresh_token":refresh_token

                    }
                )


            else:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOTP_CODE",self.accept_language)
                raise HTTPException(status_code=401, detail=message)

        except Exception as e:
            format_error = format_exception(f"[verify_totp_to_login] error login ",e)
            self.app_debug_print(f"Error refresh token: {format_error}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def syc_auth_config_update(self,request: Request ):
        # Retrieve the user's secret; in production, fetch this from your secure store.
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            user_id =  user_details.get('id', None)


            mfa_query = {
                "filter__is_activated": True,
                "filter__flag": MFaFlag.SYCAMORE_2FA_APP,
            }
            mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        **mfa_query
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )

            mfa_id =  mfa.get('id', None)
            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_mfas_query = {
                "filter__is_activated": False,
                "filter__sys_user_id":user_id,
                "filter__ref_mfa_id":mfa_id,
            }
            user_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                accept_language=self.accept_language,
                query=user_mfas_query,
                _skip_rls=True,
            )
            if not user_mfa:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            secret = user_mfa.get('secret')
            self.app_debug_print(f"\n\n secret : {secret} \n\n",True)
            if not secret:
                raise HTTPException(status_code=404, detail="User not found")

            # Allow a valid window of 1 time-step before and after to account for clock skew.
            message = self.get_response_message(MessageCategory.SUCCESS, "TOTP_ACTIVATED_SUCCESSFULLY",self.accept_language)

            new_doc = {
                "is_activated": True,
                "is_configured": True,
                "sys_user_id": user_id,
                "ref_mfa_id": mfa['id'],
                "secret":secret
            }
            result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                filter_data={"ref_mfa_id":new_doc['ref_mfa_id'],'sys_user_id':new_doc['sys_user_id']},
                update_data=new_doc
            )
            self.app_debug_print(f"user mfa config updated : {result}",True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":message,
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error refresh token: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def verify_totp_to_unlock(self,request: Request, payload:TOtpRequest, ):
        try:
            # Retrieve the user's secret; in production, fetch this from your secure store.
            self.app_debug_print(f"\n\n {payload}\n\n",False)

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            user_id =  user_details.get('id', None)


            mfa_query = {
                "filter__is_activated": True,
                "filter__flag": MFaFlag.SYCAMORE_2FA_APP,
            }
            mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        **mfa_query
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )

            mfa_id =  mfa.get('id', None)
            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_mfas_query = {
                "filter__is_activated": True,
                "filter__sys_user_id":user_id,
                "filter__ref_mfa_id":mfa_id,
            }
            user_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                accept_language=self.accept_language,
                query=user_mfas_query,
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n user_mfa : {user_mfa}",True)
            if not user_mfa:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if not mfa or not mfa_id :
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            secret = user_mfa.get('secret')
            if not secret:
                raise HTTPException(status_code=404, detail="User not found")

            # Allow a valid window of 1 time-step before and after to account for clock skew.
            if GeneratorService.verify_totp_code(secret, payload.totp):
                message = self.get_response_message(MessageCategory.SUCCESS, "TOTP_ACTIVATED_SUCCESSFULLY",self.accept_language)

                self.app_debug_print(f"message : {message}",True)

                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message,
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOTP_CODE",self.accept_language)
                raise HTTPException(status_code=401, detail=message)

        except Exception as e:
            self.app_debug_print(f"Error refresh token: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def upload_user_signature_file(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        upload_file: UploadFile = File(...)
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            self.app_debug_print("upload data : ")

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)

            # Read the uploaded file into memory
            self.app_debug_print(f"Uploaded file: {upload_file}", True)
            file_data = await upload_file.read()

            # Generate a unique processing ID for tracking
            import uuid
            processing_id = str(uuid.uuid4())

            # Process image in background to avoid blocking the request
            asyncio.create_task(
                self.process_and_upload_signature_background(
                    file_data=file_data,
                    filename=upload_file.filename,
                    content_type=upload_file.content_type,
                    user_details=user_details,
                    processing_id=processing_id
                )
            )

            # Return immediate response while image is being processed in background
            message = self.get_response_message(MessageCategory.SUCCESS, "IMAGE_PROCESSING_STARTED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": {
                        "processing_status": "Image processing started in background",
                        "processing_id": processing_id,
                        "message": "Your signature is being processed. You will be notified when it's ready."
                    },
                    "message": message
                }
            )

        except Exception as e:
            self.app_debug_print(f"Error during file upload: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")

    def process_and_upload_signature_background(self, file_data, filename, content_type, user_details, processing_id):
        """
        Background task method for processing signature image (background removal, cropping) and uploading.
        This runs asynchronously without blocking the main request.
        """
        try:
            from rembg import remove
            from PIL import Image
            from io import BytesIO
            import requests

            self.app_debug_print(f"Starting background signature processing for user {user_details['id']}", True)

            try:
                # Process the file (remove background, trim, etc.)
                output_data = remove(file_data)  # Use rembg to remove the background
            except Exception as bg_error:
                self.app_debug_print(f"Background removal failed: {bg_error}", True)
                # Fall back to using the original image if background removal fails
                output_data = file_data

            # Open the image using Pillow
            signature_image = Image.open(BytesIO(output_data))

            # Convert the image to RGBA (if not already)
            signature_image = signature_image.convert("RGBA")

            # Get the bounding box of the non-transparent region (signature)
            bbox = signature_image.getbbox()

            # Crop the image to the signature's bounding box
            trimmed_signature = signature_image.crop(bbox)

            # Save the trimmed signature to a BytesIO object
            trimmed_signature_bytes = BytesIO()
            trimmed_signature.save(trimmed_signature_bytes, format="PNG")
            trimmed_signature_bytes.seek(0)

            # Upload file to file system using requests (synchronous in background)
            headers = {
                "authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}"
            }

            files = {"upload_file": (filename, trimmed_signature_bytes.getvalue(), "image/png")}
            response = requests.post(
                f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/files/upload?base_dir={settings.SENAT_DIGIT_APPS_FILE_ORGANIZATION_USER_SIGNATURE_BASE_DIR}",
                files=files,
                headers=headers
            )

            self.app_debug_print(f"Background signature upload response status: {response.status_code}", True)

            if response.status_code in [200, 201]:
                resp = response.json()
                data = resp.get('data', {})

                # Prepare arch file data
                file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/view-file/{data.get('file_str_id_composed')}"
                arch_file_data = {
                    "remote_arch_file_id": data.get('id'),
                    "remote_arch_file_url": data.get('file_url'),
                    "file_name": data.get('file_name'),
                    "file_str_id_composed": data.get('file_str_id_composed'),
                    "file_url": file_url_composed,
                    "file_original_name": data.get('file_original_name'),
                    "file_extension": data.get('file_extension'),
                    "file_type": data.get('file_type'),
                    "file_size": data.get('file_size'),
                    "file_path": data.get('file_path'),
                }

                self.app_debug_print(f"Background signature processed successfully. File data: {arch_file_data}", True)
                self.app_debug_print(f"TODO: Save arch_file_data and user_signature_data to database for user {user_details['id']}", True)

            else:
                self.app_debug_print(f"Failed to upload background signature. Status: {response.status_code}", True)

        except Exception as e:
            self.app_debug_print(f"Failed to process background signature for user {user_details['id']}: {e}", True)
            # Don't raise here as this is a background task


    async def delete_user_signature_file(
        self,
        request: Request,
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            self.app_debug_print("upload data : ")

            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)

            cfg_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id":str(user_details['id'])},
                _skip_rls=True,
            )
            if not cfg_signature:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SIGNATURE_FOUND",self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": message,
                    }
                )

            arch_file = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.ARCH_FILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":str(cfg_signature['arch_file_id'])},
                _skip_rls=True,
            )
            if not arch_file:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_ARCH_FILE_FOUND",self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": message,
                    }
                )
            await self.generic_service.hard_delete_data_from_collection(CollectionKey.ARCH_FILE, str(cfg_signature['arch_file_id']),self.accept_language)
            await self.generic_service.hard_delete_data_from_collection(CollectionKey.CFG_USER_SIGNATURE, str(cfg_signature['id']),self.accept_language)
            if 'remote_arch_file_id' in arch_file:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}"
                    }
                    response = await client.delete(
                        f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/files/delete/{arch_file['remote_arch_file_id']}",
                        headers=headers
                    )


            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED",self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                }
            )

        except Exception as e:
            self.app_debug_print(f"Error during deleting file: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")

    async def get_user_signature_file(
        self,
        request: Request,
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            self.app_debug_print("upload data : ")

            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)

            cfg_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id":str(user_details['id'])},
                _skip_rls=True,
            )
            if not cfg_signature:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SIGNATURE_FOUND",self.accept_language)
                return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "message": message,
                    "data":None
                }
            )
                # return CustomJSONResponse(
                #     status_code=status.HTTP_404_NOT_FOUND,
                #     content={
                #         "status_code": status.HTTP_404_NOT_FOUND,
                #         "message": message,
                #     }
                # )

            arch_file = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.ARCH_FILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":str(cfg_signature['arch_file_id'])},
                _skip_rls=True,
            )
            if not arch_file:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_ARCH_FILE_FOUND",self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": message,
                    }
                )
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED",self.accept_language)
            download_file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/download-file?file_id={arch_file['file_str_id_composed']}"
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": message,
                    "data":{
                        'signature_get_url':arch_file['file_url'],
                        'signature_download_url':download_file_url_composed,
                    }
                }
            )

        except Exception as e:
            self.app_debug_print(f"Error during deleting file: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")


    async def sycAuthConfig(
        self,
        request: Request,

    ):
        try:
            import json as _json
            import time as _time
            from app.modules.core.services.encryption.encryption_service import EncryptionService

            user_details = await self.get_user_info(request,self.accept_language)

            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            user_id =  user_details.get('id', None)
            username =  user_details.get('username', None)

            self.app_debug_print(f"\n\n user_id : {user_id}\n\n",True)
            self.app_debug_print(f"\n\n user_details : {user_details}\n\n",False)

            if not user_details or not user_id:
                self.app_debug_print(f"\n\n user_details or user_id not found : {user_details} - {user_id}\n\n",False)
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # ── Device Pairing QR Code Generation ──
            import secrets as _secrets
            from urllib.parse import quote as _url_quote

            # ── Step 1: Look up MFA reference and user's existing config ──
            mfa_query = {
                "filter__is_activated": True,
                "filter__flag": MFaFlag.SYCAMORE_2FA_APP,
            }
            mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={**mfa_query},
                    sort={"created_at": -1},
                    _skip_rls=True,
                )
            
            self.app_debug_print(f"\n\n mfa : {mfa}\n\n",False)

            mfa_id = mfa.get('id', None) if mfa else None

            # ── Step 2: Check user's existing MFA config to decide on pairing_key ──
            # FIX: Previously we always generated a new secret on every call,
            # which caused the secret to be overwritten when Flutter's TOTP tab
            # called this endpoint a second time (race condition after re-login).
            # Now we check the user's CFG_USER_MFA record first:
            #   - If fully configured (is_activated + is_configured): block re-setup
            #   - If pending pairing (is_activated=False, has secret): reuse existing secret
            #   - Otherwise: generate new secret
            existing_user_mfa = None
            if mfa_id:
                existing_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        "filter__ref_mfa_id": mfa_id,
                        "filter__sys_user_id": user_id,
                    },
                    _skip_rls=True,
                )

            if existing_user_mfa:
                is_activated = existing_user_mfa.get('is_activated', False)
                is_configured = existing_user_mfa.get('is_configured', False)
                existing_secret = existing_user_mfa.get('secret', None)

                # Fully configured and activated → block re-setup
                if is_activated and is_configured:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_ALREADY_CONFIGURED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                # Pending pairing (not yet activated, has secret) → reuse existing secret
                # This prevents the secret from being overwritten on repeated calls
                if not is_activated and existing_secret:
                    pairing_key = existing_secret
                    self.app_debug_print(f"Reusing existing TOTP secret for pending pairing", True)
                else:
                    pairing_key = GeneratorService.generate_totp_secret()
                    self.app_debug_print(f"Generating new TOTP secret (post-logout re-setup)", True)
            else:
                pairing_key = GeneratorService.generate_totp_secret()
                self.app_debug_print(f"Generating new TOTP secret (first-time setup)", True)

            # ── Step 3: Generate pairing token and store in Redis ──
            # Generate a short random token for the QR code
            pairing_token = _secrets.token_urlsafe(8)  # ~11 char URL-safe token

            api_Consumer_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__flag": EApiConsumerFlag.FLUTTER_VALIDATION_AND_TOTP_MFA_APPS.value},
                _skip_rls=True,
            )
            if not api_Consumer_info:
                message = self.get_response_message(MessageCategory.COMMON, "API_CONSUMER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # Encrypt the consumer key
            encrypted_consumer_key = EncryptionService.encrypt_data(
                api_Consumer_info['consumer_key'])
            
            # Store full pairing data in Redis with 10-minute expiration
            pairing_data = _json.dumps({
                "base_url": settings.MAIN_APP_BASE_URL,
                "user_id": user_id,
                "pairing_key": pairing_key,
                "timestamp": int(_time.time()),
                "api_consumer": encrypted_consumer_key,
                "api_consumer_hash_key":api_Consumer_info.get('consumer_hash',""),
                # AES key used to decrypt sudo deeplinks on mobile
                "auth_app_pairing_secret_key": settings.AUTH_APP_PAIRING_SECRET_KEY or settings.GATEWAY_ENCRYPTION_SECRET_KEY,
            })
            self.app_debug_print(f"Pairing data: {pairing_data}", True)
            redis_key = f"pairing:token:{pairing_token}"
            await AppRedisService.set_redis_value(redis_key, pairing_data, expiry=600)

            self.app_debug_print(f"Pairing token: {pairing_token}, Redis key: {redis_key}", True)

            # ── Step 4: Build QR code ──
            # Build simple deeplink QR code content (minimal data for easy scanning)
            encoded_base_url = _url_quote(settings.MAIN_APP_BASE_URL, safe='')
            qr_deeplink = f"sycamore://auth/pair?token={pairing_token}&base_url={encoded_base_url}"

            self.app_debug_print(f"QR deeplink: {qr_deeplink}", True)

            # Generate QR code image (base64 PNG) for SenatDigit Auth app pairing
            qr_code_str = GeneratorService.otpauth_to_qrcode(qr_deeplink)

            # Build a standard otpauth URI for common TOTP apps
            # (Google Authenticator, Microsoft Authenticator, Authy, etc.)
            totp_account_name = str(username or user_details.get('email') or user_id)
            totp_label = f"{settings.TOTP_ISSUER}:{totp_account_name}"
            encoded_totp_label = _url_quote(totp_label, safe='')
            encoded_totp_issuer = _url_quote(str(settings.TOTP_ISSUER), safe='')
            common_totp_uri = (
                f"otpauth://totp/{encoded_totp_label}"
                f"?secret={pairing_key}&issuer={encoded_totp_issuer}"
            )
            common_totp_qr_code_str = GeneratorService.otpauth_to_qrcode(common_totp_uri)

            # ── Step 5: Upsert user MFA config with the (reused or new) secret ──
            if mfa:
                new_doc = {
                    "is_activated": False,
                    "sys_user_id": user_id,
                    "ref_mfa_id": mfa_id,
                    "secret": pairing_key,
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    filter_data={"ref_mfa_id": mfa_id, "sys_user_id": user_id},
                    update_data=new_doc
                )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_FETCHED_SUCCESSED",self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":message,
                    "data":{
                        # Backward-compatible keys (used by current frontend)
                        "qr_code_str": qr_code_str,
                        "pairing_info": {
                            "expires_in": 600,
                            "instructions": "Scan this QR code with SenatDigit Auth app to pair your device"
                        },
                        # New dual pairing payloads
                        "pairing_options": {
                            "sycamore_auth_app": {
                                "qr_code_str": qr_code_str,
                                "expires_in": 600,
                                "instructions": "Scan this QR code with SenatDigit Auth app to pair your device"
                            },
                            "common_totp_app": {
                                "qr_code_str": common_totp_qr_code_str,
                                "otpauth_uri": common_totp_uri,
                                "issuer": str(settings.TOTP_ISSUER),
                                "account_name": totp_account_name,
                                "instructions": (
                                    "Scan this QR code with Google Authenticator, "
                                    "Microsoft Authenticator, Authy, or any compatible TOTP app. "
                                    "Then enter the generated code to validate pairing."
                                ),
                            },
                        },
                    },
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error syc auth config: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def get_signature_config(
        self,
        request: Request,
    ):
        try:

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            user_id =  user_details.get('id', None)

            self.app_debug_print(f"\n\n user_id : {user_id}\n\n",True)

            if not user_details or not user_id:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            signature_query = {
                "filter__is_configured": True,
                "filter__sys_user_id": user_id,
                "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
            }
            cfg_signature = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_SIGNATURE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                    **signature_query
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )

            if 'user_account_hash' not in user_details:
                # TODO: UPDATE USER TO ADD user_account_hash
                user_account_hash = HashService.generate_hash(f"{user_details['id']}")
                data_update = {
                    "user_account_hash":user_account_hash
                }
                user_details['user_account_hash'] = user_account_hash
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.USERS, item_id=user_details['id'], data=data_update)  # TODO: Update user to add user_account_hash
            if 'user_account_socket_hash' not in user_details:
                # TODO: UPDATE USER TO ADD user_account_socket_hash
                user_account_socket_hash = HashService.generate_hash(user_details['id'])
                data_update = {
                    "user_account_socket_hash":user_account_socket_hash
                }
                user_details['user_account_socket_hash'] = user_account_socket_hash
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.USERS, item_id=user_details['id'], data=data_update)  # TODO: Update user to add user_account_socket_hash



            if not cfg_signature or not cfg_signature :
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_FETCHED_SUCCESSED",self.accept_language)
                token = self.token_service.create_access_token(
                    data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.SIGNATURE},
                    token_type=EJWTTokenType.SIGNATURE,
                    expires_delta=timedelta(days=2)  # Expires after 2 days
                )
                qr_code_str = f"signature://user/user_token:{token}?user_account_hash={user_details['user_account_hash']}&user_account_socket_hash={user_details['user_account_socket_hash']}"
                qr_code_str = GeneratorService.otpauth_to_qrcode(qr_code_str)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message,
                        "data":{
                            "qr_code_str":qr_code_str,
                        },
                    }
                )
            else :
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message,
                        "data":cfg_signature,
                    }
                )
        except Exception as e:
            self.app_debug_print(f"Error getting user signature: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR",self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def post_validate_otp(
        self,
        request: Request,
        payload: OtpRequest,
        mfa_type: str = Query(..., description="The type of MFA (e.g., email, phone)")
    ):
        try:

            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)


            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            self.app_debug_print(f"\n\n\n after saas_config_info \n\n\n",True)
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)

            # DECODE USER TOKEN
            user_details = await self.token_service.decode_and_get_user_from_token(
                request=request,
                expected_type=EJWTTokenType.MFA_VERIFICATION,
            )
            self.app_debug_print(f"\n\n\n after user_details : {user_details} \n\n\n",True)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)


            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_details['id'])
            self.app_debug_print(f"\n\n\n after user_device_info : {user_device_info} \n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )

            # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )

            loginHistory = await self.login_service.get_today_init_login_history(
                sys_user_id=user_details['id'],
                cfg_user_device_id=user_device_info.get("id")
            )
            self.app_debug_print(f"\n\n\n after loginHistory : {loginHistory} \n\n\n",True)
            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # check totp loginHistory
            if mfa_type == MFaFlag.SYCAMORE_2FA_APP.value:
                # payload.otp
                mfa_query = {
                    "filter__is_activated": True,
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP,
                }
                mfa = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_MFAS,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            **mfa_query
                        },
                        sort={"created_at": -1},
                        _skip_rls=True,
                    )

                mfa_id =  mfa.get('id', None)
                if not mfa or not mfa_id :
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                    raise HTTPException(status_code=404, detail=message)

                user_mfas_query = {
                    "filter__is_configured": True,
                    "filter__sys_user_id":user_details['id'],
                    "filter__ref_mfa_id":mfa_id,
                }
                self.app_debug_print(f"\n\n user_mfas_query : {user_mfas_query} \n\n",True)
                user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    accept_language=self.accept_language,
                    query=user_mfas_query,
                    _skip_rls=True,
                )
                self.app_debug_print(f"\n\n user_mfa : {user_mfa} \n\n",True)
                if not user_mfa:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                    raise HTTPException(status_code=404, detail=message)

                if not mfa or not mfa_id :
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",self.accept_language)
                    raise HTTPException(status_code=404, detail=message)

                secret = user_mfa.get('secret')
                self.app_debug_print(f"\n\n secret : {secret} \n\n",True)
                if not secret:
                    raise HTTPException(status_code=404, detail="User not found")

                # Allow a valid window of 1 time-step before and after to account for clock skew.
                self.app_debug_print(f"\n\n payload.otp : {payload.otp} \n\n",True)
                if GeneratorService.verify_totp_code(secret, payload.otp):
                    return await self._continue_with_otp_login(user_details,device_hashed_id, user_device_info, loginHistory)
                else:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOTP_CODE",self.accept_language)
                    raise HTTPException(status_code=401, detail=message)


            

            otp_code = loginHistory.get("otp")
            if not otp_code:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "LOGIN_PROCESS_NOT_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if mfa_type == MFaFlag.EMAIL.value or mfa_type == MFaFlag.PHONE_NUMBER.value:

                # CHECK OTP MACHING HTTP_422_UNPROCESSABLE_ENTITY
                if otp_code != payload.otp:
                    message = self.get_response_message(MessageCategory.COMMON, "OTP_NO_MATCHING", self.accept_language)
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

                return await self._continue_with_otp_login(user_details,device_hashed_id, user_device_info, loginHistory)
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

        except Exception as e:
            formated_error = format_exception(f"error get_otp ",e)
            self.app_debug_print(f"[post_validate_otp] Error getting OTP: {formated_error}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    def check_mfa_setup_needed(self,cfg_user_mfa):
        next_setup = cfg_user_mfa.get("mfa_configuration_next_setup_at")
        
        if next_setup is None:
            return False  # No setup date set
        
        # Ensure both are timezone-aware (UTC)
        current_time = datetime.now(timezone.utc)
        
        # If next_setup is naive, assume it's UTC
        if next_setup.tzinfo is None:
            import pytz
            next_setup = next_setup.replace(tzinfo=timezone.utc)
            # or: next_setup = pytz.UTC.localize(next_setup)
        
        return next_setup <= current_time
    
    async def _continue_with_otp_login(self, user_details: dict,device_hashed_id: str, user_device_info: dict, loginHistory: dict):
        try:
            self.app_debug_print(f"\n\n\n [_continue_with_otp_login] user_details : {user_details} \n\n\n",True)
            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(days=14)  # Expires after 2 days
            )
            refresh_token = self.token_service.create_access_token(
                data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=14)  # Expires after 2 days
            )
            self.app_debug_print(f"\n\n\n after refresh_token : {refresh_token} \n\n\n",True)
            # Initialize token expiration variables for refresh token
            token_expiry_duration = timedelta(days=14)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()

            user_mfas = await self.user_configured_mfa(sys_user_id=user_details['id'],accept_language=self.accept_language)
            generated_session_id = GeneratorService.generate_base32_secret(str(loginHistory['id']))

            # 7 days expiration
            session_actual_expiration_date = datetime.now(timezone.utc) + timedelta(days=14)

            # update many login histories to logout where current device and user
            await self.generic_service.update_many_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data={
                    "status":ELoginStatus.LOGGED_OUT.value,
                },
                filter_data={
                    "sys_user_id":user_details['id'],
                    "cfg_user_device_id":user_device_info['id'],
                    "status":ELoginStatus.LOGGED_IN.value,
                }
            )

            update_data = {
                "status":ELoginStatus.LOGGED_IN.value,
                "session_last_activity":datetime.now(timezone.utc),
                "session_id_str":generated_session_id,
                "device_id_str":device_hashed_id,
                "session_actual_expiration":session_actual_expiration_date
            }
            self.app_debug_print(f"\n\n update_data :  {update_data}\n\n")
            # UPDATE OTP ON LOGIN HISTORY
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=loginHistory['id'],
                data=update_data
            )

            DebugService.app_debug_print(f"\n\n\nuser_details [user_details] >>>>>> : {user_details}\n\n\n",True)
            user_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_user_id":user_details['id'],
                    "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
                },
                _skip_rls=True,
            )

            should_setup_totp = False
            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value,
                },
                _skip_rls=True,
            )
            if ref_totp_mfa:
                cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        "filter__sys_user_id":user_details['id'],
                        "filter__ref_mfa_id":ref_totp_mfa['id'],
                    },
                    _skip_rls=True,
                )
                if not cfg_user_mfa:
                    should_setup_totp = True
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        filter_data={"sys_user_id":user_details['id'],"ref_mfa_id":ref_totp_mfa['id']},
                        update_data={"sys_user_id":user_details['id'],"ref_mfa_id":ref_totp_mfa['id'],"is_configured":False,"is_activated":True,"mfa_configuration_next_setup_at":datetime.now()}
                    )
                else:
                    is_disabled = cfg_user_mfa.get("is_disabled", False)
                    is_configured = cfg_user_mfa.get("is_configured", False)
                    if is_disabled or is_configured:
                        # Already configured or explicitly disabled - no setup needed
                        should_setup_totp = False
                    else:
                        # Not configured and not disabled - check if reminder period has passed
                        if self.check_mfa_setup_needed(cfg_user_mfa):
                            should_setup_totp = True


            print(f"\n\n\n\ token ::: {token}")

            # Resolve role + profil so the mobile client can render
            # role-aware UI (Home grid filter, Plus tab badge,
            # greeting label) without a follow-up fetch. The Flutter
            # `AuthStateAuthenticated.roleFlag` reads `role.flag`
            # directly off the login response.
            #
            # Both lookups are best-effort: if either id is missing or
            # the row is gone, surface a `null` rather than crashing
            # the OTP flow.
            role_payload = None
            profil_payload = None
            try:
                role_id = user_details.get("rbac_role_id")
                if role_id:
                    role_row = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": str(role_id)},
                        _skip_rls=True,
                    )
                    if role_row:
                        role_payload = {
                            "id": str(role_row.get("id") or role_row.get("_id") or ""),
                            "flag": role_row.get("flag"),
                            "name": role_row.get("name"),
                        }
            except Exception as role_err:
                self.app_debug_print(
                    f"[_continue_with_otp_login] role resolve failed (non-fatal): {role_err}",
                    True,
                )
            try:
                profil_id = user_details.get("rbac_profile_id")
                if profil_id:
                    profil_row = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": str(profil_id)},
                        _skip_rls=True,
                    )
                    if profil_row:
                        profil_payload = {
                            "id": str(profil_row.get("id") or profil_row.get("_id") or ""),
                            "flag": profil_row.get("flag"),
                            "name": profil_row.get("name"),
                        }
            except Exception as profil_err:
                self.app_debug_print(
                    f"[_continue_with_otp_login] profil resolve failed (non-fatal): {profil_err}",
                    True,
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "user":{
                        "id":f"{user_details['id']}",
                        "username":f"{user_details['username']}",
                        "first_name":f"{user_details['first_name']}",
                        "last_name":f"{user_details['last_name']}",
                        "gender":f"{user_details['gender']}",
                        "phone_number":f"{user_details['phone_number']}",
                        "email_address":f"{user_details['email']}",
                        "mfas":user_mfas,
                        "user_account_socket_hash":f"{user_details['user_account_socket_hash']}",
                        "should_setup_totp":should_setup_totp,
                        "should_update_password":user_details.get('should_update_password', False),
                    },
                    "role": role_payload,
                    "profil": profil_payload,
                    "signature":user_signature,
                    "access_token":token,
                    "expires_in":token_expires_in,
                    "expires_at":token_expires_at,
                    "refresh_token":refresh_token

                }
            )
        except Exception as e:
            self.app_debug_print(f"Error continuing with OTP login: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )



    async def post_totp_validate_otp(
        self,
        request: Request,
        payload: OtpRequest,
        mfa_type: str = Query(..., description="The type of MFA (e.g., email, phone)")
    ):
        try:
            self.app_debug_print(f"\n\n payload : {payload}\n\n")
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)


            # DECODE USER TOKEN
            user_details = await self.token_service.decode_and_get_user_from_token(
                request=request,
                expected_type=EJWTTokenType.MFA_VERIFICATION,
            )

            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)


            user_device_info = getattr(request.state, "userDeviceInfo", None)

            if not user_device_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            loginHistory = await self.login_service.get_today_init_login_history(
                sys_user_id=user_details['id'],
                cfg_user_device_id=user_device_info.get("id")
            )

            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            self.app_debug_print(f"\n\n loginHistory : {loginHistory}\n\n")
            otp_code = loginHistory.get("otp")
            self.app_debug_print(f"\n\n otp_code : {otp_code}\n\n")
            if not otp_code:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "LOGIN_PROCESS_NOT_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if mfa_type == MFaFlag.EMAIL.value or mfa_type == MFaFlag.PHONE_NUMBER.value:

                # CHECK OTP MACHING HTTP_422_UNPROCESSABLE_ENTITY
                if otp_code != payload.otp:
                    message = self.get_response_message(MessageCategory.COMMON, "OTP_NO_MATCHING", self.accept_language)
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

                # Generate access token
                token = self.token_service.create_access_token(
                    data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                    token_type=EJWTTokenType.LOGIN,
                    expires_delta=timedelta(minutes=10)  # Expires after 2 days
                )
                refresh_token = self.token_service.create_access_token(
                    data={"sub":user_details['id'], "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                    token_type=EJWTTokenType.REFRESH_TOKEN,
                    expires_delta=timedelta(days=7)  # Expires after 2 days
                )
                user_mfas = await self.user_configured_mfa(sys_user_id=user_details['id'],accept_language=self.accept_language)

                update_data = {
                "status":ELoginStatus.LOGGED_IN.value,
                }
                self.app_debug_print(f"\n\n h_data :  {update_data}\n\n")
                # UPDATE OTP ON LOGIN HISTORY
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    item_id=loginHistory['id'],
                    data=update_data
                )

                user_signature = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__sys_user_id":user_details['id'],
                        "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
                    },
                    _skip_rls=True,
                )

                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,

                        "user":{
                            "id":f"{user_details['id']}",
                            "username":f"{user_details['username']}",
                            "first_name":f"{user_details['first_name']}",
                            "last_name":f"{user_details['last_name']}",
                            "gender":f"{user_details['gender']}",
                            "phone_number":f"{user_details['phone_number']}",
                            "email_address":f"{user_details['email']}",
                            "mfas":user_mfas,
                            "user_account_socket_hash":f"{user_details['user_account_socket_hash']}",
                        },
                        "signature":user_signature,
                        "access_token":token,
                        "refresh_token":refresh_token

                    }
                )
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

        except Exception as e:
            self.app_debug_print(f"Error VALIDATE TOTP OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def post_unlock_screen(
        self,
        request: Request,
        payload: TOtpRequest,
        mfa_type: str = Query(..., description="The type of MFA (e.g., email, phone)")
    ):
        try:


            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            user_device_info = await self.get_optional_device_info(request,self.accept_language)
            loginHistory = await self.get_user_login_history(request,self.accept_language)

            if not user_device_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                raise HTTPException(status_code=404, detail=message)


            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if mfa_type == MFaFlag.SYCAMORE_2FA_APP.value:

                # CHECK TOTP MACHING
                totp_code = payload.totp
                self.app_debug_print(f"\n\n totp_code : {totp_code}")
                message = self.get_response_message(MessageCategory.SUCCESS, "SCREEN_UNLOCK_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message

                    }
                )
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

        except Exception as e:
            self.app_debug_print(f"Error validating TOTP: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def post_reset_password(
        self,
        request: Request,
        payload: PasswordResetRequest,

    ):
        try:

            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            device_hashed_id = getattr(request.state, "deviceHashedId", None)


            # DECODE USER TOKEN
            user_details =  await self.token_service.decode_and_get_user_from_token(
                request=request,
                expected_type=EJWTTokenType.LOGIN,
            )

            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_device_info =  await self.get_optional_device_info(request,self.accept_language)

            if not user_device_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            loginHistory = await self.login_service.get_today_init_login_history(
                sys_user_id=user_details['id'],
                cfg_user_device_id=user_device_info.get("id")
            )

            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            password = payload.oldpassword

            # Verify password
            if not self.verify_password(password, user_details['password']):
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "OLD_PASSWORD_INCORRECT", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # CHECK PASSWORD EQUALITY
            if payload.password != payload.repeted_password:
                message = self.get_response_message(MessageCategory.LOGIN, "OLD_AND_NEW_PASSWORD_NOT_MATCH", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            new_password = self.hash_password(payload.password)
            h_data = {
                "password":f"{new_password}"
            }
            # UPDATE OTP ON LOGIN HISTORY
            update_new_password = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=user_details['id'],
                data=h_data
            )

            if update_new_password == True:
                message = self.get_response_message(MessageCategory.COMMON, "PASSWORD_UPDATE_SUCCEFULLY", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
            else :
                message = self.get_response_message(MessageCategory.COMMON, "PASSWORD_UPDATE_FAILS", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
        except Exception as e:
            self.app_debug_print(f"Error getting OTP: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


    async def logout(
        self,
        request: Request,
    ):
        try:
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            loginHistory = getattr(request.state, "loginHistory", None)
            self.app_debug_print(f"loginHistory :  {loginHistory}")

            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            h_data = {
                "status":ELoginStatus.LOGGED_OUT.value,
            }
            self.app_debug_print(f"\n\n h_data  udpate :  {h_data}\n\n")
            # UPDATE OTP ON LOGIN HISTORY
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=loginHistory['id'],
                data=h_data
            )

            # CLEAR ALL USER STATIC CACHES (application groups, applications, sub-menus)
            user_id = user_details.get('id', '')
            if user_id:
                try:
                    # Delete all static_cache keys for this user
                    deleted_static = await AppRedisService.delete_keys_by_pattern(f"static_cache:{user_id}:*")
                    # Delete app icon caches for this user
                    deleted_icons = await AppRedisService.delete_keys_by_pattern(f"apps_icon_*_{user_id}_*")
                    self.app_debug_print(
                        f"\ud83e\uddf9 LOGOUT CACHE CLEAR: Deleted {deleted_static} static cache keys "
                        f"and {deleted_icons} icon cache keys for user {user_id}"
                    )
                except Exception as cache_err:
                    self.app_debug_print(f"Warning: Failed to clear user caches on logout: {cache_err}")

            # CLEAR FCM TOKEN ON THE LOGGING-OUT DEVICE
            # Otherwise FCM push could still reach the device after the
            # user has logged out \u2014 they'd see notifications for an
            # account they're no longer in. We unset the column on the
            # specific cfg_user_device row tied to this login session.
            device_id = (loginHistory or {}).get("cfg_user_device_id")
            if device_id:
                try:
                    await self.generic_service.update_data_in_collection(
                        collection_key=CollectionKey.CFG_USER_DEVICE,
                        item_id=str(device_id),
                        data={"fcm_token": None},
                    )
                    self.app_debug_print(
                        f"\ud83d\udd07 LOGOUT FCM CLEAR: unset fcm_token on device {device_id}"
                    )
                except Exception as fcm_err:
                    self.app_debug_print(
                        f"Warning: failed to clear fcm_token on logout: {fcm_err}"
                    )

            message = self.get_response_message(MessageCategory.COMMON, "LOGOUT_FINISHED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":message
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error logout: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    async def totp_apps_logout(
        self,
        request: Request,
        body: dict = Body(...),
    ):
        try:
            self.app_debug_print(f"body totp apps:  {body}",True)
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language) 
            self.app_debug_print(f"user_details totp apps:  {user_details}",True)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            self.app_debug_print(f"api_Consumer totp apps:  {api_Consumer}",True)
            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            self.app_debug_print(f"device_hashed_id totp apps:  {device_hashed_id}",True)

            login_history_query = {
                "sys_user_id": user_details['id'],
                "status": ELoginStatus.LOGGED_IN.value,
                "device_id_str":device_hashed_id
            }

            self.app_debug_print(f"login_history_query data query > :  {login_history_query}",True)

            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )
            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            h_data = {
                "status":ELoginStatus.LOGGED_OUT.value,
            }

            self.app_debug_print(f"\n\n h_data  udpate :  {h_data}\n\n",False)
            # UPDATE OTP ON LOGIN HISTORY
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=loginHistory['id'],
                data=h_data
            )

            # CLEAR ALL USER STATIC CACHES (application groups, applications, sub-menus)
            user_id = user_details.get('id', '')
            if user_id:
                try:
                    deleted_static = await AppRedisService.delete_keys_by_pattern(f"static_cache:{user_id}:*")
                    deleted_icons = await AppRedisService.delete_keys_by_pattern(f"apps_icon_*_{user_id}_*")
                    self.app_debug_print(
                        f"\ud83e\uddf9 TOTP LOGOUT CACHE CLEAR: Deleted {deleted_static} static cache keys "
                        f"and {deleted_icons} icon cache keys for user {user_id}", True
                    )
                except Exception as cache_err:
                    self.app_debug_print(f"Warning: Failed to clear user caches on totp logout: {cache_err}", True)

            # RESET THE TOTP USER CONFIG
            await self.generic_service.update_data_with_query_in_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                native_query={
                    "sys_user_id": ObjectId(user_details['id']),
                },
                data={
                    "is_configured": False,
                    "secret": None,
                    "mfa_configuration_next_setup_at": datetime.now(timezone.utc)
                }
            )

            # RESET ALL USER TOTP ENTRIES TO AVOID STALE SECRET REUSE AFTER RE-PAIRING
            existing_totps = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_TOTP,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__sys_user_id": user_details['id'],
                    "filter__is_configured": True
                },
                _skip_rls=True,
            )
            for totp_item in (existing_totps or []):
                totp_item_id = totp_item.get('id')
                if totp_item_id:
                    await self.generic_service.update_data_in_collection(
                        collection_key=CollectionKey.CFG_USER_TOTP,
                        item_id=totp_item_id,
                        data={"is_configured": False}
                    )

            message = self.get_response_message(MessageCategory.COMMON, "LOGOUT_FINISHED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":message
                }
            )
        except Exception as e:
            
            self.app_debug_print(f"Error logout: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )


     # =========================================================================
    # GOOGLE AUTHENTICATION (LOGIN & REGISTRATION)
    # =========================================================================

    async def _auto_login_user(self, sys_user_id: str,device_hashed_id:str,ip_address:str,cfg_user_device_id:str):
        """
        Auto-login user after registration
        """
        try:
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": sys_user_id},
                _skip_rls=True,
            )
            if not user_details:
                raise HTTPException(status_code=404, detail="User not found")

            if 'user_account_socket_hash' not in user_details:
                user_account_hash = HashService.generate_hash(f"{sys_user_id}")
                user_account_socket_hash = HashService.generate_hash(sys_user_id)
                data_update = {
                    "user_account_hash":user_account_hash,
                    "user_account_socket_hash":user_account_socket_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=sys_user_id, data=data_update)

            # Link device to visitor user
            # device_result = await self.generic_service.upsert_data_to_collection(
            #     collection_key=CollectionKey.CFG_USER_DEVICES,
            #     filter_data={
            #         "sys_user_id": sys_user_id,
            #         "device_id_str": device_hashed_id,
            #     },
            #     update_data={
            #         "sys_user_id": sys_user_id,
            #         "device_id_str": device_hashed_id,
            #         "status": EUserDeviceStatus.ALLOWED.value,
            #     }
            # )
            # device_result_id = device_result if isinstance(device_result,str) else device_result['id']

            # Create minimal user config (optional)
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter__short_code": 'fr'},
                _skip_rls=True,
            )
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    data={
                        "sys_user_id": sys_user_id,
                        "allowed_device_count": 1,
                        "language_code": language['short_code'],
                        "ref_language_id": language['id'],
                    }
                )

            _loginHistory = {
                    "sys_user_id":sys_user_id,
                    "ip_address":ip_address,
                    "cfg_user_device_id":cfg_user_device_id,
                    "device_id_str":device_hashed_id,
                    "status":ELoginStatus.LOGGED_IN.value,
                    "sys_organization_id":None,
            }

            login_history_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data=_loginHistory
            )

            # Issue JWT and return
            access_token = self.token_service.create_access_token(
                data={"sub":sys_user_id, "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(days=365)  # Expires after 2 days
            )
            refresh_token = self.token_service.create_access_token(
                data={"sub":sys_user_id, "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=365 * 2)  # Expires after 2 days
            )
            # user_mfas = await self.user_configured_mfa(sys_user_id=sys_user_id,accept_language=self.accept_language)
            generated_session_id = self.generator_service.generate_base32_secret(str(login_history_id))

            # 7 days expiration
            session_actual_expiration_date = datetime.now(timezone.utc) + timedelta(days=365)

            # update many login histories to logout where current device and user
            await self.generic_service.update_many_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data={
                    "status":ELoginStatus.LOGGED_OUT.value,
                },
                filter_data={
                    "sys_user_id":sys_user_id,
                    "cfg_user_device_id":cfg_user_device_id,
                    "status":ELoginStatus.LOGGED_IN.value,
                }
            )

            update_data = {
                "status":ELoginStatus.LOGGED_IN.value,
                "session_last_activity":datetime.now(timezone.utc),
                "session_id_str":generated_session_id,
                "device_id_str":device_hashed_id,
                "session_actual_expiration":session_actual_expiration_date
            }
            self.app_debug_print(f"\n\n update_data :  {update_data}\n\n")
            # UPDATE OTP ON LOGIN HISTORY
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=login_history_id,
                data=update_data
            )

            formated_user_and_profil = await self.get_logged_in_user_and_profils(user_details,self.accept_language)
            if formated_user_and_profil['status'] == False:
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=formated_user_and_profil['message']
                )

            cfg_user_auth_setup = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_AUTH_SETUP,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": sys_user_id,"filter__cfg_user_device_id": cfg_user_device_id},
                _skip_rls=True,
            )

            is_user_biometric_set = False
            is_user_pin_set = False
            user_pin = None
            if cfg_user_auth_setup:
                is_user_biometric_set = cfg_user_auth_setup['is_user_biometric_set']
                is_user_pin_set = cfg_user_auth_setup['is_user_pin_set']
                user_pin = cfg_user_auth_setup['user_pin']
            else:
                all_user_auth_setup =  await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_USER_AUTH_SETUP,
                    output_data_type=OutputDataType.DEFAULT.value,
                    all_data=True,
                    query={"filter__sys_user_id": sys_user_id,"filter__cfg_user_device_id": cfg_user_device_id},
                    _skip_rls=True,
                )
                if all_user_auth_setup:
                    is_user_biometric_set = False
                    is_user_pin_set = all_user_auth_setup[0]['is_user_pin_set']
                    user_pin = all_user_auth_setup[0]['user_pin']

            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "success": True,
                    "message": "User logged in successfully",
                    "data": {
                        "user":formated_user_and_profil['data']['user'],
                        "user_profils":formated_user_and_profil['data']['user_profils'],
                        "access_token":access_token,
                        "refresh_token":refresh_token,
                        "auth_config":{
                            "is_user_biometric_set":is_user_biometric_set,
                            "is_user_pin_set":is_user_pin_set,
                            "user_pin":user_pin,
                            "registration_origin":formated_user_and_profil['data']['user']['registration_origin']
                        }
                    }
                }
            )

        except Exception as e:
            formated_error = format_exception("Failed to auto-login user", e)
            self.app_debug_print(formated_error, True)


    async def upload_users_profile_photo(
        self,
        request: Request,
        id: str = Form(...),
        upload_file: UploadFile = File(...),
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            self.app_debug_print(f"Received id: {id}", True)
            self.app_debug_print(f"Received file: {upload_file}", True)
            # Read the file content
            user_info = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language= self.accept_language,
                native_query={
                    "_id": ObjectId(id),
                }
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Read the entire file content first
            file_content = await upload_file.read()

            # Reset file pointer for potential reuse
            await upload_file.seek(0)

            # Use httpx AsyncClient to post the file to the target endpoint
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=20.0, read=60.0, write=60.0, pool=None)
            ) as client:
                headers = {
                    "authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}"
                }
                # math
                current_year = datetime.now().year
                currenty_month = datetime.now().month
                if currenty_month < 10:
                    currenty_month = f"0{currenty_month}"
                base_dir = f"{settings.SENAT_DIGIT_APPS_FILE_ORGANIZATION_LOGO_BASE_DIR}___users_profiles___{EGender(user_info['gender']).value}___{current_year}___{currenty_month}"
                self.app_debug_print(f"\n\n\n headers : {headers} \n\n", False)
                response = await client.post(
                    f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/files/upload?base_dir={base_dir}",
                    files={"upload_file": (upload_file.filename, file_content, upload_file.content_type)},
                    headers=headers
                )
                self.app_debug_print(f"Forwarded file upload response status: {response.status_code}", False)

            self.app_debug_print(f" UPLOADED FILE response : {isinstance(response.status_code, int)}", False)
            self.app_debug_print(f" UPLOADED FILE all response : {response.json()}", False)

            # You may want to validate the response from the target endpoint.
            if response.status_code == 200 or response.status_code == 201:
                # Assuming response.data is a dictionary or an object with attributes
                resp = response.json()
                data = resp.get('data', {})

                # Access the fields from response.data
                # Access the fields from response.data
                id = data.get('id')
                file_name = data.get('file_name')
                file_url = data.get('file_url')
                # created_at = data.get('created_at')
                file_size = data.get('file_size')
                file_type = data.get('file_type')
                file_path = data.get('file_path')
                # identifier = data.get('identifier')
                file_original_name = data.get('file_original_name')
                file_extension = data.get('file_extension')
                file_str_id_composed = data.get('file_str_id_composed')

                # PREPARE ARCH FILE DATA
                # timestamp = get_today_timestamp_int()
                # file_str_id_composed = f"{uuid.uuid4()}_{id}_{timestamp}"
                file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/view-file/{file_str_id_composed}"
                arch_file_data = {
                    "remote_arch_file_id":data.get('id'),
                    "remote_arch_file_url":file_url,
                    "file_name":file_name,
                    "file_str_id_composed":file_str_id_composed,
                    "file_url":file_url_composed,
                    "file_original_name":file_original_name,
                    "file_extension":file_extension,
                    "file_type":file_type,
                    "file_size":file_size,
                    "file_path":file_path,
                }
                # Call the asynchronous function to update the collection
                added_file_id = await self.generic_service.add_data_to_collection(collection_key=CollectionKey.ARCH_FILE, data=arch_file_data)
                self.app_debug_print(f" added_file_id: {added_file_id}", False)

                # SAVE ORG FILE
                # Prepare the update data
                update_data = {
                    "face_image_path_id": added_file_id
                }
                self.app_debug_print(f" update_data: {update_data}", False)
                # Call the asynchronous function to update the collection
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_info['id'],
                    data=update_data
                )
                self.app_debug_print(f" updated: {updated}", False)
                message = self.get_response_message(MessageCategory.SUCCESS, "DONOR_PROFILE_PHOTO_UPLOADED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            raise HTTPException(status_code=response.status_code, detail="Failed to forward the file to the target API.")

        except Exception as e:
            self.app_debug_print(f"Error during file upload: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")



    async def upload_user_registration_id_card(
        self,
        request: Request,
        id: str = Form(...),
        upload_file: UploadFile = File(...),
    ):
        """Upload an ID card photo for an INS request and attach it to the request document"""
        try:
            self.app_debug_print(f"Received INS request id: {id}", True)
            self.app_debug_print(f"Received file: {upload_file}", True)

            ins_info = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                native_query={"_id": ObjectId(id)},
            )
            if not ins_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

            file_content = await upload_file.read()
            await upload_file.seek(0)

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=20.0, read=60.0, write=60.0, pool=None)
            ) as client:
                headers = {"authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}"}
                current_year = datetime.now().year
                currenty_month = datetime.now().month
                if currenty_month < 10:
                    currenty_month = f"0{currenty_month}"
                gender = (ins_info.get("gender") or "m").lower()
                base_dir = f"{settings.SENAT_DIGIT_APPS_FILE_ORGANIZATION_LOGO_BASE_DIR}___ins_requests_id_cards___{gender}___{current_year}___{currenty_month}"
                response = await client.post(
                    f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/files/upload?base_dir={base_dir}",
                    files={"upload_file": (upload_file.filename, file_content, upload_file.content_type)},
                    headers=headers,
                )

            if response.status_code in (200, 201):
                resp = response.json()
                data = resp.get("data", {})
                file_str_id_composed = data.get("file_str_id_composed")
                file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/view-file/{file_str_id_composed}"

                arch_file_data = {
                    "remote_arch_file_id": data.get("id"),
                    "remote_arch_file_url": data.get("file_url"),
                    "file_name": data.get("file_name"),
                    "file_str_id_composed": file_str_id_composed,
                    "file_url": file_url_composed,
                    "file_original_name": data.get("file_original_name"),
                    "file_extension": data.get("file_extension"),
                    "file_type": data.get("file_type"),
                    "file_size": data.get("file_size"),
                    "file_path": data.get("file_path"),
                }
                added_file_id = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.ARCH_FILE, data=arch_file_data
                )

                update_data = {"id_card_image_path_id": added_file_id}
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=ins_info["id"],
                    data=update_data,
                )

                message = self.get_response_message(
                    MessageCategory.SUCCESS, "SUCCESSFULL_OPERATION_COMPLETED", self.accept_language
                )
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "data": {"arch_file_id": added_file_id},
                    },
                )

            raise HTTPException(status_code=response.status_code, detail="Failed to forward the file to the target API.")

        except Exception as e:
            format_error = format_exception("error : ",e)
            self.app_debug_print(f"Error during INS ID card upload: {format_error}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")



    async def upload_org_logo(
        self,
        request: Request,
        id: str = Form(...),
        upload_file: UploadFile = File(...),
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            self.app_debug_print(f"Received id: {id}", True)
            self.app_debug_print(f"Received file: {upload_file}", True)
            # Read the file content
            org_info = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                accept_language= self.accept_language,
                native_query={
                    "_id": ObjectId(id),
                }
            )
            if not org_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Read the entire file content first
            file_content = await upload_file.read()

            # Reset file pointer for potential reuse
            await upload_file.seek(0)

            # Use httpx AsyncClient to post the file to the target endpoint
            async with httpx.AsyncClient() as client:
                headers = {
                    "authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}"
                }
                # math
                self.app_debug_print(f"\n\n\n headers : {headers} \n\n", False)
                response = await client.post(
                    f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/files/upload?base_dir={settings.SENAT_DIGIT_APPS_FILE_ORGANIZATION_LOGO_BASE_DIR}",
                    files={"upload_file": (upload_file.filename, file_content, upload_file.content_type)},
                    headers=headers
                )
                self.app_debug_print(f"Forwarded file upload response status: {response.status_code}", False)

            self.app_debug_print(f" UPLOADED FILE response : {isinstance(response.status_code, int)}", False)
            self.app_debug_print(f" UPLOADED FILE all response : {response.json()}", False)

            # You may want to validate the response from the target endpoint.
            if response.status_code == 200 or response.status_code == 201:
                # Assuming response.data is a dictionary or an object with attributes
                resp = response.json()
                data = resp.get('data', {})

                # Access the fields from response.data
                # Access the fields from response.data
                id = data.get('id')
                file_name = data.get('file_name')
                file_url = data.get('file_url')
                # created_at = data.get('created_at')
                file_size = data.get('file_size')
                file_type = data.get('file_type')
                file_path = data.get('file_path')
                # identifier = data.get('identifier')
                file_original_name = data.get('file_original_name')
                file_extension = data.get('file_extension')
                file_str_id_composed = data.get('file_str_id_composed')

                # PREPARE ARCH FILE DATA
                # timestamp = get_today_timestamp_int()
                # file_str_id_composed = f"{uuid.uuid4()}_{id}_{timestamp}"
                file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/view-file/{file_str_id_composed}"
                arch_file_data = {
                    "remote_arch_file_id":data.get('id'),
                    "remote_arch_file_url":file_url,
                    "file_name":file_name,
                    "file_str_id_composed":file_str_id_composed,
                    "file_url":file_url_composed,
                    "file_original_name":file_original_name,
                    "file_extension":file_extension,
                    "file_type":file_type,
                    "file_size":file_size,
                    "file_path":file_path,
                }
                # Call the asynchronous function to update the collection
                added_file_id = await self.generic_service.add_data_to_collection(collection_key=CollectionKey.ARCH_FILE, data=arch_file_data)
                self.app_debug_print(f" added_file_id: {added_file_id}", False)

                # SAVE ORG FILE
                # Prepare the update data
                update_data = {
                    "logo_file_id": added_file_id  # Ensure `id` is defined and has the correct value
                }
                self.app_debug_print(f" update_data: {update_data}", False)
                # Call the asynchronous function to update the collection
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    item_id=org_info['id'],
                    data=update_data
                )
                self.app_debug_print(f" updated: {updated}", False)
                message = self.get_response_message(MessageCategory.SUCCESS, "FILE_UPLOADED_SUCCESSFULLY", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            raise HTTPException(status_code=response.status_code, detail="Failed to forward the file to the target API.")

        except Exception as e:
            self.app_debug_print(f"Error during file upload: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")



    async def get_auth_questions(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
    ):
        try:
            auth_question_categories = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_AUTH_QUESTION_CATEGORY,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__is_activated": True,
                },
                sort={"created_at": -1},
                _skip_rls=True,
            )
            formated_categories = []
            for category in auth_question_categories:
                formated_questions = []
                questions = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.REF_AUTH_QUESTION,
                    output_data_type=OutputDataType.DEFAULT.value,
                    all_data=True,
                    query={"filter__ref_auth_question_category_id": category['id']},
                    sort={"created_at": -1},
                    _skip_rls=True,
                )
                for question in questions:
                    formated_questions.append({
                        "id": question['id'],
                        "name": question['name'],
                    })
                formated = {
                    "id": category['id'],
                    "name": category['name'],
                }
                formated['questions'] = formated_questions
                formated_categories.append(formated)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": formated_categories,
                }
            )
        except Exception as e:
            format_error = format_exception("error : ",e)
            self.app_debug_print(f"Error getting auth questions: {format_error}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")


    async def get_logged_in_user_and_profils(self,user_details:dict,accept_language:str = 'fr') -> dict:
        user_profils = []
        try:
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                _skip_rls=True,
            )

            if not user_profil:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", accept_language)
                return {
                    "status":False,
                    "message":message
                }

            if user_profil['rbac_profile_id']:
                rbac_profile_id = user_profil['rbac_profile_id']
                user_profil = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": str(rbac_profile_id)},
                    _skip_rls=True,
                )
                if not user_profil:
                    message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", accept_language)
                    return {
                        "status":False,
                        "message":message
                    }

            user_entity = {}
            # get from organization
            self.app_debug_print(f"\n\n\n user_details : {user_details} \n\n\n",False)
            if user_details.get('sys_organization_id') or user_details.get('ref_entity_id'):
                ref_entity_id = user_details.get('ref_entity_id') or user_details.get('sys_organization_id')
                DebugService.app_debug_print(f"\n\n\n ref_entity_id : {ref_entity_id} \n\n\n",False)
                user_org = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": str(user_details['sys_organization_id'])},
                    _skip_rls=True,
                )
                DebugService.app_debug_print(f"\n\n\n user_org : {user_org} \n\n\n",False)
                if user_org:
                    user_entity_info = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": str(user_org['ref_entity_id'])},
                        _skip_rls=True,
                    )
                    DebugService.app_debug_print(f"\n\n\n user_entity_info : {user_entity_info} \n\n\n",False)
                    user_entity = {
                        "id":user_entity_info['id'],
                        "name":user_entity_info['name']
                    }
                elif ref_entity_id:
                    user_entity_info = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": ref_entity_id},
                        _skip_rls=True,
                    )
                    DebugService.app_debug_print(f"\n\n\n user_entity_info : {user_entity_info} \n\n\n",False)
                    user_entity = {
                        "id":user_entity_info['id'],
                        "name":user_entity_info['name']
                    }
            else :
                user_entity_info = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": user_details['ref_entity_id']},
                    _skip_rls=True,
                )
                user_entity = {
                    "id":user_entity_info['id'],
                    "name":user_entity_info['name']
                }

            account_type = "customer"  # Default fallback
            user_address = user_details.get('address', '')

            # Collect base profile from sys_profil
            account_type = "customer"
             

            return {
                "status":True,
                "data":{
                    "user":{
                        "id":f"{user_details['id']}",
                        "username":f"{user_details['username']}",
                        "first_name":f"{user_details['first_name']}",
                        "last_name":f"{user_details['last_name']}",
                        "gender":f"{user_details['gender']}",
                        "phone_number":f"{user_details['phone_number']}",
                        "email_address":f"{user_details['email']}",
                        "account_status":user_details['account_status'],
                        "address":f"{user_address}",
                        "day_of_birth":f"{user_details.get('birth_day', '')}",
                        "sys_organization_id":f"{user_details.get('sys_organization_id')}",
                        "user_account_socket_hash":f"{user_details['user_account_socket_hash']}",
                        "account_type":account_type,
                        "user_entity":user_entity,
                        "registration_origin":f"{user_details.get('registration_origin')}",
                    },
                    "user_profils":user_profils,
                }
            }

        except Exception as e:
            format_error = format_exception("error : ",e)
            DebugService.app_debug_print(f"\n\n\n Error fetching user profile: {format_error} \n\n\n", True)
            message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", accept_language)
            return {
                "status":False,
                "message":message
            }


    async def complete_device_pairing(
        self,
        request: Request,
        payload: DevicePairingRequest,
    ):
        """
        Complete device pairing from the Flutter mobile app.
        Validates the pairing_key against CFG_USER_MFA, creates device record,
        generates auth tokens, and returns response matching OTP validation format.
        """
        try:
            user_id = payload.user_id
            pairing_key = payload.pairing_key

            # Get device and IP info from middleware
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            ip_address = await self.get_optional_api_address(request, self.accept_language)
            device_info = await AuthenticatedService.get_optional_device_info(request)
            self.app_debug_print(f"\n\n[DEVICE PAIRING] user_id={user_id}, device={device_hashed_id}, ip={ip_address}\n\n", True)

            # Validate user exists
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": user_id},
                _skip_rls=True,
            )
            if not user_details:
                raise HTTPException(status_code=404, detail="User not found")

            # Validate pairing key against CFG_USER_MFA
            user_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__sys_user_id": user_id,
                    "filter__secret": pairing_key,
                    "filter__is_activated": False,
                },
                _skip_rls=True,
            )
            if not user_mfa:
                raise HTTPException(status_code=400, detail="Invalid or expired pairing key")

            # Mark pairing as activated
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.CFG_USER_MFA,
                item_id=user_mfa['id'],
                data={"is_activated": True}
            )

            # Create/update device record
            device_result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                filter_data={
                    "sys_user_id": user_id,
                    "device_id_str": device_hashed_id,
                },
                update_data={
                    "sys_user_id": user_id,
                    "device_id_str": device_hashed_id,
                    "device_info":device_info,
                    "status": EUserDeviceStatus.ALLOWED.value,
                }
            )
            device_result_id = device_result if isinstance(device_result, str) else device_result['id']

            # Create login history
            _loginHistory = {
                "sys_user_id": user_id,
                "ip_address": ip_address,
                "cfg_user_device_id": device_result_id,
                "device_id_str": device_hashed_id,
                "status": ELoginStatus.LOGGED_IN.value,
                "sys_organization_id": None,
            }
            login_history_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data=_loginHistory
            )

            # Generate tokens
            token = self.token_service.create_access_token(
                data={"sub": user_id, "device_id_str": device_hashed_id, "type": EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(days=4)
            )
            refresh_token = self.token_service.create_access_token(
                data={"sub": user_id, "device_id_str": device_hashed_id, "type": EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=7)
            )

            # Update login history with session info
            generated_session_id = GeneratorService.generate_base32_secret(str(login_history_id))
            session_actual_expiration_date = datetime.now(timezone.utc) + timedelta(days=7)

            # Logout other sessions for this device/user
            await self.generic_service.update_many_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data={"status": ELoginStatus.LOGGED_OUT.value},
                filter_data={
                    "sys_user_id": user_id,
                    "cfg_user_device_id": device_result_id,
                    "status": ELoginStatus.LOGGED_IN.value,
                }
            )

            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=login_history_id,
                data={
                    "status": ELoginStatus.LOGGED_IN.value,
                    "session_last_activity": datetime.now(timezone.utc),
                    "session_id_str": generated_session_id,
                    "device_id_str": device_hashed_id,
                    "session_actual_expiration": session_actual_expiration_date,
                }
            )

            user_mfas = await self.user_configured_mfa(sys_user_id=user_id, accept_language=self.accept_language)

            # Upsert TOTP configuration
            secret = user_mfa.get('secret')
            mfa_id = user_mfa.get('ref_mfa_id')

            totp_upsert_doc = {
                "is_configured": True,
                "sys_user_id": user_id,
                "cfg_user_device_id": device_result_id,
                "secret": secret,
                "username": user_details.get('username'),
                "issuer": settings.TOTP_ISSUER,
            }
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_TOTP,
                filter_data={"sys_user_id": user_id, "cfg_user_device_id": device_result_id},
                update_data=totp_upsert_doc
            )

            # Also upsert CFG_USER_MFA
            if mfa_id:
                mfa_upsert_doc = {
                    "is_activated": True,
                    "is_configured": True,
                    "sys_user_id": user_id,
                    "ref_mfa_id": mfa_id,
                    "secret": secret
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    filter_data={"ref_mfa_id": mfa_upsert_doc['ref_mfa_id'], "sys_user_id": mfa_upsert_doc['sys_user_id']},
                    update_data=mfa_upsert_doc
                )

            # Fetch user signature (matching post_validate_otp pattern)
            user_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_user_id":user_details['id'],
                    "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
                },
                _skip_rls=True,
            )

            # Fetch user auth setup to check TOTP app PIN status
            cfg_user_auth_setup = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_AUTH_SETUP,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": user_id, "filter__cfg_user_device_id": device_result_id},
                _skip_rls=True,
            )
            is_totp_app_pin_set = False
            if cfg_user_auth_setup:
                is_totp_app_pin_set = cfg_user_auth_setup.get('is_totp_app_pin_set', False) or False

            logged_in_user_data = {
                "id": f"{user_details['id']}",
                "username": f"{user_details['username']}",
                "first_name": f"{user_details['first_name']}",
                "last_name": f"{user_details['last_name']}",
                "gender": f"{user_details['gender']}",
                "phone_number": f"{user_details['phone_number']}",
                "email_address": f"{user_details['email']}",
                "mfas": user_mfas,
                "user_account_socket_hash": f"{user_details.get('user_account_socket_hash', '')}",
                "is_totp_app_pin_set": is_totp_app_pin_set,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "user":logged_in_user_data,
                    "signature": user_signature,
                    "access_token": token,
                    "refresh_token": refresh_token,
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error completing device pairing: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def set_totp_app_pin(
        self,
        request: Request,
        payload,
    ):
        """
        Set the TOTP app PIN for the authenticated user.
        Upserts the PIN into CFG_USER_AUTH_SETUP.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = user_details.get('id')
            pin = payload.pin

            # Get device info
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": user_id, "filter__device_id_str": device_hashed_id},
                _skip_rls=True,
            )
            device_id = device.get('id') if device else None

            if not device_id:
                raise HTTPException(status_code=400, detail="Device not found")

            # Upsert CFG_USER_AUTH_SETUP with the TOTP app PIN
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_AUTH_SETUP,
                filter_data={"sys_user_id": user_id, "cfg_user_device_id": device_id},
                update_data={
                    "sys_user_id": user_id,
                    "cfg_user_device_id": device_id,
                    "totp_app_pin": pin,
                    "is_totp_app_pin_set": True,
                }
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "TOTP app PIN set successfully",
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error setting TOTP app PIN: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def get_pairing_data(
        self,
        request: Request,
        payload,
    ):
        """
        Retrieve pairing data from Redis using a short-lived token.
        Token is deleted after retrieval (one-time use).
        """
        try:
            token = payload.token
            redis_key = f"pairing:token:{token}"

            # Retrieve pairing data from Redis
            pairing_data_str = await AppRedisService.get_str_redis_value(redis_key)

            if not pairing_data_str:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail="Invalid or expired pairing token")

            pairing_data = json.loads(pairing_data_str)

            # Delete token after use (one-time use)
            await AppRedisService.remove_redis_value(redis_key)

            self.app_debug_print(f"Pairing data retrieved for token: {token}", True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": 200,
                    "message": "Pairing data retrieved successfully",
                    "data": pairing_data
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error retrieving pairing data: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def get_mobile_pairing_secret(self, request: Request):
        """
        Return the AES secret used to decrypt mobile sudo deeplinks.
        Requires authenticated user.
        """
        try:
            await self.get_user_info(request, self.accept_language)
            pairing_secret = settings.AUTH_APP_PAIRING_SECRET_KEY or settings.GATEWAY_ENCRYPTION_SECRET_KEY
            if not pairing_secret:
                raise HTTPException(status_code=500, detail="Pairing secret key not configured")

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Pairing secret retrieved successfully",
                    "data": {
                        "auth_app_pairing_secret_key": pairing_secret
                    }
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error retrieving mobile pairing secret: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def get_user_totps(self, request: Request):
        """
        Fetch all TOTP configurations for the authenticated user.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = user_details.get('id')

            totps = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_TOTP,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": user_id, "filter__is_configured": True},
                _skip_rls=True,
            )

            # fetch_data_from_collection defaults to created_at DESC.
            # Keep only the newest item per logical account identity to prevent
            # stale secrets from overriding fresh ones on mobile.
            deduped_totps = []
            seen_identity_keys = set()
            for totp in (totps or []):
                username_key = str(totp.get('username') or '').strip().lower()
                issuer_key = str(totp.get('issuer') or '').strip().lower()
                fallback_device = str(totp.get('cfg_user_device_id') or '').strip()
                identity_key = (
                    f"{issuer_key}|{username_key}"
                    if (issuer_key or username_key)
                    else f"device:{fallback_device}"
                )

                if identity_key in seen_identity_keys:
                    continue
                seen_identity_keys.add(identity_key)
                deduped_totps.append(totp)

            totp_list = []
            for totp in deduped_totps:
                totp_list.append({
                    "id": str(totp.get('id', '')),
                    "username": totp.get('username'),
                    "secret": totp.get('secret'),
                    "issuer": totp.get('issuer'),
                    "is_configured": totp.get('is_configured'),
                    "cfg_user_device_id": str(totp.get('cfg_user_device_id', '')) if totp.get('cfg_user_device_id') else None,
                })

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": totp_list
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error fetching user TOTPs: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def add_scanned_totp(self, request: Request, payload):
        """
        Add a new TOTP from scanned QR code.
        Accepts a TOTP URI (otpauth://totp/...) and stores it in CFG_USER_TOTP.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = user_details.get('id')

            # Get device info
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": user_id, "filter__device_id_str": device_hashed_id},
                _skip_rls=True,
            )
            device_id = device.get('id') if device else None

            # Parse TOTP URI: otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(payload.totp_uri)

            if parsed.scheme != 'otpauth' or parsed.netloc != 'totp':
                raise HTTPException(status_code=400, detail="Invalid TOTP URI format")

            # Extract username from path
            path_parts = parsed.path.lstrip('/').split(':')
            issuer_from_path = path_parts[0] if len(path_parts) > 1 else None
            username = path_parts[-1] if len(path_parts) > 1 else path_parts[0]

            # Extract secret and issuer from query params
            query_params = parse_qs(parsed.query)
            secret = query_params.get('secret', [None])[0]
            issuer = query_params.get('issuer', [issuer_from_path])[0]

            if not secret:
                raise HTTPException(status_code=400, detail="No secret found in TOTP URI")

            # Upsert TOTP
            totp_doc = {
                "sys_user_id": user_id,
                "cfg_user_device_id": device_id,
                "username": username,
                "secret": secret,
                "issuer": issuer or settings.TOTP_ISSUER,
                "is_configured": True,
            }

            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_TOTP,
                filter_data={"sys_user_id": user_id, "secret": secret},
                update_data=totp_doc
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "TOTP added successfully",
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error adding TOTP: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def skip_totp_setup(self, request: Request, payload):
        """
        Skip TOTP setup for a period chosen by the user.
        Updates mfa_configuration_next_setup_at to a future date.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = user_details['id']

            duration_map = {
                "1_day": timedelta(days=1),
                "3_days": timedelta(days=3),
                "7_days": timedelta(days=7),
                "14_days": timedelta(days=14),
                "30_days": timedelta(days=30),
            }

            skip_delta = duration_map.get(payload.skip_duration, timedelta(days=7))
            next_setup_at = datetime.now(timezone.utc) + skip_delta

            # Find the SYCAMORE_2FA_APP MFA reference
            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__flag": MFaFlag.SYCAMORE_2FA_APP.value},
                _skip_rls=True,
            )

            if ref_totp_mfa:
                # Upsert the cfg_user_mfa record with the new next setup date
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    filter_data={
                        "sys_user_id": user_id,
                        "ref_mfa_id": ref_totp_mfa['id'],
                    },
                    update_data={
                        "sys_user_id": user_id,
                        "ref_mfa_id": ref_totp_mfa['id'],
                        "is_configured": False,
                        "mfa_configuration_next_setup_at": next_setup_at,
                    }
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "TOTP setup skipped successfully",
                    "next_setup_at": next_setup_at.isoformat(),
                    "skip_duration": payload.skip_duration,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error skipping TOTP setup: {e}", True)
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            raise HTTPException(status_code=500, detail=str(e))


    async def force_update_password(self, request: Request, payload):
        """
        Force update password during post-login setup flow.
        Sets should_update_password to False after successful update.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = user_details['id']

            if payload.new_password != payload.confirm_password:
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "Passwords do not match",
                    }
                )

            # Validate password strength
            password_validation = self.validate_password_strength(payload.new_password)
            if not password_validation['is_valid']:
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": password_validation.get('message', 'Password does not meet requirements'),
                    }
                )

            # Hash new password
            hashed_password = HashService.hash_password(payload.new_password)

            # Update user password and set should_update_password to False
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=user_id,
                data={
                    "password": hashed_password,
                    "should_update_password": False,
                }
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Password updated successfully",
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error force updating password: {e}", True)
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            raise HTTPException(status_code=500, detail=str(e))
        





    async def login_visitor_user(self, request) -> Dict[str, Any]:
        """Visitor login check: if current device is already linked to a user, return a login token.
        Otherwise, indicate that entity selection is required.
        """
        try:
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 

            # Compute or extract device hashed id (middleware/helper)
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            ip_address = await self.get_optional_api_address(request, self.accept_language)
            if not ip_address:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            # Find device record
            user_devices = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={"filter__device_id_str": device_hashed_id},
                _skip_rls=True,
            ) 
            self.app_debug_print(f"\n\n\n ip_address : {ip_address}",True)
            if len(user_devices) > 0:
                for device in user_devices:
                    if device['status'] == EUserDeviceStatus.LOCKED.value or device['status'] == EUserDeviceStatus.REVOQUED.value:
                        message = self.get_response_message(MessageCategory.COMMON, "DEVICE_BLOCKED", self.accept_language)
                        return CustomJSONResponse(
                            status_code=status.HTTP_200_OK,
                            content={
                                "status_code": status.HTTP_200_OK,
                                "success": False,
                                "needs_entity": False,
                                "message": message
                            }
                        )
                    sys_user_id = str(device['sys_user_id'])
                    self.app_debug_print(f"\n\n\n sys_user_id : {sys_user_id}",True)
                    user_info = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": sys_user_id},
                        _skip_rls=True,
                    )
                    if user_info:
                        user_role = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_ROLE,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___id": user_info['rbac_role_id']},
                            _skip_rls=True,
                        )
                        if user_role:
                            if user_role.get('flag') == ESysProfilSuperUserRoleFlag.TRANS_VISITOR_ROLE.value:
                                self.app_debug_print(f"\n\n\n user_role.get('flag') : {user_role.get('flag')}",True)
                                return await self._complete_visitor_login(
                                    cfg_user_device_id=str(device['id']),
                                    sys_user_id=str(sys_user_id),
                                    ip_address=str(ip_address),
                                    device_hashed_id=str(device_hashed_id),
                                    request=request
                                )
                # self.app_debug_print(f"\n\n\n user_info : {user_info}",True)
                self.app_debug_print(f"\n\n\n user_role.get('flag') : {user_role.get('flag')}",True)
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_LINKED_TO_NON_VISITOR_ACCOUNT", self.accept_language,email=support_email)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "success": False,
                        "needs_entity": False,
                        "data":{
                            "needs_entity": False,
                        },
                        "message": message
                    }
                )
                # if user_info:
                #     user_role = await self.generic_service.fetch_one_from_collection(
                #         collection_key=CollectionKey.RBAC_ROLE,
                #         output_data_type=OutputDataType.DEFAULT.value,
                #         query={"filter___id": user_info['rbac_role_id']}
                #     )
                #     self.app_debug_print(f"\n\n\n user_role : {user_role}",True)
                #     if user_role:
                #         if user_role.get('flag') == ESysProfilSuperUserRoleFlag.SENAT_DIGIT_VISITOR_ROLE.value:
                #             self.app_debug_print(f"\n\n\n user_role.get('flag') : {user_role.get('flag')}",True)
                #             return await self._complete_visitor_login(
                #                 cfg_user_device_id=str(user_device['id']),
                #                 sys_user_id=str(sys_user_id),
                #                 ip_address=str(ip_address),
                #                 device_hashed_id=str(device_hashed_id)
                #             )
                #         else:
                #             self.app_debug_print(f"\n\n\n user_role.get('flag') : {user_role.get('flag')}",True)
                #             message = self.get_response_message(MessageCategory.COMMON, "DEVICE_LINKED_TO_NON_VISITOR_ACCOUNT", self.accept_language)
                #             return CustomJSONResponse(
                #                 status_code=status.HTTP_200_OK,
                #                 content={
                #                     "status_code": status.HTTP_200_OK,
                #                     "success": False,
                #                     "needs_entity": False,
                #                     "message": message
                #                 }
                #             )

            # Otherwise indicate we need the user's entity/location
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": False,
                    "needs_entity": True,
                    "message": "Device not linked. Provide location_id to create visitor."
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            formated_error = format_exception("login_visitor_user", e)
            self.app_debug_print(f"Error in login_visitor_user: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def create_visitor_user(self, request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a visitor account linked to the current device and return a login token.
        Required payload: { location_id: <entity id> }
        """
        try:

            decoded_token = await self.get_decoded_token(request,EJWTTokenType.REGISTRATION_PROCESS,self.accept_language)
            if not decoded_token:
                message = self.get_response_message(MessageCategory.LOGIN, "TOKEN_INVALID", self.accept_language)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
            
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
            device_info = await AuthenticatedService.get_optional_device_info(request)
            ip_address = await self.get_optional_api_address(request, self.accept_language)
            if not ip_address:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            location_id = (data.get('location_id') or '').strip()
            if not location_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing location_id")

            # If device already linked, reuse 
            user_devices = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={"filter__device_id_str": device_hashed_id},
                _skip_rls=True,
            ) 
            self.app_debug_print(f"\n\n\n ip_address : {ip_address}",True)
            if len(user_devices) > 0:
                for device in user_devices:
                    if device['status'] == EUserDeviceStatus.LOCKED.value or device['status'] == EUserDeviceStatus.REVOQUED.value:
                        message = self.get_response_message(MessageCategory.COMMON, "DEVICE_BLOCKED", self.accept_language)
                        return CustomJSONResponse(
                            status_code=status.HTTP_200_OK,
                            content={
                                "status_code": status.HTTP_200_OK,
                                "success": False,
                                "needs_entity": False,
                                "message": message
                            }
                        )
                    sys_user_id = str(device['sys_user_id'])
                    self.app_debug_print(f"\n\n\n sys_user_id : {sys_user_id}",True)
                    user_info = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": sys_user_id},
                        _skip_rls=True,
                    )
                    self.app_debug_print(f"\n\n\n user_info : {user_info}",True)
                    if user_info:
                        user_role = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_ROLE,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___id": user_info['rbac_role_id']},
                            _skip_rls=True,
                        )
                        self.app_debug_print(f"\n\n\n user_role : {user_role}",True)
                        if user_role:
                            if user_role.get('flag') == ESysProfilSuperUserRoleFlag.TRANS_VISITOR_ROLE.value:
                                self.app_debug_print(f"\n\n\n user_role.get('flag') : {user_role.get('flag')}",True)
                                return await self._complete_visitor_login(
                                    cfg_user_device_id=str(device['id']),
                                    sys_user_id=str(sys_user_id),
                                    ip_address=str(ip_address),
                                    device_hashed_id=str(device_hashed_id),
                                    request=request
                                )

            # Resolve customer-like (visitor) profile and role
            customer_profile = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__flag": ESysProfileFlag.TRANS_VISITOR.value},
                _skip_rls=True,
            )

            customer_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__flag": ESysProfilSuperUserRoleFlag.TRANS_VISITOR_ROLE.value},
                _skip_rls=True,
            )
            if not customer_profile or not customer_role:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing system profile/role")

            # Create a unique visitor username based on device id suffix
            suffix = device_hashed_id[-8:] if len(device_hashed_id) >= 8 else device_hashed_id
            base_username = f"visitor-{suffix}".lower()
            username = base_username
            # Ensure uniqueness if needed
            attempt = 0
            while True:
                existing = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__username": username},
                    _skip_rls=True,
                )
                if not existing:
                    break
                attempt += 1
                username = f"{base_username}-{attempt}"

            # Generate fake visitor data
            first_name = self._generate_fake_first_name()
            last_name = self._generate_fake_last_name()
            fake_email = self._generate_fake_email(first_name, last_name, suffix)
            fake_phone = self._generate_fake_phone_number()

            # Generate strong internal password
            rand_pwd = ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#%_") for _ in range(24))

            user_payload = {
                "username": username,
                "email": fake_email,
                "phone_number": fake_phone,
                "first_name": first_name,
                "last_name": last_name,
                "phone_numbers": [{
                    "phone_number": fake_phone
                }],
                "emails": [{
                    "email": fake_email
                }],
                "password": PasswordService.hash_password(rand_pwd),
                "gender": random.choice(["m", "f"]),  # Random gender
                "account_status": AccountStatusFlag.ACTIVE.value,
                "rbac_profile_id": customer_profile["id"],
                "rbac_role_id": customer_role["id"],
                "login_fail_attempt_count": 0,
                "is_email_verified": False,
                "email_verification_code": None,
                "email_verification_expires_at": None,
                "registration_origin": ERegistrationOrigin.PHONE_NUMBER_REGISTRATION.value,
                "ref_entity_id": location_id,
            }

            sys_user_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_payload)

            # SAVE USER CURRENT ENTITY
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_CURRENT_ENTITY,
                filter_data={
                    "targeted_id": sys_user_id,
                    "ref_entity_id": location_id,
                },
                update_data={
                    "targeted_id": sys_user_id,
                    "ref_entity_id": location_id,
                }
            )

            user_account_hash = HashService.generate_hash(f"{sys_user_id}")
            user_account_socket_hash = HashService.generate_hash(sys_user_id)
            data_update = {
                "user_account_hash":user_account_hash,
                "user_account_socket_hash":user_account_socket_hash
            }
            await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=sys_user_id, data=data_update)

            # Link device to visitor user //existing_device_id
            device_result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                filter_data={
                    "sys_user_id": sys_user_id,
                    "device_id_str": device_hashed_id,
                },
                update_data={
                    "sys_user_id": sys_user_id,
                    "device_id_str": device_hashed_id,
                    "device_info":device_info,
                    "status": EUserDeviceStatus.ALLOWED.value,
                }
            )
            device_result_id = device_result if isinstance(device_result,str) else device_result['id']

            # Create minimal user config (optional)
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter__short_code": 'fr'},
                _skip_rls=True,
            )
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    data={
                        "sys_user_id": sys_user_id,
                        "allowed_device_count": 1,
                        "language_code": language['short_code'],
                        "ref_language_id": language['id'],
                    }
                )

            return await self._complete_visitor_login(
                cfg_user_device_id=str(device_result_id),
                sys_user_id=str(sys_user_id),
                ip_address=str(ip_address),
                device_hashed_id=str(device_hashed_id),
                request=request
            )
        #
        except HTTPException:
            raise
        except Exception as e:
            formated_error = format_exception("create_visitor_user", e)
            self.app_debug_print(f"Error in create_visitor_user: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))



    async def _complete_visitor_login(self,cfg_user_device_id:str,sys_user_id:str,ip_address:str,device_hashed_id:str,request:Optional[Request]):
        try:
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": sys_user_id}
,
                _skip_rls=True,
            )
            device_info = None
            if request:
                device_info = await AuthenticatedService.get_optional_device_info(request)
            if not user_info:
                raise HTTPException(status_code=404, detail="User not found")
        
            if 'user_account_hash' not in user_info:
                user_account_hash = HashService.generate_hash(f"{sys_user_id}")
                data_update = {
                    "user_account_hash":user_account_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=sys_user_id, data=data_update)

            if 'user_account_socket_hash' not in user_info:
                user_account_socket_hash = HashService.generate_hash(sys_user_id)
                data_update = {
                    "user_account_socket_hash":user_account_socket_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=sys_user_id, data=data_update)

            # Link device to visitor user
            device_result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                filter_data={
                    "sys_user_id": sys_user_id,
                    "device_id_str": device_hashed_id,
                },
                update_data={
                    "sys_user_id": sys_user_id,
                    "device_id_str": device_hashed_id,
                    "device_info":device_info,
                    "status": EUserDeviceStatus.ALLOWED.value,
                }
            )
            device_result_id = device_result if isinstance(device_result,str) else device_result['id']

            cfg_user_config = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": sys_user_id,},
                _skip_rls=True,
            )
            if not cfg_user_config:
                # Create minimal user config (optional)
                language = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_LANGUAGE.value,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter__short_code": 'fr'},
                    _skip_rls=True,
                )
                if language:
                    await self.generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_CONFIG,
                        data={
                            "sys_user_id": sys_user_id,
                            "allowed_device_count": 1,
                            "language_code": language['short_code'],
                            "ref_language_id": language['id'],
                        }
                    )

            _loginHistory = {
                    "sys_user_id":sys_user_id,
                    "ip_address":ip_address,
                    "cfg_user_device_id":cfg_user_device_id,
                    "status":ELoginStatus.LOGGED_IN.value,
                    "sys_organization_id":None,
            }

            login_history_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data=_loginHistory
            )

            # Issue JWT and return
            access_token = self.token_service.create_access_token(
                data={"sub":sys_user_id, "device_id_str":device_hashed_id, "type":EJWTTokenType.LOGIN},
                token_type=EJWTTokenType.LOGIN,
                expires_delta=timedelta(days=365)  # Expires after 2 days
            )
            refresh_token = self.token_service.create_access_token(
                data={"sub":sys_user_id, "device_id_str":device_hashed_id, "type":EJWTTokenType.REFRESH_TOKEN},
                token_type=EJWTTokenType.REFRESH_TOKEN,
                expires_delta=timedelta(days=365 * 2)  # Expires after 2 days
            )
            user_mfas = await self.user_configured_mfa(sys_user_id=sys_user_id,accept_language=self.accept_language)
            generated_session_id = self.generator_service.generate_base32_secret(str(login_history_id))

            # 7 days expiration
            session_actual_expiration_date = datetime.now(timezone.utc) + timedelta(days=365)

            # update many login histories to logout where current device and user
            await self.generic_service.update_many_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                data={
                    "status":ELoginStatus.LOGGED_OUT.value,
                },
                filter_data={
                    "sys_user_id":sys_user_id,
                    "cfg_user_device_id":device_result_id,
                    "status":ELoginStatus.LOGGED_IN.value,
                }
            )

            update_data = {
                "status":ELoginStatus.LOGGED_IN.value,
                "session_last_activity":datetime.now(timezone.utc),
                "session_id_str":generated_session_id,
                "session_actual_expiration":session_actual_expiration_date
            }
            self.app_debug_print(f"\n\n update_data :  {update_data}\n\n")
            # UPDATE OTP ON LOGIN HISTORY
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=login_history_id,
                data=update_data
            )

            formated_user_and_profil = await self.get_logged_in_user_and_profils(user_info,self.accept_language)
            if formated_user_and_profil['status'] == False:
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=formated_user_and_profil['message']
                )

            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "success": True,
                    "message": "Visitor account created and logged in successfully",
                    "data": {
                        "user":formated_user_and_profil['data']['user'],
                        "user_profils":formated_user_and_profil['data']['user_profils'],
                        "access_token":access_token,
                        "refresh_token":refresh_token
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            formated_error = format_exception("_complete_visitor_login", e)
            self.app_debug_print(formated_error, True)
            raise HTTPException(status_code=500, detail=str(e))


    async def visitor_send_phone_otp(self, request: Request, background_tasks: BackgroundTasks, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send OTP to visitor's phone number for verification.
        Required payload: { phone_number: "+243812345678" }
        """
        from app.modules.core.services.sms.sms_service import SmsService
        import random
        
        try:
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            phone_number = (data.get('phone_number') or '').strip()
            if not phone_number or len(phone_number) < 10:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

            # Find visitor user linked to this device
            user_device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__device_id_str": device_hashed_id},
                _skip_rls=True,
            )
            
            if not user_device or not user_device.get('sys_user_id'):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor account not found. Please register first.")

            sys_user_id = user_device['sys_user_id']

            # Generate 6-digit OTP
            otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

            # Store OTP in user record or a dedicated collection
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=sys_user_id,
                data={
                    "phone_otp_code": otp_code,
                    "phone_otp_expires_at": otp_expiry,
                    "phone_otp_target": phone_number,
                }
            )

            # Send SMS in background
            # Format for SMS Retriever API (auto-read OTP):
            # <#> message with OTP APP_SIGNATURE_HASH
            # The app signature should be obtained from the Flutter app using SmsAutoFill().getAppSignature
            sms_service = SmsService(self.accept_language)
            app_signature = data.get('app_signature', '')
            if app_signature:
                # SMS Retriever API format
                sms_message = f"<#> Votre code E-Blood Bank: {otp_code}\n{app_signature}"
            else:
                sms_message = f"Votre code de vérification E-Blood Bank est: {otp_code}. Ce code expire dans 10 minutes."
            
            self.app_debug_print(f"SMS message: {sms_message}", True)
            # background_tasks.add_task(sms_service.send_sms_httpx_async, phone_number, sms_message)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "OTP sent successfully",
                    "data": {
                        "phone_number": phone_number,
                        "otp_expiry_minutes": 10
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            formated_error = format_exception("visitor_send_phone_otp", e)
            self.app_debug_print(f"Error in visitor_send_phone_otp: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def visitor_verify_phone_otp(self, request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify OTP and update visitor's phone number.
        Required payload: { phone_number: "+243812345678", otp_code: "123456" }
        """
        try:
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            phone_number = (data.get('phone_number') or '').strip()
            otp_code = (data.get('otp_code') or '').strip()
            
            if not phone_number or not otp_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number and OTP code are required")

            # Find visitor user linked to this device
            user_device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__device_id_str": device_hashed_id},
                _skip_rls=True,
            )
            
            if not user_device or not user_device.get('sys_user_id'):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor account not found")

            sys_user_id = user_device['sys_user_id']

            # Get user with OTP info
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": sys_user_id},
                _skip_rls=True,
            )

            if not user_info:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            stored_otp = user_info.get('phone_otp_code')
            otp_expiry = user_info.get('phone_otp_expires_at')
            otp_target = user_info.get('phone_otp_target')

            if not stored_otp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No OTP pending. Please request a new one.")

            # Check expiry
            if otp_expiry and isinstance(otp_expiry, datetime):
                # Ensure both datetimes are timezone-aware for comparison
                now_utc = datetime.now(timezone.utc)
                if otp_expiry.tzinfo is None:
                    # If otp_expiry is naive, assume it's UTC
                    otp_expiry = otp_expiry.replace(tzinfo=timezone.utc)
                if now_utc > otp_expiry:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired. Please request a new one.")

            # Check OTP match
            if stored_otp != otp_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")

            # Check phone number match
            if otp_target and otp_target != phone_number:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number mismatch")

            # Update user's phone number and clear OTP fields
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=sys_user_id,
                data={
                    "phone_number": phone_number,
                    "is_phone_verified": True,
                    "phone_otp_code": None,
                    "phone_otp_expires_at": None,
                    "phone_otp_target": None,
                }
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Phone verified successfully",
                    "data": {
                        "phone_number": phone_number,
                        "verified": True
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            formated_error = format_exception("visitor_verify_phone_otp", e)
            self.app_debug_print(f"Error in visitor_verify_phone_otp: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def update_visitor_phone(self, request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update visitor's phone number and verification status.
        Required payload: { phone_number: "+243812345678", is_phone_verified: true }
        """
        try:
            # Get device hashed id from request
            device_hashed_id = self.get_optional_device_hashed_id(request, self.accept_language)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.ERRORS, "INVALID_REQUEST_DATA", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            # Use aggregation to find visitor user linked to this device
            # A device can be linked to multiple accounts, so we filter by visitor profile
            from app.modules.auth.models.cfg_user_device.cfg_user_device_model import CfgUserDeviceModel
            
            visitor_device_pipeline = [
                {"$match": {"device_id_str": device_hashed_id}},
                {"$lookup": {
                    "from": "sys_user",
                    "localField": "sys_user_id",
                    "foreignField": "_id",
                    "as": "user_info"
                }},
                {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": False}},
                {"$lookup": {
                    "from": "sys_profil",
                    "localField": "user_info.rbac_profile_id",
                    "foreignField": "_id",
                    "as": "profile_info"
                }},
                {"$unwind": {"path": "$profile_info", "preserveNullAndEmptyArrays": False}},
                {"$match": {"profile_info.flag": ESysProfileFlag.VISITOR_USER_PROFIL.value}},
                {"$limit": 1}
            ]

            visitor_devices = await CfgUserDeviceModel.aggregate(visitor_device_pipeline).to_list(length=1)
            
            if not visitor_devices or len(visitor_devices) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Visitor account not found for this device"
                )

            visitor_device = visitor_devices[0]
            sys_user_id = str(visitor_device['sys_user_id'])

            phone_number = data.get('phone_number')
            is_phone_verified = data.get('is_phone_verified', False)

            if not phone_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number is required"
                )

            # Update user's phone number and verification status
            update_data = {
                "phone_number": phone_number,
                "is_phone_verified": is_phone_verified,
            }

            # Note: can_pay_on_delivery must be activated manually from backoffice
            # It is not automatically set when phone is verified

            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=sys_user_id,
                data=update_data
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Phone verification status updated successfully",
                    "data": {
                        "phone_number": phone_number,
                        "is_phone_verified": is_phone_verified,
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            formated_error = format_exception("update_visitor_phone", e)
            self.app_debug_print(f"Error in update_visitor_phone: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def user_setup_auth_configs(self, request, background_tasks, data: Dict[str, Any],accept_language: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """Register a new user with email for eBlood Connect"""
        try:

            ip_address = await AuthenticatedService.get_optional_api_address(request)
            device_info = await AuthenticatedService.get_optional_device_info(request)
            # Validate the registration data
            try:
                registration_data = UserRegistrationAuthConfigRequest.model_validate(data)
                # registration_data.validate_passwords_match()
            except ValidationError as ve:
                # Return a concise, structured validation error response
                error_details = []
                for err in ve.errors():
                    loc_parts = [str(part) for part in err.get("loc", []) if part != "__root__"]
                    field = ".".join(loc_parts) if loc_parts else "non_field_error"
                    error_details.append({"field": field, "message": err.get("msg", "Invalid value")})

                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "success": False,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "Invalid registration data",
                        "errors": error_details,
                        "data": None,
                    },
                )

            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                query={"filter___id": registration_data.sys_user_id},
                _skip_rls=True,
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language,username=registration_data.email)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )

            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            # Link device to visitor user //existing_device_id
            device_result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                filter_data={
                    "sys_user_id": registration_data.sys_user_id,
                    "device_id_str": device_hashed_id,
                },
                update_data={
                    "sys_user_id": registration_data.sys_user_id,
                    "device_id_str": device_hashed_id,
                    "device_info":device_info,
                    "status": EUserDeviceStatus.ALLOWED.value,
                }
            )
            device_result_id = device_result if isinstance(device_result,str) else device_result['id']

            # delete all existing question response
            await self.generic_service.hard_delete_with_query_data_from_collection(
                collection_key=CollectionKey.CFG_USER_QUESTION_RESPONSE,
                query={"sys_user_id": ObjectId(str(registration_data.sys_user_id))}
            )

            # save question responses
            for question_response in registration_data.question_responses:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_QUESTION_RESPONSE,
                    data={
                        "sys_user_id": registration_data.sys_user_id,
                        "cfg_user_question_id": question_response.question_id,
                        "response": str(question_response.response).strip().lower(),
                    }
                )

            # upser cfg_user_auth_setup
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_AUTH_SETUP,
                filter_data={"sys_user_id": registration_data.sys_user_id},
                update_data={
                    "cfg_user_device_id": device_result_id,
                    "sys_user_id": registration_data.sys_user_id,
                    "is_user_pin_set": True,
                    "user_pin": registration_data.pin,
                    "is_user_biometric_set": registration_data.biometric_enabled,
                }
            )

            # AUTO LOGIN
            return await self._auto_login_user(
                sys_user_id=registration_data.sys_user_id,
                device_hashed_id=device_hashed_id,
                ip_address=ip_address,
                cfg_user_device_id=device_result_id,
            )
        except HTTPException:
            raise
        except ValueError as e:
            self.app_debug_print(f"Registration error: {str(e)}", True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            self.app_debug_print(f"Registration error: {str(e)}", True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register user: {str(e)}"
            )
    async def esdv_users_login(self,request: Request,payload: PhoneNumberLoginRequest):
        try:
            """
            Authenticate a user and return their details.
            """
            # Fetch `Accept-Language` from headers, default to 'fr'
            # Initialize token expiration variables (will be updated later if needed)
            token_expiry_duration = timedelta(minutes=20)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()

            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 

            
            self.app_debug_print(f"\n\n\n\n usernamer: {payload.username}\n\n\n",True)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            ip_address = await self.get_optional_api_address(request,self.accept_language)
            locationInfo = await self.get_location_from_ip_secure(request,self.accept_language)
            # Get the device info from the request
            device_info = await self.get_optional_device_info(request,self.accept_language)
                
            username = str(payload.username).strip()
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__username":str(username).lower().strip()}, 
                _skip_rls=True,
            )
            # history
            self.app_debug_print(f"\n\n\n\n user_info >>>: {user_info}\n\n\n",True)  
            self.app_debug_print(f"\n\n\n\n device_hashed_id >>>: {device_hashed_id}\n\n\n",True)  
            
            if not user_info:
                message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
                self.app_debug_print(f"message : {message}",)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            
            # Check if account is locked
            if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
                if user_info['login_locked_until'] and user_info['login_locked_until'] > datetime.now(timezone.utc):
                    message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=message
                    )
                else:
                    # Unlock the account if the lock period has passed
                    user_info['login_fail_attempt_count'] = 0
                    user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                    user_info['login_locked_until'] = None
                    
            

            self.app_debug_print(f"\n\n\n\n beofore pass werif MFA: {self.accept_language}\n\n\n",False)  
            
            # Reset login failure attempts on successful login
            if user_info['login_fail_attempt_count'] > 0:
                user_info['login_fail_attempt_count'] = 0
                user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                user_info['login_locked_until'] = None
                user_data = {
                    "login_fail_attempt_count":0,
                    "login_locked_until":None,
                    "login_fail_status":ELoginResetPasswordFailStatus.NORMAL,
                }
                # UPDATE USER
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_info['id'],
                    data=user_data
                )

            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":user_info['rbac_profile_id']},
                _skip_rls=True,
            )
            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_NOT_FOUND",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub": str(user_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.MFA_VERIFICATION},
                token_type=EJWTTokenType.MFA_VERIFICATION,
                expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
            )

            # DEVICE CHECKING   
            device_hashed_id = getattr(request.state, "deviceHashedId", None)
            list_of_user_devices = getattr(request.state, "listOfUserDevices", []) 

            # filter by user id
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_info['id'])
            self.app_debug_print(f"\n\n\n\n LAST STEP 1 USER DEVICE INFO : {user_device_info} \n\n\n",True)  

            sys_organization_id = user_info['sys_organization_id']
            if not user_device_info: 
                user_device_info = await self.device_service.create_new_user_device(
                    sys_user_id=user_info['id'],
                    device_id_str=device_hashed_id,
                    sys_organization_id=sys_organization_id,
                    device_info=device_info,
                    accept_language=self.accept_language
                )
            else :
                # CHECK IF DEVICE IS USED BY THE SAME USER
                if user_device_info['sys_user_id'] != user_info['id']:
                    user_device_info = await self.device_service.create_new_user_device(
                        sys_user_id=user_info['id'],
                        device_id_str=device_hashed_id,
                        sys_organization_id=sys_organization_id,
                        device_info=device_info,
                        accept_language=self.accept_language
                    )
                    # message = self.get_response_message(MessageCategory.COMMON, "DEVICE_ALREADY_USED_BY_ANOTHER_USER",self.accept_language,email=support_email)
                    # return CustomJSONResponse(
                    #     status_code=status.HTTP_401_UNAUTHORIZED,
                    #     content={
                    #         "message":message,
                    #         "support_email":support_email,
                    #         "is_device_related_issue":True
                    #     }
                    # )
            self.app_debug_print(f"\n\n\n\n LAST STEP 2 USER DEVICE CREATION : {user_device_info} \n\n\n",True)  
            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    ) 
            self.app_debug_print(f"\n\n\n\n LAST STEP 3\n\n\n",True)  
            user_config_info = await self.device_service.create_or_get_user_config(
                sys_user_id=user_info['id'],
                accept_language=self.accept_language
            )
            self.app_debug_print(f"\n\n\n\n LAST STEP 4\n\n\n",True)
            if not user_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_CONFIG",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    ) 
            
            allowed_device_count = user_config_info.get('allowed_device_count',0)
            self.app_debug_print(f"\n\n\n\n LAST STEP 5\n\n\n",True)  
            # GET ALL ALLOWED DEVICES
            allowed_devices = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__sys_user_id":user_info['id'],
                    "filter__status":EUserDeviceStatus.ALLOWED.value
                },
                _skip_rls=True,
            ) 

            # CHECK IF DEVICE IS NOT ALLOWED
            self.app_debug_print(f"\n\n\n\n LAST STEP 6 : {user_device_info} \n\n\n",True)  
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value and user_profil['flag'] != ESysProfileFlag.TRANS_CUSTOMER.value:
                self.app_debug_print(f"\n\n\n\n LAST STEP 7 : {user_device_info} \n\n\n",True)
                # CHECK IF DEVICE IS BLOCKED
                if user_device_info['status'] == EUserDeviceStatus.LOCKED.value:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 8 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_LOCKED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    ) 
                # CHECK IF DEVICE IS REVOQUED
                if user_device_info['status'] == EUserDeviceStatus.REVOQUED.value:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 9 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_REVOQUED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )  
                token = self.token_service.create_access_token(
                    data={"sub": str(user_device_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                    token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                    expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
                )
                # Initialize token expiration variables
                token_expiry_duration = timedelta(minutes=20)
                token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
                token_expires_in = token_expiry_duration.total_seconds()
                self.app_debug_print(f"\n\n\n\n LAST STEP 10 : {user_device_info} \n\n\n",True)
                # CHECK IF MAX DEVICE REACHED
                if len(allowed_devices) >= allowed_device_count:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 10 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.COMMON, "MAX_DEVICE_REACHED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )  
                self.app_debug_print(f"\n\n\n\n LAST STEP 11 : {user_device_info} \n\n\n",True)
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )
            

            self.app_debug_print(f"\n\n\n\n AFTER DEVICE CREATION: {self.accept_language}\n\n\n",False)   
            # Get current time in UTC 
            await self.login_service.get_or_create_init_login_history_in_30_min(
                sys_user_id=user_info['id'],
                ip_address=ip_address,
                cfg_user_device_id=user_device_info.get("id",None) if user_device_info else None,
                sys_organization_id=user_info['sys_organization_id'],
                device_id_str=device_hashed_id,
                accept_language=self.accept_language
            )
            
            if 'user_account_hash' not in user_info:
                # TODO: UPDATE USER TO ADD user_account_hash login_fail_status
                user_account_hash = HashService.generate_hash(f"{user_info['id']}")
                data_update = {
                    "user_account_hash":user_account_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=user_info['id'], data=data_update)  # TODO: Update user to add user_account_hash
            if 'user_account_socket_hash' not in user_info:
                # TODO: UPDATE USER TO ADD user_account_socket_hash
                user_account_socket_hash = HashService.generate_hash(user_info['id'])
                data_update = {
                    "user_account_socket_hash":user_account_socket_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=user_info['id'], data=data_update)  # TODO: Update user to add user_account_socket_hash
            last = {
                "status_code":status.HTTP_200_OK,
                "redirect_to_mfa":True,
                "access_token":token,
                "username":user_info['username'], 
            }

            #TODO:: REMOVE AS SOON AS POSSIBLE: JUST FOR TESTING
            # AUTO LOGIN FOR TESTING
            # return await self._auto_login_user(user_info['id'],device_hashed_id,ip_address,user_device_info['id'])

            self.app_debug_print(f"\n\n\n\n LAST : {last}\n\n\n",False)   
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "redirect_to_mfa":True,
                        "access_token":token,
                        "expires_in":token_expires_in,
                        "expires_at":token_expires_at,
                        "username":user_info['username'], 
                    }
                ) 
        
        except Exception as e:
            format_error = format_exception(f"error login ",e)
            self.app_debug_print(f"\n\n\n format_error login : {format_error}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )

    async def get_esdv_users_otp(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        app_signature: str = "",
    ):
        try:
            
            # DECODE USER TOKEN 
            self.app_debug_print(f"\n\n\n before get_user_info \n\n\n",True)
            user_details = await self.get_user_info_from_unsecured_path(request,self.accept_language,EJWTTokenType.MFA_VERIFICATION)
            self.app_debug_print(f"\n\n\n user_details get otp {user_details} \n\n\n",True)
            mfa_type = MFaFlag.PHONE_NUMBER.value

            # user_details = await self.get_user_info(request=request,self.accept_language=accept_language)
            # api_Consumer = await self.get_api_consumer(request=request,self.accept_language=accept_language)
            # user_profil = await self.get_user_profil(request=request,self.accept_language=accept_language) 
            # Get current time in UTC
            now = datetime.now(timezone.utc)

            # Calculate the time 30 minutes ago
            start_time = now - timedelta(minutes=10)

            # Query to fetch login history from the last 30 minutes
            login_history_query = {
                "sys_user_id": user_details['id'],
                "status": ELoginStatus.INIT_LOGIN.value,
                "created_at": {"$gte": start_time, "$lt": now}
            }
            self.app_debug_print(f"login_history_query data query > :  {login_history_query}",True)
            
            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )
            self.app_debug_print(f"loginHistory >>> :  {loginHistory}",True)
            
            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            otp_code = GeneratorService.generate_otp(length=6)
            h_data = {
                "otp":f"{otp_code}"
            }
            # UPDATE OTP ON LOGIN HISTORY
            result_update = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=loginHistory['id'],
                data=h_data
            )
            self.app_debug_print(f"\n\n result_update : {result_update} \n\n",True)
                
            self.app_debug_print(f"\n\n otp_code : {otp_code} \n\n",True)
            
            if mfa_type == MFaFlag.EMAIL.value:
                email = user_details.get("email")
                if not email:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                mail_title_translated =  self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_TITLE", self.accept_language)
                # self.app_debug_print(f"mail_title_translated : {mail_title_translated}")
                mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_BODY", self.accept_language, otp_code=otp_code)
                # self.app_debug_print(f"mail_message_translated : {mail_message_translated}")
                second_mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_SECOND_MESSAGE", self.accept_language)
                # self.app_debug_print(f"second_mail_message_translated : {second_mail_message_translated}")
                mail_note_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_NOTE", self.accept_language)
                # self.app_debug_print(f"mail_note_translated : {mail_note_translated}")
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # Send email in background to avoid blocking the request
                    self.app_debug_print(f" current env : {env}",False) 
                asyncio.create_task(asyncio.to_thread(
                    self.email_sender_service.send_simple_email_background,
                    email_to=email,
                    subject=f"{otp_code} - OTP",
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language
                )) 
                
                # Return the formatted response message
                sms= self.get_response_message(MessageCategory.COMMON, "OTP_SENT_EMAIL", self.accept_language, email=email)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":sms 
                    }
                ) 
            
            elif mfa_type == MFaFlag.PHONE_NUMBER.value:
                phone = user_details.get("phone_number")
                if not phone:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_PHONE_NOT_FOUND", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                if app_signature:
                    sms_message = f"<#> Votre code SenatDigit: {otp_code}\n{app_signature}"
                else:
                    # Get the translated SMS message
                    sms_message = self.get_response_message(
                        MessageCategory.COMMON,
                        "OTP_SMS_MESSAGE",
                        self.accept_language,
                        otp_code=otp_code
                    )

                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # Send SMS in background to avoid blocking the request
                    pass
                asyncio.create_task(
                    self.sms_service.lisoloo_send_sms(
                        phone_number=phone,
                        message=sms_message
                    )
                )

                # Return the formatted response message
                message = self.get_response_message(MessageCategory.COMMON, "OTP_SENT_PHONE", self.accept_language, phone=phone)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
        
        except Exception as e:
            self.app_debug_print(f"Error sending esdv users OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    async def esdv_users_post_validate_otp(
        self,
        request: Request, 
        payload: OtpRequest,
    ):
        try:
            
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            ip_address = await self.get_optional_api_address(request,self.accept_language)

            mfa_type = request.query_params.get("mfa_type",MFaFlag.PHONE_NUMBER.value)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )

            self.app_debug_print(f"\n\n\n after saas_config_info \n\n\n",True)
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            
            # DECODE USER TOKEN 
            user_details = await self.token_service.decode_and_get_user_from_token(
                request=request, 
                expected_type=EJWTTokenType.MFA_VERIFICATION, 
            )
            self.app_debug_print(f"\n\n\n after user_details : {user_details} \n\n\n",True)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                _skip_rls=True,
            )
            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_details['id'])
            self.app_debug_print(f"\n\n\n after user_device_info : {user_device_info} \n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )
                # raise HTTPException(status_code=404, detail=message)
            
            # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value and user_profil['flag'] != ESysProfileFlag.TRANS_CUSTOMER.value: 
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )
            loginHistory = await self.login_service.get_today_init_login_history(
                sys_user_id=user_details['id'],
                cfg_user_device_id=user_device_info.get("id")
            )
            self.app_debug_print(f"\n\n\n after loginHistory : {loginHistory} \n\n\n",True)
            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            otp_code = loginHistory.get("otp")
            self.app_debug_print(f"\n\n\n after otp_code : {otp_code} \n\n\n",True)
            if not otp_code:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "LOGIN_PROCESS_NOT_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if mfa_type == MFaFlag.EMAIL.value or mfa_type == MFaFlag.PHONE_NUMBER.value:
                self.app_debug_print(f"\n\n\n before otp matching : {otp_code} : {payload.otp} \n\n\n",True)
                
                # CHECK OTP MACHING HTTP_422_UNPROCESSABLE_ENTITY
                if otp_code != payload.otp:
                    message = self.get_response_message(MessageCategory.COMMON, "OTP_NO_MATCHING", self.accept_language)
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) 
                
                
                return await self._auto_login_user(
                    sys_user_id=user_details['id'],
                    device_hashed_id=device_hashed_id,
                    ip_address=ip_address,
                    cfg_user_device_id=user_device_info['id'],
                ) 
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
        
        except Exception as e:
            self.app_debug_print(f"Error getting OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            



    # AGENT AUTHS
    async def core_users_login(self,request: Request,payload: LoginAgentRequest):
        try:
            """
            Authenticate a user and return their details.
            """
            # Fetch `Accept-Language` from headers, default to 'fr'
            # Initialize token expiration variables (will be updated later if needed)
            token_expiry_duration = timedelta(minutes=20)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()

            # GET HASHED DEVICE ID
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language)


            self.app_debug_print(f"\n\n\n\n usernamer: {payload.username}\n\n\n",True)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            ip_address = await self.get_optional_api_address(request,self.accept_language)
            locationInfo = await self.get_location_from_ip_secure(request,self.accept_language)
            # Get the device info from the request
            device_info = await self.get_optional_device_info(request,self.accept_language)

            username = str(payload.username).strip()
            username = f"243{username}"
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__username":str(username).lower().strip()},
                _skip_rls=True,
            )
            # history
            self.app_debug_print(f"\n\n\n\n user_info >>>: {user_info}\n\n\n",True)
            self.app_debug_print(f"\n\n\n\n device_hashed_id >>>: {device_hashed_id}\n\n\n",True)

            if not user_info:
                message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
                self.app_debug_print(f"message : {message}",)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )

            # Check if account is locked
            if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
                if user_info['login_locked_until'] and user_info['login_locked_until'] > datetime.now(timezone.utc):
                    message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=message
                    )
                else:
                    # Unlock the account if the lock period has passed
                    user_info['login_fail_attempt_count'] = 0
                    user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
                    user_info['login_locked_until'] = None



            self.app_debug_print(f"\n\n\n\n beofore pass werif MFA: {self.accept_language}\n\n\n",False)
            # Verify password
            # if not self.verify_password(password, user_info['password']):
            #     incremented = user_info['login_fail_attempt_count'] + 1
            #     user_data = {
            #         "login_fail_attempt_count":incremented,
            #     }
            #     if incremented >= 5:
            #         user_data = {
            #             "login_locked_until": datetime.now(timezone.utc) + timedelta(days=3),
            #             "login_fail_status":ELoginResetPasswordFailStatus.LOCKED,
            #             **user_data
            #         }
            #     # UPDATE USER mfa
            #     updated = await self.generic_service.update_data_in_collection(
            #         collection_key=CollectionKey.SYS_USER,
            #         item_id=user_info['id'],
            #         data=user_data
            #     )
            #     if user_info['login_fail_status'] == ELoginResetPasswordFailStatus.LOCKED:
            #         message = self.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", self.accept_language)
            #         raise HTTPException(
            #             status_code=status.HTTP_423_LOCKED,
            #             detail=message
            #         )
            #     else:
            #         message = self.get_response_message(MessageCategory.LOGIN, "INVALID_CREDENTIALS", self.accept_language)
            #         raise HTTPException(
            #             status_code=status.HTTP_401_UNAUTHORIZED,
            #             detail=message
            #         )

            # Reset login failure attempts on successful login
            # if user_info['login_fail_attempt_count'] > 0:
            #     user_info['login_fail_attempt_count'] = 0
            #     user_info['login_fail_status'] = ELoginResetPasswordFailStatus.NORMAL
            #     user_info['login_locked_until'] = None
            #     user_data = {
            #         "login_fail_attempt_count":0,
            #         "login_locked_until":None,
            #         "login_fail_status":ELoginResetPasswordFailStatus.NORMAL,
            #     }
            #     # UPDATE USER
            #     updated = await self.generic_service.update_data_in_collection(
            #         collection_key=CollectionKey.SYS_USER,
            #         item_id=user_info['id'],
            #         data=user_data
            #     )

            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub": str(user_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.MFA_VERIFICATION},
                token_type=EJWTTokenType.MFA_VERIFICATION,
                expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
            )

            # Get MFA (Multi-factor Authentication) settings
            default_mfa = None
            mfas = await self.user_available_login_mfa(sys_user_id=user_info['id'],accept_language=self.accept_language)
            self.app_debug_print(f"\n\n\n\n IN MFA: {len(mfas)}\n\n\n",True)
            mfas_with_icon = [];
            for element in mfas:
                self.app_debug_print(f"\n\n mfa element :{element}",False)
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 1 >> {element['name']['display_value']} \n\n\n",True)
                icon_rel = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    output_data_type=OutputDataType.DATA_TABLE.value,
                    query={
                        "filter__targeted_id":element["id"]["display_value"]
                    },
                    sort={"created_at": -1},
                    _skip_rls=True,
                )
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 2 {icon_rel['ref_icon_id']} \n\n\n",True)
                if icon_rel:
                    icon = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_ICON,
                        output_data_type=OutputDataType.DATA_TABLE.value,
                        query={
                            "filter___id":icon_rel["ref_icon_id"]["display_value"],
                        },
                        sort={"created_at": -1},
                        _skip_rls=True,
                    )
                    self.app_debug_print(f"\n\n\n\n IN MFA LOOP 3 \n\n\n",True)
                    if icon:
                        mfas_with_icon.append({
                            **element,
                            "icon":icon
                        })
                    else :
                        mfas_with_icon.append(element)
                    self.app_debug_print(f"\n\n\n\n IN MFA LOOP 4 \n\n\n",True)
                else :
                    mfas_with_icon.append(element)

            if len(mfas_with_icon) > 0 :
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 5 \n\n\n",True)
                self.app_debug_print(f"\n\n\n\n IN MFA LOOP 5 {len(mfas_with_icon)} \n\n\n",True)
                default_mfa = mfas_with_icon[0]
            self.app_debug_print(f"\n\n\n\n AFTER MFA: {len(mfas)}\n\n\n",True)
            # DEVICE CHECKING
            device_hashed_id = getattr(request.state, "deviceHashedId", None)
            list_of_user_devices = getattr(request.state, "listOfUserDevices", [])

            # filter by user id
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_info['id'])
            self.app_debug_print(f"\n\n\n\n LAST STEP 1 USER DEVICE INFO : {user_device_info} \n\n\n",True)

            sys_organization_id = user_info['sys_organization_id']
            if not user_device_info:
                user_device_info = await self.device_service.create_new_user_device(
                    sys_user_id=user_info['id'],
                    device_id_str=device_hashed_id,
                    sys_organization_id=sys_organization_id,
                    device_info=device_info,
                    accept_language=self.accept_language
                )
            else :
                # CHECK IF DEVICE IS USED BY THE SAME USER
                if user_device_info['sys_user_id'] != user_info['id']:
                    user_device_info = await self.device_service.create_new_user_device(
                        sys_user_id=user_info['id'],
                        device_id_str=device_hashed_id,
                        sys_organization_id=sys_organization_id,
                        device_info=device_info,
                        accept_language=self.accept_language
                    )
                    # message = self.get_response_message(MessageCategory.COMMON, "DEVICE_ALREADY_USED_BY_ANOTHER_USER",self.accept_language,email=support_email)
                    # return CustomJSONResponse(
                    #     status_code=status.HTTP_401_UNAUTHORIZED,
                    #     content={
                    #         "message":message,
                    #         "support_email":support_email,
                    #         "is_device_related_issue":True
                    #     }
                    # )
            self.app_debug_print(f"\n\n\n\n LAST STEP 2 USER DEVICE CREATION : {user_device_info} \n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
            self.app_debug_print(f"\n\n\n\n LAST STEP 3\n\n\n",True)
            user_config_info = await self.device_service.create_or_get_user_config(
                sys_user_id=user_info['id'],
                accept_language=self.accept_language
            )
            self.app_debug_print(f"\n\n\n\n LAST STEP 4\n\n\n",True)
            if not user_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_CONFIG",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )

            allowed_device_count = user_config_info.get('allowed_device_count',0)
            self.app_debug_print(f"\n\n\n\n LAST STEP 5\n\n\n",True)
            # GET ALL ALLOWED DEVICES
            allowed_devices = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__sys_user_id":user_info['id'],
                    "filter__status":EUserDeviceStatus.ALLOWED.value
                },
                _skip_rls=True,
            )

            # GET COUNT LOGIN HISTORY WHERE session_actual_expiration DATE IS GREATER OR EQUAL TO NOW GROUP BY cfg_user_device_id
            # pipeline = [
            #     {
            #         "$match": {
            #             "sys_user_id": user_info['id'],
            #             "status":ELoginStatus.LOGGED_IN.value,
            #             "session_actual_expiration": {"$gte": datetime.now(timezone.utc)}
            #         }
            #     },
            #     {
            #         "$group": {
            #             "_id": "$cfg_user_device_id",
            #             "count": {"$sum": 1}
            #         }
            #     },
            #     {
            #         "$project": {
            #             "cfg_user_device_id": "$_id",
            #             "login_count": "$count",
            #             "_id": 0
            #         }
            #     }
            # ]

            # login_histories = await self.generic_service.fetch_native_aggregate_data_from_collection(
            #     collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
            #     all_data=True,
            #     output_data_type=OutputDataType.DEFAULT,
            #     pipeline=pipeline,
            # )

            # active_login_device_session_count = sum(login['login_count'] for login in login_histories)

            # CHECK IF DEVICE IS NOT ALLOWED
            self.app_debug_print(f"\n\n\n\n LAST STEP 6 : {user_device_info} \n\n\n",True)
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value:
                self.app_debug_print(f"\n\n\n\n LAST STEP 7 : {user_device_info} \n\n\n",True)
                # CHECK IF DEVICE IS BLOCKED
                if user_device_info['status'] == EUserDeviceStatus.LOCKED.value:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 8 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_LOCKED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
                # CHECK IF DEVICE IS REVOQUED
                if user_device_info['status'] == EUserDeviceStatus.REVOQUED.value:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 9 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.LOGIN, "DEVICE_REVOQUED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True
                        }
                    )
                token = self.token_service.create_access_token(
                    data={"sub": str(user_device_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                    token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                    expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
                )
                # Initialize token expiration variables
                token_expiry_duration = timedelta(minutes=20)
                token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
                token_expires_in = token_expiry_duration.total_seconds()
                self.app_debug_print(f"\n\n\n\n LAST STEP 10 : {user_device_info} \n\n\n",True)
                # CHECK IF MAX DEVICE REACHED
                if len(allowed_devices) >= allowed_device_count:
                    self.app_debug_print(f"\n\n\n\n LAST STEP 10 : {user_device_info} \n\n\n",True)
                    message = self.get_response_message(MessageCategory.COMMON, "MAX_DEVICE_REACHED",self.accept_language,email=support_email)
                    return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )
                self.app_debug_print(f"\n\n\n\n LAST STEP 11 : {user_device_info} \n\n\n",True)
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                return CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_device_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )
            # 1. Check allowed platform
            # await check_allowed_platform(user_id=user.id, platform=platform, self.accept_language=self.accept_language)


            self.app_debug_print(f"\n\n\n\n AFTER DEVICE CREATION: {self.accept_language}\n\n\n",False)
            # Get current time in UTC
            await self.login_service.get_or_create_init_login_history_in_30_min(
                sys_user_id=user_info['id'],
                ip_address=ip_address,
                cfg_user_device_id=user_device_info.get("id",None) if user_device_info else None,
                sys_organization_id=user_info['sys_organization_id'],
                device_id_str=device_hashed_id,
                accept_language=self.accept_language
            )

            if 'user_account_hash' not in user_info:
                # TODO: UPDATE USER TO ADD user_account_hash login_fail_status
                user_account_hash = HashService.generate_hash(f"{user_info['id']}")
                data_update = {
                    "user_account_hash":user_account_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=user_info['id'], data=data_update)  # TODO: Update user to add user_account_hash
            if 'user_account_socket_hash' not in user_info:
                # TODO: UPDATE USER TO ADD user_account_socket_hash
                user_account_socket_hash = HashService.generate_hash(user_info['id'])
                data_update = {
                    "user_account_socket_hash":user_account_socket_hash
                }
                await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=user_info['id'], data=data_update)  # TODO: Update user to add user_account_socket_hash
            last = {
                "status_code":status.HTTP_200_OK,
                "redirect_to_mfa":True,

                "mfas":mfas_with_icon,
                "default_mfa":default_mfa,
                "access_token":token,
                "username":user_info['username'],
            }
            self.app_debug_print(f"\n\n\n\n LAST : {last}\n\n\n",False)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "redirect_to_mfa":True,

                        "mfas":mfas_with_icon,
                        "default_mfa":default_mfa,
                        "access_token":token,
                        "expires_in":token_expires_in,
                        "expires_at":token_expires_at,
                        "username":user_info['username'],
                    }
                )

        except Exception as e:
            format_error = format_exception(f"error login ",e)
            self.app_debug_print(f"\n\n\n format_error login : {format_error}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    async def get_core_users_get_otp(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        app_signature: str = "",
    ):
        try:
            
            # DECODE USER TOKEN 
            self.app_debug_print(f"\n\n\n before get_user_info \n\n\n",True)
            user_details = await self.get_user_info_from_unsecured_path(request,self.accept_language,EJWTTokenType.MFA_VERIFICATION)
            self.app_debug_print(f"\n\n\n user_details get otp {user_details} \n\n\n",True)
            mfa_type = MFaFlag.PHONE_NUMBER.value

            # user_details = await self.get_user_info(request=request,self.accept_language=accept_language)
            # api_Consumer = await self.get_api_consumer(request=request,self.accept_language=accept_language)
            # user_profil = await self.get_user_profil(request=request,self.accept_language=accept_language) 
            # Get current time in UTC
            now = datetime.now(timezone.utc)

            # Calculate the time 30 minutes ago
            start_time = now - timedelta(minutes=10)

            # Query to fetch login history from the last 30 minutes
            login_history_query = {
                "sys_user_id": user_details['id'],
                "status": ELoginStatus.INIT_LOGIN.value,
                "created_at": {"$gte": start_time, "$lt": now}
            }
            self.app_debug_print(f"login_history_query data query > :  {login_history_query}",True)
            
            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1},
                _skip_rls=True,
            )
            self.app_debug_print(f"loginHistory >>> :  {loginHistory}",True)
            
            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            otp_code = GeneratorService.generate_otp(length=6)
            h_data = {
                "otp":f"{otp_code}"
            }
            # UPDATE OTP ON LOGIN HISTORY
            result_update = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                item_id=loginHistory['id'],
                data=h_data
            )
            self.app_debug_print(f"\n\n result_update : {result_update} \n\n",True)
                
            self.app_debug_print(f"\n\n otp_code : {otp_code} \n\n",True)
            
            if mfa_type == MFaFlag.EMAIL.value:
                email = user_details.get("email")
                if not email:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                mail_title_translated =  self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_TITLE", self.accept_language)
                # self.app_debug_print(f"mail_title_translated : {mail_title_translated}")
                mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_BODY", self.accept_language, otp_code=otp_code)
                # self.app_debug_print(f"mail_message_translated : {mail_message_translated}")
                second_mail_message_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_SECOND_MESSAGE", self.accept_language)
                # self.app_debug_print(f"second_mail_message_translated : {second_mail_message_translated}")
                mail_note_translated = self.get_response_message(MessageCategory.COMMON, "OTP_EMAIL_NOTE", self.accept_language)
                # self.app_debug_print(f"mail_note_translated : {mail_note_translated}")
                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # Send email in background to avoid blocking the request
                    self.app_debug_print(f" current env : {env}",False)
                     
                asyncio.create_task(asyncio.to_thread(
                    self.email_sender_service.send_simple_email_background,
                    email_to=email,
                    subject=f"{otp_code} - OTP",
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language
                )) 
                
                # Return the formatted response message
                sms= self.get_response_message(MessageCategory.COMMON, "OTP_SENT_EMAIL", self.accept_language, email=email)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":sms 
                    }
                ) 
            
            elif mfa_type == MFaFlag.PHONE_NUMBER.value:
                phone = user_details.get("username")
                # phone = user_details.get("phone_number")
                if not phone:
                    message = self.get_response_message(MessageCategory.COMMON, "USER_PHONE_NOT_FOUND", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                # Format SMS — use SMS Retriever API format if app_signature provided
                if app_signature:
                    sms_message = f"<#> Votre code SenatDigit Apps: {otp_code}\n{app_signature}"
                else:
                    sms_message = self.get_response_message(
                        MessageCategory.COMMON,
                        "OTP_SMS_MESSAGE",
                        self.accept_language,
                        otp_code=otp_code
                    )

                env = settings.ENV.lower()
                if env == "production" or env == "development":
                    # Send SMS in background to avoid blocking the request
                    pass
                    # asyncio.create_task(
                    #     self.sms_service.lisoloo_send_sms(
                    #         phone_number=phone,
                    #         message=sms_message
                    #     )
                    # )
                asyncio.create_task(
                    self.sms_service.lisoloo_send_sms(
                        phone_number=phone,
                        message=sms_message
                    )
                )

                # Return the formatted response message
                message = self.get_response_message(MessageCategory.COMMON, "OTP_SENT_PHONE", self.accept_language, phone=phone)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
        
        except Exception as e:
            self.app_debug_print(f"Error sending esdv users OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    async def core_users_post_validate_otp(
        self,
        request: Request, 
        payload: OtpRequest,
    ):
        try:
            
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            device_hashed_id =  self.get_optional_device_hashed_id(request,self.accept_language)
            ip_address = await self.get_optional_api_address(request,self.accept_language)

            mfa_type = request.query_params.get("mfa_type",MFaFlag.PHONE_NUMBER.value)

            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                _skip_rls=True,
            )

            self.app_debug_print(f"\n\n\n after saas_config_info \n\n\n",True)
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            
            # DECODE USER TOKEN 
            user_details = await self.token_service.decode_and_get_user_from_token(
                request=request, 
                expected_type=EJWTTokenType.MFA_VERIFICATION, 
            )
            self.app_debug_print(f"\n\n\n after user_details : {user_details} \n\n\n",True)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                _skip_rls=True,
            )
            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            
            user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_details['id'])
            self.app_debug_print(f"\n\n\n after user_device_info : {user_device_info} \n\n\n",True)
            if not user_device_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )
                # raise HTTPException(status_code=404, detail=message)
            
            # TODO : RECHECK IF ALLOWED DEVICE IS MANDATORY
            if user_device_info['status'] != EUserDeviceStatus.ALLOWED.value and user_profil['flag'] != ESysProfileFlag.TRANS_CUSTOMER.value: 
                message = self.get_response_message(MessageCategory.COMMON, "DEVICE_NOT_ALLOWED",self.accept_language,email=support_email)
                return CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True
                    }
                )
            loginHistory = await self.login_service.get_today_init_login_history(
                sys_user_id=user_details['id'],
                cfg_user_device_id=user_device_info.get("id")
            )
            self.app_debug_print(f"\n\n\n after loginHistory : {loginHistory} \n\n\n",True)
            if not loginHistory:
                message = self.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            otp_code = loginHistory.get("otp")
            self.app_debug_print(f"\n\n\n after otp_code : {otp_code} \n\n\n",True)
            if not otp_code:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "LOGIN_PROCESS_NOT_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if mfa_type == MFaFlag.EMAIL.value or mfa_type == MFaFlag.PHONE_NUMBER.value:
                self.app_debug_print(f"\n\n\n before otp matching : {otp_code} : {payload.otp} \n\n\n",True)
                
                # CHECK OTP MACHING HTTP_422_UNPROCESSABLE_ENTITY
                if otp_code != payload.otp:
                    message = self.get_response_message(MessageCategory.COMMON, "OTP_NO_MATCHING", self.accept_language)
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) 
                
                
                return await self._auto_login_user(
                    sys_user_id=user_details['id'],
                    device_hashed_id=device_hashed_id,
                    ip_address=ip_address,
                    cfg_user_device_id=user_device_info['id'],
                ) 
            else:
                message = self.get_response_message(MessageCategory.COMMON, "INVALID_MFA_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
        
        except Exception as e:
            self.app_debug_print(f"Error getting OTP: {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
