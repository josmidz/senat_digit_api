import re
import httpx
import json

from app.modules.core.configs.config import settings
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import EncryptionService


class SvgIconService:
    @staticmethod
    def _sanitize_component(value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", str(value or "").strip())
        return sanitized.strip("._")

    @classmethod
    def _build_base_dir_from_path(cls, path_value: str) -> str:
        raw_parts = [part.strip() for part in str(path_value or "").split("/")]
        app_or_menu_path = [part for part in raw_parts[1:] if part]
        safe_parts = [cls._sanitize_component(part) for part in app_or_menu_path]
        safe_parts = [part for part in safe_parts if part]

        path_suffix = "___".join(safe_parts)
        configured_base_dir = str(
            getattr(settings, "SENAT_DIGIT_APPS_ICONS_SYSTEM_BASE_DIR", "") or ""
        ).strip()

        if not configured_base_dir:
            return path_suffix
        if not path_suffix:
            return configured_base_dir
        if configured_base_dir.endswith("___"):
            return f"{configured_base_dir}{path_suffix}"
        return f"{configured_base_dir}___{path_suffix}"

    @classmethod
    async def upload_svg_icon(
        cls,
        svg_icon: str,
        path_value: str,
        icon_flag: str,
        api_consumer_flag: str,
    ) -> bool:
        try:
            if not str(svg_icon or "").strip():
                return False

            file_system_url = str(settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL or "").strip()
            if not file_system_url:
                DebugService.app_debug_print(
                    "SVG ICON UPLOAD SKIPPED: SENAT_DIGIT_APPS_FILE_SYSTEM_URL missing",
                    True,
                )
                return False

            safe_icon_flag = cls._sanitize_component(icon_flag)
            safe_api_consumer_flag = cls._sanitize_component(api_consumer_flag)
            if not safe_icon_flag or not safe_api_consumer_flag:
                DebugService.app_debug_print(
                    "SVG ICON UPLOAD SKIPPED: invalid icon_flag or api_consumer_flag",
                    True,
                )
                return False

            base_dir = cls._build_base_dir_from_path(path_value)
            file_name = f"{safe_icon_flag}___{safe_api_consumer_flag}.svg"
            endpoint = f"{file_system_url}/files/upload-svg"

            headers = {
                "authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}",
            }
            data = {
                "file_name": file_name,
                "api_consumer_flag": safe_api_consumer_flag,
                "svg_content": str(svg_icon),
            }
            params = {"base_dir": base_dir} if base_dir else {}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    data=data,
                    params=params,
                    headers=headers,
                )

            if response.status_code not in (200, 201):
                DebugService.app_debug_print(
                    f"SVG ICON UPLOAD FAILED [{response.status_code}] file={file_name} base_dir={base_dir}",
                    True,
                )
                return False

            return True
        except Exception as exc:
            DebugService.app_debug_print(f"SVG ICON UPLOAD ERROR: {exc}", True)
            return False

    @classmethod
    def build_svg_icon_file_server_url(
        cls,
        menu_or_app_path: str,
        menu_or_app_flag: str,
        api_consumer_flag: str,
    ) -> str:
        safe_path = str(menu_or_app_path or "").strip()
        safe_flag = cls._sanitize_component(menu_or_app_flag)
        safe_api_consumer_flag = cls._sanitize_component(api_consumer_flag)

        payload = {
            "menu_or_app_path": safe_path,
            "menu_or_app_flag": safe_flag,
            "api_consumer_flag": safe_api_consumer_flag,
        }
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
        encrypted_query = EncryptionService.encrypt_data_url_safe(payload_json)
        # test_dencrypted_data = EncryptionService.decrypt_data_url_safe(encrypted_query)
        # DebugService.app_debug_print(f"💾 ] 💾] 💾  encrypted_query: {encrypted_query}", True)
        # DebugService.app_debug_print(f" ✅  ✅ ✅ ✅ test_dencrypted_data: {test_dencrypted_data}", True)

        base_url = str(settings.MAIN_APP_BASE_URL or "").strip().rstrip("/")
        if not base_url:
            return f"/static/files/view-svg?q={encrypted_query}"
        return f"{base_url}/static/files/view-svg?q={encrypted_query}"
