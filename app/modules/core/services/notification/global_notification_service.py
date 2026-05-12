from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from beanie import PydanticObjectId

from app.modules.core.enums.type_enum import (
    ENotificationChannelFlag,
    ENotificationTunnelFlag,
)
from app.modules.core.models.ref_notification_channel.ref_notification_channel_model import (
    RefNotificationChannelModel,
)
from app.modules.core.models.ref_notification_tunnel.ref_notification_tunnel_model import (
    RefNotificationTunnelModel,
)
from app.modules.core.models.cfg_notification_config.cfg_notification_config_model import (
    CfgNotificationConfigModel,
)
from app.modules.core.models.sys_user.sys_user_model import SysUserModel
from app.modules.core.services.messaging.messaging_service import MessengingService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService


class GlobalNotificationService:
    """
    Global notification dispatcher.

    Sends notifications by CHANNEL + TUNNEL and optional ENTITY using configured
    recipients in CfgNotificationConfigModel.

    Supported channels: EMAIL, SMS, PUSH
    """

    def __init__(self, accept_language: str = DEFAULT_LANGUAGE) -> None:
        self.accept_language = accept_language
        self.messaging = MessengingService(accept_language)
        self.sms_service = SmsService()

    @staticmethod
    def _normalize_flag(flag: Union[str, ENotificationChannelFlag, ENotificationTunnelFlag]) -> str:
        return flag.value if hasattr(flag, "value") else str(flag)

    @staticmethod
    def _to_object_id(id_str: Optional[Union[str, PydanticObjectId]]) -> Optional[PydanticObjectId]:
        if not id_str:
            return None
        if isinstance(id_str, PydanticObjectId):
            return id_str
        try:
            return PydanticObjectId(str(id_str))
        except Exception:
            return None

    async def _resolve_channel_and_tunnel(
        self,
        channel_flag: Union[str, ENotificationChannelFlag],
        tunnel_flag: Union[str, ENotificationTunnelFlag],
    ) -> Dict[str, Any]:
        channel_flag_val = self._normalize_flag(channel_flag)
        tunnel_flag_val = self._normalize_flag(tunnel_flag)

        channel = await RefNotificationChannelModel.find_one(
            RefNotificationChannelModel.flag == channel_flag_val
        )
        tunnel = await RefNotificationTunnelModel.find_one(
            RefNotificationTunnelModel.flag == tunnel_flag_val
        )

        return {"channel": channel, "tunnel": tunnel}

    async def _load_recipients_from_config(
        self,
        channel_id: Optional[PydanticObjectId],
        tunnel_id: Optional[PydanticObjectId],
        entity_id: Optional[Union[str, PydanticObjectId]] = None,
    ) -> List[CfgNotificationConfigModel]:
        if not channel_id or not tunnel_id:
            return []
        query: Dict[str, Any] = {
            "ref_notification_channel_id": channel_id,
            "ref_notification_tunnel_id": tunnel_id,
        }
        ent = self._to_object_id(entity_id)
        if ent:
            query["ref_entity_id"] = ent
        return await CfgNotificationConfigModel.find(query).to_list()

    async def send_by_flags(
        self,
        *,
        channel_flag: Union[str, ENotificationChannelFlag],
        tunnel_flag: Union[str, ENotificationTunnelFlag],
        entity_id: Optional[Union[str, PydanticObjectId]] = None,
        title: str,
        message: str,
        targeted_user_ids: Optional[Sequence[Union[str, PydanticObjectId]]] = None,
        fallback_email: Optional[str] = None,
        fallback_phone: Optional[str] = None,
        push_data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch notification to recipients based on configured CHANNEL+TUNNEL (+ENTITY optional).

        If no config recipients are found, will use provided fallbacks/targeted_user_ids when possible.
        """
        try:
            resolved = await self._resolve_channel_and_tunnel(channel_flag, tunnel_flag)
            channel = resolved.get("channel")
            tunnel = resolved.get("tunnel")

            if not channel or not tunnel:
                return {
                    "status": "error",
                    "message": "Channel or Tunnel not found for provided flags",
                    "channel": self._normalize_flag(channel_flag),
                    "tunnel": self._normalize_flag(tunnel_flag),
                }

            # Collect recipients from config
            configs = await self._load_recipients_from_config(channel.id, tunnel.id, entity_id)

            emails: List[str] = []
            phones: List[str] = []
            users: List[SysUserModel] = []

            for cfg in configs:
                # sys_user based
                if cfg.sys_user_id:
                    user = await SysUserModel.get(cfg.sys_user_id)
                    if user:
                        users.append(user)
                        if user.email:
                            emails.append(user.email)
                        if user.phone_number:
                            phones.append(user.phone_number)
                # direct contacts
                if cfg.email:
                    emails.append(cfg.email)
                if cfg.phone_number:
                    phones.append(cfg.phone_number)

            # Fallbacks if no config match
            if not configs and targeted_user_ids:
                for uid in targeted_user_ids:
                    u = await SysUserModel.get(self._to_object_id(uid))
                    if u:
                        users.append(u)
                        if u.email:
                            emails.append(u.email)
                        if u.phone_number:
                            phones.append(u.phone_number)
            if not configs and fallback_email:
                emails.append(fallback_email)
            if not configs and fallback_phone:
                phones.append(fallback_phone)

            # Deduplicate
            emails = list(dict.fromkeys([e for e in emails if e]))
            phones = list(dict.fromkeys([p for p in phones if p]))
            users = list({str(u.id): u for u in users if u}.values())

            channel_flag_val = self._normalize_flag(channel_flag)
            dispatch_results: Dict[str, Any] = {"channel": channel_flag_val, "tunnel": self._normalize_flag(tunnel_flag)}

            if channel_flag_val == ENotificationChannelFlag.EMAIL.value:
                if emails:
                    send_result = await self.messaging.send_email_to_users(
                        emails=emails,
                        subject=title,
                        body=message,
                        is_html=False,
                    )
                    dispatch_results["emails_sent"] = send_result
                else:
                    dispatch_results["emails_sent"] = {"status": "skipped", "reason": "no email recipients"}

            elif channel_flag_val == ENotificationChannelFlag.SMS.value:
                sms_results: List[Dict[str, Any]] = []
                for phone in phones:
                    try:
                        await self.sms_service.send_sms_httpx_async(phone, message)
                        sms_results.append({"phone": phone, "status": True})
                    except Exception as e:
                        DebugService.app_debug_print(f"SMS send failed to {phone}: {e}", True)
                        sms_results.append({"phone": phone, "status": False, "error": str(e)})
                dispatch_results["sms_sent"] = sms_results

            elif channel_flag_val == ENotificationChannelFlag.PUSH.value:
                if users:
                    # Convert users to dicts for push manager
                    results = []
                    for u in users:
                        u_data = await u.get_default_formated_data(self.accept_language)
                        r = await self.messaging.send_push_notification_to_user(
                            user_data=u_data,
                            title=title,
                            body=message,
                            data=push_data or {},
                            platforms=None,
                        )
                        results.append({"user_id": str(u.id), **r})
                    dispatch_results["push_sent"] = results
                else:
                    dispatch_results["push_sent"] = {"status": "skipped", "reason": "no users with tokens"}

            else:
                dispatch_results["status"] = "error"
                dispatch_results["message"] = f"Unsupported channel: {channel_flag_val}"
                return dispatch_results

            dispatch_results["status"] = "success"
            dispatch_results["recipients"] = {
                "emails": emails,
                "phones": phones,
                "user_ids": [str(u.id) for u in users],
            }
            dispatch_results["config_count"] = len(configs)
            return dispatch_results

        except Exception as e:
            DebugService.app_debug_print(f"Global notification dispatch error: {e}", True)
            return {"status": "error", "message": str(e)}
    
    async def send_notifications_by_flags(
        self,
        *,
        channel_flag: Union[str, ENotificationChannelFlag],
        tunnel_flag: Union[str, ENotificationTunnelFlag],
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        title: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Dispatch notification to recipients based on configured CHANNEL+TUNNEL (+ENTITY optional).

        If no config recipients are found, will use provided fallbacks/targeted_user_ids when possible.
        """
        try:
            DebugService.app_debug_print(
                f"[send_notifications_by_flags] ENTER channel_flag={channel_flag}, tunnel_flag={tunnel_flag}, email={email}, phone={phone_number}, title={title}",
                False,
            )
            resolved = await self._resolve_channel_and_tunnel(channel_flag, tunnel_flag)
            channel = resolved.get("channel")
            tunnel = resolved.get("tunnel")

            DebugService.app_debug_print(
                f"[send_notifications_by_flags] Resolved channel={getattr(channel,'name',None)}({getattr(channel,'id',None)}), tunnel={getattr(tunnel,'name',None)}({getattr(tunnel,'id',None)})",
                False,
            )

            if not channel or not tunnel:
                DebugService.app_debug_print("[send_notifications_by_flags] ERROR: Channel or Tunnel not found for provided flags", True)
                return {
                    "status": "error",
                    "message": "Channel or Tunnel not found for provided flags",
                    "channel": self._normalize_flag(channel_flag),
                    "tunnel": self._normalize_flag(tunnel_flag),
                }

            emails: List[str] = []
            phones: List[str] = []

            # Deduplicate
            emails = [email] if email else []
            phones = [phone_number] if phone_number else []

            DebugService.app_debug_print(f"[send_notifications_by_flags] Recipients emails={emails}, phones={phones}", False)

            channel_flag_val = self._normalize_flag(channel_flag)
            dispatch_results: Dict[str, Any] = {"channel": channel_flag_val, "tunnel": self._normalize_flag(tunnel_flag)}

            if channel_flag_val == ENotificationChannelFlag.EMAIL.value:
                if emails:
                    DebugService.app_debug_print(
                        f"[send_notifications_by_flags] Sending EMAIL to {emails} subject='{title}' len={len(message) if message is not None else 0}",
                        False,
                    )
                    send_result = await self.messaging.send_email_to_users(
                        emails=emails,
                        subject=title,
                        body=message,
                        is_html=False,
                    )
                    DebugService.app_debug_print(f"[send_notifications_by_flags] Email send result: {send_result}", False)
                    dispatch_results["emails_sent"] = send_result
                else:
                    DebugService.app_debug_print("[send_notifications_by_flags] Skipped email send: no email recipients", False)
                    dispatch_results["emails_sent"] = {"status": "skipped", "reason": "no email recipients"}

            elif channel_flag_val == ENotificationChannelFlag.SMS.value:
                sms_results: List[Dict[str, Any]] = []
                for phone in phones:
                    try:
                        DebugService.app_debug_print(f"[send_notifications_by_flags] Sending SMS to {phone}", False)
                        await self.sms_service.send_sms_httpx_async(phone, message)
                        sms_results.append({"phone": phone, "status": True})
                        DebugService.app_debug_print(f"[send_notifications_by_flags] SMS sent to {phone}", False)
                    except Exception as e:
                        DebugService.app_debug_print(f"SMS send failed to {phone}: {e}", True)
                        sms_results.append({"phone": phone, "status": False, "error": str(e)})
                dispatch_results["sms_sent"] = sms_results

            else:
                DebugService.app_debug_print(f"[send_notifications_by_flags] ERROR: Unsupported channel: {channel_flag_val}", True)
                dispatch_results["status"] = "error"
                dispatch_results["message"] = f"Unsupported channel: {channel_flag_val}"
                return dispatch_results

            dispatch_results["status"] = "success"
            dispatch_results["recipients"] = {
                "emails": emails,
                "phones": phones,
            }
            DebugService.app_debug_print(f"[send_notifications_by_flags] EXIT results={dispatch_results}", False)
            return dispatch_results

        except Exception as e:
            DebugService.app_debug_print(f"Global notification dispatch error: {e}", True)
            return {"status": "error", "message": str(e)}

    async def send_tunnel_channel_messages(
        self,
        *,
        channel_flag: Union[str, ENotificationChannelFlag],
        tunnel_flag: Union[str, ENotificationTunnelFlag],
        message: str,
        entity_id: Optional[Union[str, PydanticObjectId]] = None,
        title_trealing: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch notification to recipients based on configured CHANNEL+TUNNEL (+ENTITY optional) using EMAIL/SMS.

        If no config recipients are found, will use provided fallbacks/targeted_user_ids when possible. (EMAIL/SMS)
        """
        try:
            # generic service
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.models.mapping_keys import CollectionKey
            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING

            DebugService.app_debug_print(
                f"[send_tunnel_channel_messages] ENTER channel_flag={channel_flag}, tunnel_flag={tunnel_flag}, entity_id={entity_id}, message_len={len(message) if message is not None else 0}",
                False,
            )

            generic_service = GenericService(self.accept_language)
            # CollectionKey.CFG_NOTIFICATION_CONFIG
            resolved = await self._resolve_channel_and_tunnel(channel_flag, tunnel_flag)
            channel = resolved.get("channel")
            tunnel = resolved.get("tunnel")

            DebugService.app_debug_print(
                f"[send_tunnel_channel_messages] Resolved channel={getattr(channel,'name',None)}({getattr(channel,'id',None)}), tunnel={getattr(tunnel,'name',None)}({getattr(tunnel,'id',None)})",
                False,
            )

            query = {
                "filter__ref_notification_channel_id": str(channel.id),
                "filter__ref_notification_tunnel_id": str(tunnel.id),
                "filter__ref_entity_id": str(entity_id) if entity_id else None,
            }
            DebugService.app_debug_print(f"[send_tunnel_channel_messages] Fetching cfg with query={query}", False)

            cfg_notifications = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_NOTIFICATION_CONFIG,
                all_data=True,
                query=query,
            )

            DebugService.app_debug_print(
                f"[send_tunnel_channel_messages] Found {len(cfg_notifications)} configs",
                False,
            )

            # LOOP THROUGHT cfg_notifications TO SEND CORRESPONDING MESSAGES (EMAIL/SMS) TO RECIPIENTS
            for idx, cfg in enumerate(cfg_notifications, start=1):
                message_title =  f"{str(tunnel.name)} - ({title_trealing})"
                message_body = message
                DebugService.app_debug_print(
                    f"[send_tunnel_channel_messages] Dispatching [{idx}/{len(cfg_notifications)}] email={cfg.get('email')} phone={cfg.get('phone_number')}",
                    False,
                )
                res = await self.send_notifications_by_flags(
                    channel_flag=channel_flag,
                    tunnel_flag=tunnel_flag,
                    email=cfg['email'],
                    phone_number=cfg['phone_number'],
                    title=message_title,
                    message=message_body,
                )
                DebugService.app_debug_print(f"[send_tunnel_channel_messages] Result for [{idx}]: {res}", False)
            DebugService.app_debug_print("[send_tunnel_channel_messages] EXIT success", False)
            return {"status": "success", "message": "Messages sent"}

        except Exception as e:
            DebugService.app_debug_print(f"Global notification dispatch error: {e}", True)
            return {"status": "error", "message": str(e)}



    async def send_tunner_channel_mesages(
        self,
        *,
        channel_flag: Union[str, ENotificationChannelFlag],
        tunnel_flag: Union[str, ENotificationTunnelFlag],
        message: str,
        entity_id: Optional[Union[str, PydanticObjectId]] = None,
        title_trealing: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch notification to recipients based on configured CHANNEL+TUNNEL (+ENTITY optional).

        If no config recipients are found, will use provided fallbacks/targeted_user_ids when possible.
        """
        try:
            # generic service
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.models.mapping_keys import CollectionKey
            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING

            DebugService.app_debug_print(
                f"[send_tunner_channel_mesages] ENTER channel_flag={channel_flag}, tunnel_flag={tunnel_flag}, entity_id={entity_id}, message_len={len(message) if message is not None else 0}",
                False,
            )

            generic_service = GenericService(self.accept_language)
            # CollectionKey.CFG_NOTIFICATION_CONFIG
            resolved = await self._resolve_channel_and_tunnel(channel_flag, tunnel_flag)
            channel = resolved.get("channel")
            tunnel = resolved.get("tunnel")

            DebugService.app_debug_print(
                f"[send_tunner_channel_mesages] Resolved channel={getattr(channel,'name',None)}({getattr(channel,'id',None)}), tunnel={getattr(tunnel,'name',None)}({getattr(tunnel,'id',None)})",
                False,
            )

            query = {
                "filter__ref_notification_channel_id": str(channel.id),
                "filter__ref_notification_tunnel_id": str(tunnel.id),
                "filter__ref_entity_id": str(entity_id) if entity_id else None,
            }
            DebugService.app_debug_print(f"[send_tunner_channel_mesages] Fetching cfg with query={query}", False)

            cfg_notifications = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_NOTIFICATION_CONFIG,
                all_data=True,
                query=query,
            )

            DebugService.app_debug_print(
                f"[send_tunner_channel_mesages] Found {len(cfg_notifications)} configs",
                False,
            )

            # LOOP THROUGHT cfg_notifications TO SEND CORRESPONDING MESSAGES
            for idx, cfg in enumerate(cfg_notifications, start=1):
                message_title =  f"{str(tunnel.name)} - ({title_trealing})"
                message_body = message
                DebugService.app_debug_print(
                    f"[send_tunner_channel_mesages] Dispatching [{idx}/{len(cfg_notifications)}] email={cfg.get('email')} phone={cfg.get('phone_number')}",
                    False,
                )
                res = await self.send_notifications_by_flags(
                    channel_flag=channel_flag,
                    tunnel_flag=tunnel_flag,
                    email=cfg['email'],
                    phone_number=cfg['phone_number'],
                    title=message_title,
                    message=message_body,
                )
                DebugService.app_debug_print(f"[send_tunner_channel_mesages] Result for [{idx}]: {res}", False)
            DebugService.app_debug_print("[send_tunner_channel_mesages] EXIT success", False)
            return {"status": "success", "message": "Messages sent"}

        except Exception as e:
            DebugService.app_debug_print(f"Global notification dispatch error: {e}", True)
            return {"status": "error", "message": str(e)}
