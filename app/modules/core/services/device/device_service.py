

from typing import Any, Dict, Optional
import json
import re
import requests
from fastapi import Request
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import FormatedOutPut, OutputDataType

from app.modules.core.services.redis.redis_service import AppRedisService


class DeviceService:
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language=accept_language)

    async def device_info_from_hashed_id(self,device_hashed_id:str,accept_language:str = DEFAULT_LANGUAGE,output_data_type:OutputDataType=OutputDataType.DEFAULT.value)-> Optional[Dict[str, Any]]:
        try:
            
            # DEVICE CHECKING 
            user_device_query = {
                "filter__device_id_str": device_hashed_id,
            }
            # GET USER DEVICE INFO
            user_device_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=output_data_type,
                query=user_device_query,
                accept_language=accept_language
            )
            return user_device_info
        
        except Exception as e:
            print(f"Error logged in : {e}")
            return None
    async def device_info_from_db_and_user_id(self,device_hashed_id:str,sys_user_id:str,accept_language:str = DEFAULT_LANGUAGE,output_data_type:OutputDataType=OutputDataType.DEFAULT.value)-> Optional[Dict[str, Any]]:
        try:
            from app.modules.auth.models.cfg_user_device.cfg_user_device_model import CfgUserDeviceModel
            # DEVICE CHECKING 
            user_device_query = {
                "filter__device_id_str": device_hashed_id,
                "filter__sys_user_id": str(sys_user_id),
            }
            # GET USER DEVICE INFO
            user_device_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=output_data_type,
                query=user_device_query,
                accept_language=accept_language
            )
            formated_info = None
            if user_device_info:
                formated_info = await CfgUserDeviceModel(**user_device_info).get_formated_data(accept_language,FormatedOutPut.MINIMAL)
                return formated_info
            return user_device_info
        
        except Exception as e:
            print(f"Error logged in : {e}")
            return None
        
    async def devices_list_from_hashed_id(self,device_hashed_id:str,accept_language:str = DEFAULT_LANGUAGE,output_data_type:OutputDataType=OutputDataType.DEFAULT.value)-> Optional[Dict[str, Any]]:
        try:
            
            # DEVICE CHECKING 
            user_device_query = {
                "filter__device_id_str": device_hashed_id,
            }
            # GET USER DEVICE INFO
            user_device_list = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=output_data_type,
                all_data=True,
                query=user_device_query,
                accept_language=accept_language
            )
            return user_device_list
        
        except Exception as e:
            print(f"Error logged in : {e}")
            return []
        
    async def create_new_user_device(
        self,
        sys_user_id:str,
        device_id_str:str,
        sys_organization_id:str,
        device_info:any,accept_language:str = DEFAULT_LANGUAGE)-> Optional[Dict[str, Any]]:
        try:
            user_device_data = {
                "sys_user_id":sys_user_id,
                "device_id_str":device_id_str,
                "device_info":device_info,
                "sys_organization_id":sys_organization_id
            }
            user_device_info = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                filter_data={
                    "sys_user_id": user_device_data["sys_user_id"],
                    "device_id_str": user_device_data["device_id_str"],
                    "sys_organization_id": user_device_data["sys_organization_id"]
                },
                update_data=user_device_data
            )
            print("user_device_info has been upserted.", user_device_info) 
            return user_device_info
        
        except Exception as e:
            print(f"Error logged in : {e}")
            # Get translated message
            return None
        
    async def create_or_get_user_config(
        self,
        sys_user_id:str,
        accept_language:str = DEFAULT_LANGUAGE)-> Optional[Dict[str, Any]]:
        try:

            # GET REF LANGUAGE FROM ACCEPT LANGUAGE
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query={
                    "filter__short_code":str(accept_language).strip()
                }
            )
            if not language:
                language = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_LANGUAGE.value,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language= self.accept_language,
                    query={
                        "filter__short_code":'fr'
                    }
                )
            user_device_allowed_count_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query={
                    "filter__sys_user_id":sys_user_id
                }
            )
            user_device_allowed_count = 0
            if user_device_allowed_count_info:
                user_device_allowed_count = user_device_allowed_count_info['allowed_device_count']
            user_config_data = {
                "sys_user_id":sys_user_id,
                "allowed_device_count":user_device_allowed_count,
                "dark_mode":False,
                "sys_app_theme_id":None,
                "ref_language_id":language['id'],
            }
            user_config_info = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_CONFIG,
                filter_data={
                    "sys_user_id": user_config_data["sys_user_id"],
                },
                update_data=user_config_data
            )
            # print("user_config_info has been upserted.", user_config_info)
            return user_config_info

        except Exception as e:
            # Print + log with full stack so the silent NO_EXISTING_USER_CONFIG
            # 401 stops being a black box. Common root causes:
            #   - ref_language for `fr` not seeded → language['id'] crashes
            #   - Mongo unreachable at the connection pool
            #   - Validation error on the cfg_user_config payload
            import logging, traceback
            logging.getLogger("senat_digit.device_service").exception(
                "create_or_get_user_config failed for sys_user_id=%s: %s",
                sys_user_id,
                e,
            )
            print(f"[device_service] create_or_get_user_config error: {e}")
            print(traceback.format_exc())
            return None

    @staticmethod
    async def get_hashed_device_id(request: Request) -> str:
        from app.modules.core.services.debug.debug_service import DebugService
        # Extract the user-agent and device_id from headers
        user_agent = request.headers.get('user-agent', '')
        DebugService.app_debug_print(f"user_agent : {user_agent}")
        device_id = request.headers.get('device_id', '')
        print(f"device_id : {device_id}")
        mobile_device_infos = request.headers.get('mobile_device_infos', None)
        if mobile_device_infos:
            try:
                mobile_device_infos = json.loads(mobile_device_infos)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing mobile_device_infos: {e}")
                mobile_device_infos = {}
                
        if isinstance(mobile_device_infos, dict) and mobile_device_infos.get('device_id',None):
            device_identifier = mobile_device_infos.get('device_id',None)
        else:
            device_identifier = None
        # Determine the source (mobile device or browser user-agent)
        if device_identifier:
            device_identifier = device_identifier
        elif user_agent.lower() == "mobile" and device_id:
            device_identifier = device_id  # Mobile device ID
        elif device_id:
            device_identifier = device_id  # Mobile device ID
        else:
            device_identifier = user_agent  # Browser user-agent

        

        # Hash the device identifier
        hashed_device_id = HashService.generate_base64_hash(device_identifier)
        DebugService.app_debug_print(f" hashed_device_id : {hashed_device_id}")
        return hashed_device_id
        
    @staticmethod
    def get_real_ip_address(request: Request) -> str:
        """
        Extracts the real IP address from the request, considering proxies.

        For Nginx:
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_set_header X-Real-IP $remote_addr;
        """
        # Get the real IP address from the "x-forwarded-for" header
        forwarded_ip = request.headers.get("x-forwarded-for")
        
        # If "x-forwarded-for" is present, extract the first IP address
        if forwarded_ip:
            return forwarded_ip.split(",")[0].strip()
        
        # Fallback to the client's host if "x-forwarded-for" is not present
        return request.client.host

    @staticmethod
    async def get_location_from_ip_secure(request: Request) -> dict:
        """
        Get detailed location information (country, city, region, etc.) based on IP address.
        """
        ip_address = DeviceService.get_real_ip_address(request)
        print("ip_address :", ip_address)
        
        # Check Redis cache for location data
        cached_location = await AppRedisService.get_str_redis_value(ip_address)
        print("cached_location :", cached_location)
        
        if cached_location:
            print(f"Cache hit for IP: {ip_address}")
            return json.loads(cached_location)  # Convert JSON string to dict
        # private_ip_ranges = [
        #     "192.168.",  # Local network
        #     "10.",  # Private network
        #     "127.0.0.",  # Loopback
        #     "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
        # ]
        # if any(ip_address.startswith(prefix) for prefix in private_ip_ranges):

        try:
            
            if ip_address.startswith(("192.168.", "10.", "127.", "172.")):
                return {
                    "ip": ip_address,
                    "city": "Local Network",
                    "region": "N/A",
                    "country_name": "N/A",
                    "latitude": None,
                    "longitude": None,
                    "timezone": "N/A",
                    "calling_code": "N/A",
                    "currency": "N/A",
                    "languages": "N/A",
                    "asn": "N/A",
                    "org": "N/A",
                    "location": "Internal Network",
                    "is_private": True
                }
            
            # Perform API request
            response = requests.get(f"https://ipapi.co/{ip_address}/json/")
            print(f"response: {response}")

            if response.status_code == 200:
                data = response.json()
                location_data = {
                    "ip": response.json().get("ip"),
                    "city": response.json().get("city"),
                    "region": response.json().get("region"),
                    "country_name": response.json().get("country_name"),
                    "latitude": response.json().get("latitude"),
                    "longitude": response.json().get("longitude"),
                    "timezone": response.json().get("timezone"),
                    "org": response.json().get("org"),
                    "country_code": response.json().get("country"),
                    "calling_code": response.json().get("country_calling_code"),
                    "currency": response.json().get("currency"),
                    "languages": response.json().get("languages")
                }

                # Cache the location data in Redis
                await AppRedisService.set_redis_value(key=ip_address,value= json.dumps(location_data),expiry=86400)
                print(f"Location data cached for IP: {ip_address}")

                return location_data
            else:
                return {"error": f"Failed to fetch location data: {response.status_code}"}

        except Exception as e:
            return {"error": str(e)}
        
    @staticmethod
    def _parse_user_agent(user_agent: str) -> Dict[str, Any]:
        """Parse a user-agent string and return a detailed breakdown."""
        result: Dict[str, Any] = {
            "browser_name": "Unknown",
            "browser_version": "Unknown",
            "rendering_engine": "Unknown",
            "os_name": "Unknown",
            "os_version": "Unknown",
            "platform_type": "Unknown",
            "architecture": "Unknown",
            "device_type": "desktop",
            "device_name": "Unknown Browser",
            "manufacturer": "Unknown",
            "model": "Unknown",
            "is_bot": False,
        }

        if not user_agent or user_agent == "Unknown":
            return result

        ua = user_agent
        ua_lower = ua.lower()

        # ── Bot detection ──
        bot_patterns = ["bot", "crawl", "spider", "slurp", "mediapartners", "feedfetcher", "lighthouse"]
        if any(bp in ua_lower for bp in bot_patterns):
            result["is_bot"] = True
            result["device_type"] = "bot"
            bot_match = re.search(r"([\w-]+bot|Googlebot|Bingbot|Slurp|DuckDuckBot|Baiduspider|YandexBot|Lighthouse)[/\s]?([\d.]*)", ua, re.IGNORECASE)
            if bot_match:
                result["browser_name"] = bot_match.group(1)
                result["browser_version"] = bot_match.group(2) or "Unknown"
                result["device_name"] = bot_match.group(1)
            return result

        # ── Browser detection (order matters: check specific before generic) ──
        browser_rules = [
            (r"OPR/([\d.]+)", "Opera"),
            (r"Opera(?:.*Version)?/([\d.]+)", "Opera"),
            (r"Edg(?:e|A|iOS)?/([\d.]+)", "Microsoft Edge"),
            (r"SamsungBrowser/([\d.]+)", "Samsung Internet"),
            (r"UCBrowser/([\d.]+)", "UC Browser"),
            (r"Brave(?:/([\d.]+))?", "Brave"),
            (r"Vivaldi/([\d.]+)", "Vivaldi"),
            (r"YaBrowser/([\d.]+)", "Yandex Browser"),
            (r"Firefox/([\d.]+)", "Mozilla Firefox"),
            (r"FxiOS/([\d.]+)", "Firefox iOS"),
            (r"CriOS/([\d.]+)", "Chrome iOS"),
            (r"Chrome/([\d.]+)", "Google Chrome"),
            (r"Version/([\d.]+).*Safari", "Safari"),
            (r"Safari/([\d.]+)", "Safari"),
            (r"Dart/([\d.]+)", "Flutter/Dart App"),
            (r"PostmanRuntime/([\d.]+)", "Postman"),
            (r"Insomnia/([\d.]+)", "Insomnia"),
            (r"python-requests/([\d.]+)", "Python Requests"),
            (r"curl/([\d.]+)", "cURL"),
            (r"httpx/([\d.]+)", "HTTPX"),
        ]
        for pattern, name in browser_rules:
            m = re.search(pattern, ua)
            if m:
                result["browser_name"] = name
                result["browser_version"] = m.group(1) if m.group(1) else "Unknown"
                break

        # ── Rendering engine ──
        engine_rules = [
            (r"AppleWebKit/([\d.]+)", "WebKit"),
            (r"Gecko/([\d.]+)", "Gecko"),
            (r"Trident/([\d.]+)", "Trident"),
            (r"Presto/([\d.]+)", "Presto"),
        ]
        for pattern, name in engine_rules:
            m = re.search(pattern, ua)
            if m:
                result["rendering_engine"] = f"{name}/{m.group(1)}"
                break

        # ── OS detection ──
        os_rules = [
            (r"Windows NT ([\d.]+)", "Windows", {
                "10.0": "10/11", "6.3": "8.1", "6.2": "8",
                "6.1": "7", "6.0": "Vista", "5.1": "XP",
            }),
            (r"Mac OS X ([\d_.]+)", "macOS", None),
            (r"iPhone OS ([\d_]+)", "iOS", None),
            (r"iPad.*OS ([\d_]+)", "iPadOS", None),
            (r"Android ([\d.]+)", "Android", None),
            (r"CrOS [\w]+ ([\d.]+)", "Chrome OS", None),
            (r"Linux", "Linux", None),
        ]
        for pattern, name, version_map in os_rules:
            m = re.search(pattern, ua)
            if m:
                result["os_name"] = name
                if m.lastindex and m.lastindex >= 1:
                    raw_version = m.group(1).replace("_", ".")
                    if version_map and raw_version in version_map:
                        result["os_version"] = version_map[raw_version]
                    else:
                        result["os_version"] = raw_version
                break

        # ── Architecture ──
        if "x86_64" in ua_lower or "x64" in ua_lower or "win64" in ua_lower or "amd64" in ua_lower:
            result["architecture"] = "x86_64"
        elif "arm64" in ua_lower or "aarch64" in ua_lower:
            result["architecture"] = "ARM64"
        elif "armv7" in ua_lower or "arm" in ua_lower:
            result["architecture"] = "ARM"
        elif "x86" in ua_lower or "i686" in ua_lower or "i386" in ua_lower:
            result["architecture"] = "x86"

        # ── Device type (mobile / tablet / desktop) ──
        tablet_indicators = ["ipad", "tablet", "sm-t", "sm-x", "tab"]
        mobile_indicators = ["mobile", "iphone", "android", "ipod", "phone", "bb10", "opera mini", "opera mobi"]
        if any(t in ua_lower for t in tablet_indicators):
            result["device_type"] = "tablet"
        elif any(m in ua_lower for m in mobile_indicators):
            result["device_type"] = "mobile"
        else:
            result["device_type"] = "desktop"

        # ── Platform type ──
        result["platform_type"] = result["os_name"] if result["os_name"] != "Unknown" else DeviceService._extract_platform_from_user_agent(ua)

        # ── Manufacturer & model (best-effort) ──
        if result["os_name"] in ("iOS", "iPadOS"):
            result["manufacturer"] = "Apple"
            idevice = re.search(r"(iPhone|iPad|iPod)\d*[,\d]*", ua)
            if idevice:
                result["model"] = idevice.group(0)
        elif result["os_name"] == "macOS":
            result["manufacturer"] = "Apple"
            mac_model = re.search(r"Macintosh;\s*([\w\s]+?)(?:\)|;)", ua)
            if mac_model:
                result["model"] = mac_model.group(1).strip()
        elif result["os_name"] == "Android":
            android_model = re.search(r";\s*([^;)]+?)\s*(?:Build|MIUI|/)", ua)
            if android_model:
                model_str = android_model.group(1).strip()
                result["model"] = model_str
                first_word = model_str.split()[0] if model_str.split() else ""
                known_brands = {
                    "SM": "Samsung", "GT": "Samsung", "SCH": "Samsung",
                    "Pixel": "Google", "Nexus": "Google",
                    "LG": "LG", "LM": "LG",
                    "Mi": "Xiaomi", "Redmi": "Xiaomi", "POCO": "Xiaomi", "M2": "Xiaomi",
                    "HUAWEI": "Huawei", "VOG": "Huawei", "ELE": "Huawei",
                    "ONEPLUS": "OnePlus", "IN": "OnePlus",
                    "moto": "Motorola", "XT": "Motorola",
                    "ASUS": "ASUS", "Nokia": "Nokia", "Sony": "Sony",
                    "RMX": "Realme", "CPH": "OPPO", "V": "Vivo",
                    "TECNO": "TECNO", "INFINIX": "Infinix", "itel": "itel",
                }
                for prefix, brand in known_brands.items():
                    if first_word.upper().startswith(prefix.upper()):
                        result["manufacturer"] = brand
                        break

        # ── Device name (human-readable summary) ──
        browser_label = result["browser_name"]
        if result["browser_version"] != "Unknown":
            browser_label += f" {result['browser_version']}"
        os_label = result["os_name"]
        if result["os_version"] != "Unknown":
            os_label += f" {result['os_version']}"
        result["device_name"] = f"{browser_label} on {os_label}"

        return result

    @staticmethod
    async def get_device_info(request: Request) -> Dict[str, str]:
        """
        Retrieve the IP address, user-agent, and other device-related information.
        
        Args:
            request (Request): The incoming FastAPI request.

        Returns:
            Dict[str, str]: Dictionary containing device-related info.
        """
        # Get the IP address from headers (using `x-forwarded-for` if behind a proxy)
        client_ip = request.client.host
        forwarded_ip = request.headers.get("x-forwarded-for", client_ip).split(",")[0].strip()

        # Extract device-related information
        mobile_device_infos_str = request.headers.get('mobile_device_infos', '')
        mobile_device_infos = {}

        # Parse mobile device info JSON string
        if mobile_device_infos_str:
            try:
                import json
                mobile_device_infos = json.loads(mobile_device_infos_str)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing mobile_device_infos: {e}")
                mobile_device_infos = {}

        # Default device info structure
        device_info = {
            "ip_address": forwarded_ip,
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "device_id": request.headers.get("device_id", "Unknown"),  # Custom header for mobile devices
            "accept_language": request.headers.get("accept-language", "Unknown"),
            "host": request.headers.get("host", "Unknown"),
            "referer": request.headers.get("referer", "Unknown"),  # Where the request is coming from
            "platform": request.headers.get("sec-ch-ua-platform", "Unknown")  # Platform info for modern browsers
        }

        if isinstance(mobile_device_infos, dict) and mobile_device_infos.get('device_id'):
            device_info = {
                "ip_address": forwarded_ip,
                "user_agent": request.headers.get("user-agent", "Unknown"),
                "device_id": mobile_device_infos.get('device_id', "Unknown"),
                "accept_language": request.headers.get("accept-language", "Unknown"),
                "host": request.headers.get("host", "Unknown"),
                "referer": request.headers.get("referer", "Unknown"),  # Where the request is coming from
                "platform": mobile_device_infos.get('manufacturer', "Unknown"), # Platform info for modern browsers

                # Enhanced mobile device information
                "manufacturer": mobile_device_infos.get('manufacturer', "Unknown"),  # e.g., "samsung"
                "model": mobile_device_infos.get('model', "Unknown"),  # e.g., "SM-N981U1"
                "version": mobile_device_infos.get('version', "Unknown"),  # Android/iOS version like "11", "15.0"
                "app_type": request.headers.get("app-type", "Unknown"),  # e.g., "mobile"
                "api_consumer": request.headers.get("api-consumer", "Unknown"),  # Encrypted consumer info
                "content_type": request.headers.get("content-type", "Unknown"),
                "accept_encoding": request.headers.get("accept-encoding", "Unknown"),

                # Additional Android-specific information
                "version_sdk": mobile_device_infos.get('version_sdk', "Unknown"),  # SDK version
                "version_codename": mobile_device_infos.get('version_codename', "Unknown"),  # Codename
                "version_incremental": mobile_device_infos.get('version_incremental', "Unknown"),  # Build incremental
                "version_security_patch": mobile_device_infos.get('version_security_patch', "Unknown"),  # Security patch
                "android_id": mobile_device_infos.get('android_id', "Unknown"),  # Android ID
                "brand": mobile_device_infos.get('brand', "Unknown"),  # Device brand
                "device": mobile_device_infos.get('device', "Unknown"),  # Device name
                "display": mobile_device_infos.get('display', "Unknown"),  # Build display
                "fingerprint": mobile_device_infos.get('fingerprint', "Unknown"),  # Build fingerprint
                "hardware": mobile_device_infos.get('hardware', "Unknown"),  # Hardware name
                "build_host": mobile_device_infos.get('host', "Unknown"),  # Build host (renamed to avoid conflict)
                "product": mobile_device_infos.get('product', "Unknown"),  # Product name
                "supported_abis": mobile_device_infos.get('supportedAbis', []),  # Supported ABIs
                "tags": mobile_device_infos.get('tags', "Unknown"),  # Build tags
                "type": mobile_device_infos.get('type', "Unknown"),  # Build type
                "is_physical_device": mobile_device_infos.get('isPhysicalDevice', True),  # Is physical device

                # iOS-specific information (when applicable)
                "system_name": mobile_device_infos.get('system_name', "Unknown"),  # iOS/iPadOS
                "localized_model": mobile_device_infos.get('localized_model', "Unknown"),  # Localized model
                "machine": mobile_device_infos.get('machine', "Unknown"),  # Hardware identifier

                # Derived device information
                "device_name": DeviceService._generate_device_name(mobile_device_infos),
                "is_mobile_app": request.headers.get("app-type") == "mobile",
                "platform_type": DeviceService._determine_platform_type(mobile_device_infos, request.headers.get("user-agent", ""))
            }
            return device_info
        else:
            # For web browsers or other clients - enhance with available info
            # For web browsers or other clients - extract detailed info from user-agent
            user_agent = request.headers.get("user-agent", "Unknown")
            ua_details = DeviceService._parse_user_agent(user_agent)

            device_info.update({
                # Browser information
                "browser_name": ua_details["browser_name"],
                "browser_version": ua_details["browser_version"],
                "rendering_engine": ua_details["rendering_engine"],

                # OS / platform information
                "os_name": ua_details["os_name"],
                "os_version": ua_details["os_version"],
                "platform_type": ua_details["platform_type"],
                "architecture": ua_details["architecture"],

                # Device classification
                "device_type": ua_details["device_type"],  # desktop, mobile, tablet, bot
                "is_mobile_app": ua_details["device_type"] in ("mobile", "tablet"),
                "is_bot": ua_details["is_bot"],
                "device_name": ua_details["device_name"],

                # Manufacturer / model (best-effort from UA)
                "manufacturer": ua_details["manufacturer"],
                "model": ua_details["model"],
                "version": ua_details["os_version"],

                # Headers
                "app_type": request.headers.get("app-type", "web"),
                "api_consumer": request.headers.get("api-consumer", "Unknown"),
                "content_type": request.headers.get("content-type", "Unknown"),
                "accept_encoding": request.headers.get("accept-encoding", "Unknown"),
            })
            return device_info

    @staticmethod
    def _extract_browser_info(user_agent: str) -> str:
        """Extract browser name and version from user agent string"""
        if not user_agent or user_agent == "Unknown":
            return "Unknown Browser"

        user_agent_lower = user_agent.lower()

        # Check for common browsers
        if "chrome" in user_agent_lower and "edg" not in user_agent_lower:
            return "Google Chrome"
        elif "firefox" in user_agent_lower:
            return "Mozilla Firefox"
        elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
            return "Safari"
        elif "edg" in user_agent_lower:
            return "Microsoft Edge"
        elif "opera" in user_agent_lower or "opr" in user_agent_lower:
            return "Opera"
        elif "dart" in user_agent_lower:
            return "Flutter/Dart App"
        else:
            return f"Unknown Browser ({user_agent[:50]}...)" if len(user_agent) > 50 else f"Unknown Browser ({user_agent})"

    @staticmethod
    def _extract_platform_from_user_agent(user_agent: str) -> str:
        """Extract platform/OS information from user agent string"""
        if not user_agent or user_agent == "Unknown":
            return "Unknown"

        user_agent_lower = user_agent.lower()

        # Check for common platforms
        if "windows" in user_agent_lower:
            return "Windows"
        elif "macintosh" in user_agent_lower or "mac os" in user_agent_lower:
            return "macOS"
        elif "linux" in user_agent_lower:
            return "Linux"
        elif "android" in user_agent_lower:
            return "Android"
        elif "iphone" in user_agent_lower or "ipad" in user_agent_lower:
            return "iOS"
        elif "dart" in user_agent_lower:
            return "Mobile App"
        else:
            return "Unknown Platform"

    @staticmethod
    def _generate_device_name(mobile_device_infos: dict) -> str:
        """Generate a user-friendly device name from device information"""
        manufacturer = mobile_device_infos.get('manufacturer', '').strip()
        model = mobile_device_infos.get('model', '').strip()
        brand = mobile_device_infos.get('brand', '').strip()
        name = mobile_device_infos.get('name', '').strip()  # iOS device name

        # For iOS devices, prefer the user-set name if available
        if name and name != 'Unknown' and mobile_device_infos.get('system_name'):
            return f"{name} ({mobile_device_infos.get('system_name', 'iOS')})"

        # For Android devices, use brand if different from manufacturer
        if manufacturer and model:
            if brand and brand != manufacturer and brand != 'Unknown':
                return f"{brand} {model}"
            else:
                return f"{manufacturer} {model}"
        elif manufacturer:
            return f"{manufacturer} Device"
        elif model:
            return model
        else:
            return "Unknown Device"

    @staticmethod
    def _determine_platform_type(mobile_device_infos: dict, user_agent: str) -> str:
        """Determine the platform type from device information"""
        # Check for iOS
        system_name = mobile_device_infos.get('system_name', '')
        if system_name in ['iOS', 'iPadOS']:
            return system_name

        # Check for Android
        if mobile_device_infos.get('version_sdk') or mobile_device_infos.get('android_id'):
            return "Android"

        # Check user agent for platform hints
        user_agent_lower = user_agent.lower()
        if "android" in user_agent_lower:
            return "Android"
        elif "iphone" in user_agent_lower or "ipad" in user_agent_lower:
            return "iOS"
        elif "dart" in user_agent_lower:
            return "Flutter App"
        elif "windows" in user_agent_lower:
            return "Windows"
        elif "macintosh" in user_agent_lower or "mac os" in user_agent_lower:
            return "macOS"
        elif "linux" in user_agent_lower:
            return "Linux"
        else:
            return "Unknown Platform"

