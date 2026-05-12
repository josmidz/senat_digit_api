



from datetime import timedelta,datetime
from typing import Any, Dict, Optional, List

from fastapi import HTTPException,status,Request    
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.configs.config import settings
from app.modules.core.enums.type_enum import EJWTTokenType, EMultipleValidationStatus, EMultipleValidationType, OutputDataType
from app.modules.core.services.datetime.datetime_service import DatetimeService
from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
from app.modules.core.constants.common import CASCADE_CHILDREN_MAPPING

 
class SecurityValidationService(ResponseService,DatetimeService,EMailSenderService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        # IMPORT TO PREVENT RECURSIVE CALL
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        self.accept_language = accept_language
        self.token_service = TokenService(accept_language=accept_language)
        self.generic_service = GenericService(accept_language=accept_language)
        super().__init__(accept_language)
        
        
    async def validation_process(
        self,
        request: Request,
        operation_type: EMultipleValidationType,
        sudo_action: Dict[str, Any],
        collection_name: str,
        user_details: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None,
        target_document_id: Optional[Dict[str, Any]] = None,
        upsert_query: Optional[Dict[str, Any]] = None,
        download_email: Optional[Dict[str, Any]] = None,
        by_pass_http_return: Optional[bool] = False,
        cascade_children: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        .. deprecated::
            This method is superseded by the grouped-validation flow built into
            ``GenericService._queue_group_validation_request()``, which is triggered
            automatically by the CRUD helpers (``add_data_to_collection``,
            ``update_data_in_collection``, ``hard_delete_data_from_collection``, …)
            when the request state carries a grouped sudo-action context.

            Callers that previously invoked this method directly should be updated
            to rely on the CRUD helpers instead.  The new path:
            - Creates ``OpsValidationRequestModel`` with all required fields.
            - Creates individual ``OpsValidationRequestUserModel`` rows (ordered).
            - Sets ``ops_validation_request_id`` (parent linkage from header).
            - Sets ``validation_request_type`` (group / cross-org / inter-connected).
            - Sends email *and* SMS to the first validator (fire-and-forget).
            - Manages the VALIDATION_PROCESS Redis key for reliable sub-process linkage.

        Raises:
            NotImplementedError: always — use the CRUD-path instead.
        """
        raise NotImplementedError(
            "SecurityValidationService.validation_process() has been deprecated. "
            "Use the GenericService CRUD methods (add_data_to_collection / "
            "update_data_in_collection / hard_delete_data_from_collection) with a "
            "grouped sudo-action context in request.state — they automatically call "
            "_queue_group_validation_request() which is the authoritative path."
        )
        # ----- DEAD CODE BELOW — kept for reference only, will be removed -----
        # Validate data
        DebugService.app_debug_print(f"\n\n\n RESPONSE SUDO ACTION ++++ : : {sudo_action} ++++++ \n\n\n",False)
        is_sudo_action = sudo_action.get('is_sudo_action',False)
        is_sudo_group_action = sudo_action.get('is_sudo_group_action',False)
        can_proceed = sudo_action.get('can_proceed',False)
        random_selected_golden_number = sudo_action.get('selected_golden_number',0)
        random_sudo_action_info = sudo_action.get('random_sudo_action_info',None)
        message = sudo_action.get('message',None)
        instruction_id = sudo_action.get('instruction_id',False)
        sudo_group_users = sudo_action.get('sudo_group_users',[])
        
        # GET ENDPOINT PATH AND METHOD
        endpoint_path = request.url.path
        endpoint_method = request.method    
        
        # print(f"\n\n\n endpoint_path : {endpoint_path}")
        # print(f"\n\n\n endpoint_method : {endpoint_method}")
        
        
        if is_sudo_action == True:
            message = message if message else ResponseService.get_response_message(MessageCategory.SUCCESS, "SUDO_ACTION_IS_REQUIRED", self.accept_language)
            DebugService.app_debug_print(f"\n\n\n sudo_action : {sudo_action} \n\n\n",True)
            return {
                "is_sudo_action":True,
                "is_sudo_group_action":False,
                "message": message,
                "data":{
                    "instruction_id":instruction_id,
                    "selected_golden_number":random_selected_golden_number,
                    "random_sudo_action_info": random_sudo_action_info
                }
            }
            # return CustomJSONResponse(
            #     status_code=status.HTTP_200_OK,
            #     content={
            #         "status_code": status.HTTP_200_OK,
            #         "is_sudo_action":True,
            #         "message": message,
            #         "data":{
            #             "instruction_id":instruction_id,
            #             "selected_golden_number":random_selected_golden_number,
            #             "random_sudo_action_info": random_sudo_action_info
            #         }
            #     }
            # ) 
        
        DebugService.app_debug_print(f"\n\n\n rbac_endpoint : {sudo_action} \n\n\n",False)
        if is_sudo_group_action == True:
            DebugService.app_debug_print(f"\n\n\n sudo_group_users : {len(sudo_group_users)} \n\n\n",True)
            if len(sudo_group_users) == 0:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUDO_GROUP_USERS_FOUND", self.accept_language)
                raise HTTPException(status_code=403, detail=message)
            
            # validationRequests
            formated_validator_users = []
            #ValidatorUser
            first_user_info = None
            for index,user in enumerate(sudo_group_users):
                DebugService.app_debug_print(f"\n\n\n user : {user} \n\n\n",True) 
                if first_user_info is None and user['has_validation_access'] == True:
                    first_user_info = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id":str(user['sys_user_id'])}, 
                    ) 
                formated_validator_users.append({
                    "sys_user_id": str(user['sys_user_id']),
                    "has_validation_access":user['has_validation_access'],
                }) 
            if not first_user_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_VALIDATION_ACCESS_USER_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            next_validator_id = first_user_info['id']
            DebugService.app_debug_print(f"\n\n\n formated_validator_users : {len(formated_validator_users)} \n\n\n",True)
            DebugService.app_debug_print(f"\n\n\n first_user_info : {first_user_info} \n\n\n",True)
            cascade_children = cascade_children if cascade_children else self.get_cascade_children(collection_name)
            if operation_type == EMultipleValidationType.CREATE:
                if not data:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "DATA_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                data["multiple_validation_status"] = EMultipleValidationStatus.PENDING.value
                data["created_by_id"] = user_details['id']
                item_id = await self.generic_service.add_data_to_collection(CollectionKey(collection_name), data)
                validation_request_data = {
                    "collection_name": collection_name,
                    "operation_type": operation_type.value,
                    "target_document_id": item_id,
                    "status": EMultipleValidationStatus.PENDING.value,
                    "validator_users": formated_validator_users,
                    "created_by_id": user_details['id'],
                    "sys_organization_id": user_details['sys_organization_id'],
                    "endpoint_path":endpoint_path,
                    "endpoint_method":endpoint_method,
                    "next_validator_id": next_validator_id,
                    "cascade_children": cascade_children,
                }
                
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_VALIDATION_QUEUED", self.accept_language)
            elif operation_type == EMultipleValidationType.UPDATE:
                if not data:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "DATA_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                if not target_document_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "TARGET_DOCUMENT_ID_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                validation_request_data = {
                    "collection_name": collection_name,
                    "operation_type": operation_type.value,
                    "data": data,
                    "target_document_id": target_document_id,
                    "status": EMultipleValidationStatus.PENDING.value,
                    "validator_users": formated_validator_users,
                    "created_by_id": user_details['id'],
                    "sys_organization_id": user_details['sys_organization_id'],
                    "endpoint_path":endpoint_path,
                    "endpoint_method":endpoint_method,
                    "next_validator_id": next_validator_id,
                    "cascade_children": cascade_children,
                }
            elif operation_type == EMultipleValidationType.UPSERT:
                if not data:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "DATA_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                if not upsert_query:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "UPSERT_QUERY_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                if not target_document_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "TARGET_DOCUMENT_ID_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                validation_request_data = {
                    "collection_name": collection_name,
                    "operation_type": operation_type.value,
                    "data": data,
                    "upsert_query": upsert_query,
                    "target_document_id": target_document_id,
                    "status": EMultipleValidationStatus.PENDING.value,
                    "validator_users": formated_validator_users,
                    "created_by_id": user_details['id'],
                    "sys_organization_id": user_details['sys_organization_id'],
                    "endpoint_path":endpoint_path,
                    "endpoint_method":endpoint_method,
                    "next_validator_id": next_validator_id,
                    "cascade_children": cascade_children,
                }
            elif operation_type == EMultipleValidationType.HARD_DELETE or operation_type == EMultipleValidationType.SOFT_DELETE:
                if not target_document_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "TARGET_DOCUMENT_ID_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                validation_request_data = {
                    "collection_name": collection_name,
                    "operation_type": operation_type.value,
                    "target_document_id": target_document_id,
                    "status": EMultipleValidationStatus.PENDING.value,
                    "validator_users": formated_validator_users,
                    "created_by_id": user_details['id'],
                    "sys_organization_id": user_details['sys_organization_id'],
                    "endpoint_path":endpoint_path,
                    "endpoint_method":endpoint_method,
                    "next_validator_id": next_validator_id,
                    "cascade_children": cascade_children,
                }
            elif operation_type == EMultipleValidationType.DOWNLOAD:
                if not download_email:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "DOWNLOAD_EMAIL_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                if not target_document_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "TARGET_DOCUMENT_ID_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                validation_request_data = {
                    "collection_name": collection_name,
                    "operation_type": operation_type.value,
                    "target_document_id": target_document_id,
                    "status": EMultipleValidationStatus.PENDING.value,
                    "validator_users": formated_validator_users,
                    "created_by_id": user_details['id'],
                    "download_email":download_email,
                    "sys_organization_id": user_details['sys_organization_id'],
                    "endpoint_path":endpoint_path,
                    "endpoint_method":endpoint_method,
                    "next_validator_id": next_validator_id,
                    "cascade_children": cascade_children,
                }
            elif operation_type == EMultipleValidationType.SHARE:
                if not target_document_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "TARGET_DOCUMENT_ID_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                validation_request_data = {
                    "collection_name": collection_name,
                    "operation_type": operation_type.value,
                    "target_document_id": target_document_id,
                    "status": EMultipleValidationStatus.PENDING.value,
                    "validator_users": formated_validator_users,
                    "created_by_id": user_details['id'],
                    "sys_organization_id": user_details['sys_organization_id'],
                    "endpoint_path":endpoint_path,
                    "endpoint_method":endpoint_method,
                    "next_validator_id": next_validator_id,
                    "cascade_children": cascade_children,
                    # "shared_with_user_ids": shared_with_user_ids
                }
            # SAVE VALIDATION REQUEST
            DebugService.app_debug_print(f"\n\n\n validation_request_data : {validation_request_data}\n\n\n")
            validation_item_id = await self.generic_service.add_data_to_collection(CollectionKey.OPS_VALIDATION_REQUEST, validation_request_data)

            # 🚀 PERFORMANCE FIX: Replace blocking time.sleep(2) with async delay
            # This prevents blocking the main thread while waiting for database consistency
            import asyncio
            await asyncio.sleep(0.1)  # Much shorter delay, just for database consistency

            validation_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_VALIDATION_REQUEST,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":str(validation_item_id)},
            )
            DebugService.app_debug_print(f"\n\n\n validation_info : {validation_info}\n\n\n",False)
            DebugService.app_debug_print(f"\n\n\n first_user_info : {first_user_info}\n\n\n",False)
            # send first validation request email
            if first_user_info and validation_info:
                await self.send_first_validation_request_email(
                    data=validation_info,
                    user=first_user_info
                )
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_VALIDATION_QUEUED", self.accept_language)
            return {
                "is_sudo_group_action": True,
                "is_sudo_action": False,
                "message": message,
                "data": {
                    "instruction_id": instruction_id,
                    "selected_golden_number": random_selected_golden_number,
                    "random_sudo_action_info": random_sudo_action_info
                }
            }
        else:
            return {
                "is_sudo_group_action": False,
                "is_sudo_action": False,
                "message": message,
                "data": {
                    "instruction_id": instruction_id,
                    "selected_golden_number": random_selected_golden_number,
                    "random_sudo_action_info": random_sudo_action_info
                }
            }
        
    async def send_first_validation_request_sms(
        self,
        data: Dict[str, Any],
        user: Dict[str, Any],
    ) -> None:
        """
        Send an SMS notification to the first validator.

        Fire-and-forget: errors are caught and logged without bubbling up.
        Uses the Lisoloo async provider (with automatic backup URL fallback).
        Falls back silently when no phone number is configured.
        """
        from app.modules.core.services.sms.sms_service import SmsService
        import asyncio

        phone: str = str(user.get("phone") or user.get("phone_number") or "").strip()
        if not phone:
            DebugService.app_debug_print(
                f"send_first_validation_request_sms: no phone for user {user.get('id', 'N/A')} — skipped",
                True,
            )
            return

        identifier = data.get("identifier", "")
        pending_validation_redirect_token = self.token_service.create_access_token(
            data={
                "sub": data["id"],
                "device_id_str": "",
                "type": EJWTTokenType.PENDING_REQUEST_VALIDATION,
            },
            token_type=EJWTTokenType.PENDING_REQUEST_VALIDATION,
            expires_delta=timedelta(days=30),
        )
        redirect_url = (
            f"{settings.FRONT_END_ANGULAR_BASE_URL}"
            f"/dp/validations/requested?elementID={pending_validation_redirect_token}"
        )
        sms_body = self.get_response_message(
            MessageCategory.MULTI_VALIDATION,
            "SMS_PENDING_MULTI_VALIDATION_BODY",
            self.accept_language,
            identifier=identifier,
            url=redirect_url,
        )

        async def _send_sms_background() -> None:
            try:
                sms_service = SmsService(accept_language=self.accept_language)
                await sms_service.send_sms_httpx_async(phone, sms_body)
                DebugService.app_debug_print(
                    f"✅ Validation SMS sent to {phone}", True
                )
            except Exception as exc:
                DebugService.app_debug_print(
                    f"❌ Validation SMS failed for {phone}: {exc}", True
                )

        try:
            asyncio.create_task(_send_sms_background())
            DebugService.app_debug_print("📱 SMS task scheduled for background processing", True)
        except Exception as exc:
            DebugService.app_debug_print(
                f"⚠️ Failed to schedule background SMS task: {exc}", True
            )

    async def send_first_validation_request_email(self,data:Dict[str,Any],user:Dict[str,Any]) -> None:
        # device_hashed_id = request.state.device_hashed_id
        
        # Send email to user with validation link
        DebugService.app_debug_print(f" in  : send_first_validation_request_email {data}",False)
        email = user.get("email")
        user_id = user.get("id")
        validation_mail_title_translated = self.get_response_message(MessageCategory.MULTI_VALIDATION, "PENDING_MULTI_VALIDATION_TITLE", self.accept_language)
        mail_message_translated = self.get_response_message(MessageCategory.MULTI_VALIDATION, "EMAIL_PENDING_MULTI_VALIDATION_BODY", self.accept_language)
        notification_message_translated = self.get_response_message(MessageCategory.MULTI_VALIDATION, "NOTIFICATION_PENDING_MULTI_VALIDATION_BODY", self.accept_language, name=f"{user['first_name']} {user['last_name']}")
        if email:
            DebugService.app_debug_print(f"mail_title_translated : {validation_mail_title_translated}",True)
            # Prepare email data for background processing
            second_mail_message_translated = self.get_response_message(MessageCategory.MULTI_VALIDATION, "MULTIPLE_VALIDATION_EMAIL_SECOND_MESSAGE", self.accept_language)
            formatted_date = DatetimeService.format_date_with_locale(locale_code=self.accept_language, date=datetime.today())
            formatted_time = self.format_datetime(datetime.today(), include_time=True, include_seconds=False)
            mail_note_translated = self.get_response_message(MessageCategory.COMMON, "MULTIPLE_VALIDATION_EMAIL_NOTE", self.accept_language,date=formatted_date,time=formatted_time)

            pending_validation_redirect_token = self.token_service.create_access_token(
                data={"sub": data['id'],"device_id_str":'', "type":EJWTTokenType.PENDING_REQUEST_VALIDATION},
                token_type=EJWTTokenType.PENDING_REQUEST_VALIDATION,
                expires_delta=timedelta(days=30)  # Expires after 30 minutes
            )

            pending_validation_redirect_url = f"{settings.FRONT_END_ANGULAR_BASE_URL}/dp/validations/requested?elementID={pending_validation_redirect_token}"
            pending_validation_button_message = self.get_response_message(MessageCategory.MULTI_VALIDATION, "CLICK_HERE_TO_ACCESS_VALIDATION", self.accept_language)

            # 🚀 PERFORMANCE FIX: Send email asynchronously in background
            # This prevents blocking the main request thread
            email_data = {
                "email_to": email,
                "subject": f"{data['identifier']} - {validation_mail_title_translated}",
                "mail_title_translated": validation_mail_title_translated,
                "mail_message_translated": mail_message_translated,
                "second_mail_message_translated": second_mail_message_translated,
                "mail_note_translated": mail_note_translated,
                "accept_language": self.accept_language,
                "action_button_url": pending_validation_redirect_url,
                "action_button_text": pending_validation_button_message,
            }

            # 🚀 PERFORMANCE FIX: Schedule email sending as fire-and-forget background task
            # This ensures the main request returns immediately without waiting for email
            import asyncio
            try:
                # Create task but don't await it - this makes it truly non-blocking
                task = asyncio.create_task(self._send_validation_email_background(email_data))
                # Optional: Add task to a set to prevent garbage collection (if needed)
                # background_tasks.add(task)
                # task.add_done_callback(background_tasks.discard)
                DebugService.app_debug_print("📧 Email task scheduled for background processing", True)
            except Exception as e:
                # If task creation fails, log but don't break the main flow
                DebugService.app_debug_print(f"⚠️ Failed to schedule background email task: {str(e)}", True)
        if user_id:
            DebugService.app_debug_print(f" user_id  : {user_id}",True)
            # save user local notification
            notification_data = {
                "title":validation_mail_title_translated,
                "notification":notification_message_translated,
                "targeted_id":user_id,
            }
            await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.NTF_NOTIFICATION, data=notification_data)

    async def _send_validation_email_background(self, email_data: Dict[str, Any]) -> None:
        """
        Send validation email in background without blocking any threads.

        This method runs the synchronous email sending in a thread pool executor
        to prevent blocking the asyncio event loop.

        Args:
            email_data: Dictionary containing all email parameters
        """
        try:
            DebugService.app_debug_print("🚀 Starting background email sending...", True)

            # 🚀 PERFORMANCE FIX: Run blocking email operation in thread pool
            # This prevents blocking the asyncio event loop
            import asyncio
            import concurrent.futures

            def send_email_sync():
                """Synchronous email sending function to run in thread pool"""
                email_sender_service = EMailSenderService(accept_language=email_data["accept_language"])
                return email_sender_service.sending_translated_email_with_redirect_button(
                    email_to=email_data["email_to"],
                    subject=email_data["subject"],
                    mail_title_translated=email_data["mail_title_translated"],
                    mail_message_translated=email_data["mail_message_translated"],
                    second_mail_message_translated=email_data["second_mail_message_translated"],
                    mail_note_translated=email_data["mail_note_translated"],
                    accept_language=email_data["accept_language"],
                    action_button_url=email_data["action_button_url"],
                    action_button_text=email_data["action_button_text"],
                )

            # Execute the blocking email operation in a separate thread
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(executor, send_email_sync)

            DebugService.app_debug_print(f"✅ Background email sent successfully to: {email_data['email_to']}", True)

        except Exception as e:
            # Log error but don't raise - we don't want background email failures to affect main flow
            DebugService.app_debug_print(f"❌ Background email sending failed: {str(e)}", True)
            DebugService.app_debug_print(f"Email recipient: {email_data.get('email_to', 'unknown')}", True)

            # Optionally, you could implement retry logic here or save failed emails to a queue
            # For now, we just log the error and continue

    def get_cascade_children(self, collection_name: str) -> List[Dict[str, str]]:
        """
        Get cascade children configuration for a given collection name.

        Args:
            collection_name (str): The collection name (e.g., "ARCH_FOLDER")

        Returns:
            List[Dict[str, str]]: List of cascade children configurations

        Example:
            >>> validation_service = ValidationService()
            >>> children = validation_service.get_cascade_children("ARCH_FOLDER")
            >>> print(children)
            [{"collection_name": "ARCH_FILE", "field_name": "arch_folder_id"}]
        """
        # Remove CollectionKey prefix if present (e.g., "CollectionKey.ARCH_FOLDER" -> "ARCH_FOLDER")
        if collection_name.startswith("CollectionKey."):
            collection_name = collection_name.replace("CollectionKey.", "")

        # Get cascade children from the mapping
        cascade_children = CASCADE_CHILDREN_MAPPING.get(collection_name, [])

        return cascade_children
