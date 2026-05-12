#scripts/seed.py

import asyncio
from traceback import format_exception
from typing import Any, Optional, Union
from app.db.session import init_db
from app.modules.auth.enums.common import EIconFlag, ERbacActionFlag
from app.modules.core.enums.access_level import EAccessFlag
from app.modules.auth.enums.mfa import EMfaPurpose, MFaFlag
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping import COLLECTIONS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.types.saas import CurrencyExchangeSetupScope, ESaasConfigInfoKind, ESaasConfigPurpose
from app.modules.core.enums.type_enum import AccountStatusFlag, EDataDisplayTypeFlag, EMenuChildrenDisplayFlag, EMultipleValidationStatus, ESudoActionTypeFlag, OutputDataType
from app.modules.core.utils.common.helpers import generate_label_to_flag
import nest_asyncio
from app.modules.core.seeds.core_rbac_title import CORE_RBAC_TITLE_DB
from typing import Optional, Any, Dict, List
# Prevents loop errors by allowing re-entry into the same event loop
nest_asyncio.apply()


# Seed Data
async def init_data():
    """
    Initialize the database and seed default data.
    """
    # The whole seed is wrapped in user_app_store_guard so that ANY
    # rbac_role / rbac_profile / sys_application upsert inside its body —
    # even ones that later gain invalidation hooks — does NOT trigger a
    # stale-mark that would cascade back into a rebuild during seeding
    # (infinite loop). The end-of-seed mark_static_stale() runs deliberately
    # outside the guard.
    from app.modules.core.services.user_app_store.user_app_store_guard import (
        user_app_store_guard,
    )

    await init_db()
    async with user_app_store_guard():
        await create_default_icons()
        await create_default_countries()
        await create_budget_years()
        await create_languages()
        await create_rbac_titles()

        # await create_accesses()

        await create_default_documents()
        await create_default_fields_of_study()
        await create_default_marital_statuses()
        await create_default_colors()
        await create_default_blood_types()

        await create_default_eye_colors()
        await create_default_religions()
        await create_default_saas_config()

        await create_rbac_actions()
        await create_sudo_action_types()
        await create_bank_types()
        await create_collections()
        await create_children_display_types()
        await create_data_display_types()

        # Senat-Digit feature modules (auth, session_meeting, presence,
        # agenda, document, vote, parole, notification, audit_security).
        # The per-module loaders read the JSON catalogues
        # (`<module>/seeds/permission_titles_seed.json`) and the aggregator
        # bridges them into the legacy nested rbac_title shape.
        # Per `_planning/_followup_batch.md` F2.
        await create_senat_digit_module_rbac()

    # mark_static_stale runs OUTSIDE the guard — it's the deliberate, final
    # signal that pre-seed static cache rows are obsolete. The next request
    # rebuilds against the freshly seeded data.
    try:
        from app.modules.core.services.user_app_store.user_app_store_service import (
            UserAppStoreService,
        )
        invalidated = await UserAppStoreService.mark_static_stale()
        DebugService.app_debug_print(
            f"Seed: invalidated {invalidated} static user_app_store rows", True
        )
    except Exception as e:
        DebugService.app_debug_print(
            f"Seed: user_app_store invalidation failed: {e}", True
        )


async def create_default_icons():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Upsert default icon - update if they exist, insert if they don't.
    """
    icon_data = {
        "is_default": True,
        "flag": EIconFlag.STANDARD_SVG.value,
        "icon": """
            <svg  enable-background="new 0 0 512 512" height="512" viewBox="0 0 512 512" width="512" xmlns="http://www.w3.org/2000/svg"><path id="XMLID_52_" d="m466.6 199.1c-8.3-11.3-21.1-17.8-35.1-17.8h-10.6v-28.5c0-24-19.5-43.5-43.6-43.5h-127.2c-7.3 0-14.3-2.9-19.5-8l-20-19.9c-8.2-8.2-19.1-12.7-30.7-12.7h-99.4c-24 0-43.5 19.5-43.5 43.6v253.7c-.3 9.7 2.6 19.3 8.5 27.3 8.4 11.4 21.3 18 35.5 18h305.9c19.1 0 35.8-12.3 41.6-30.6l44.7-142.9c4.1-13.3 1.7-27.4-6.6-38.7zm-413.7-86.8c0-15.2 12.4-27.6 27.5-27.6h99.5c7.3 0 14.2 2.9 19.5 8l20 19.9c8.2 8.2 19.1 12.7 30.7 12.7h127.3c15.2 0 27.6 12.4 27.6 27.5v28.5h-280c-19.1 0-35.8 12.3-41.6 30.5l-30.6 97.6v-197.1zm404.9 120.8-44.7 142.9c-3.6 11.6-14.2 19.3-26.3 19.3h-305.9c-9 0-17.2-4.2-22.6-11.4-5.3-7.3-6.9-16.4-4.2-25l44.5-142.3c3.6-11.6 14.2-19.3 26.3-19.3h306.5c8.9 0 17 4.1 22.2 11.2 5.4 7.2 6.9 16.1 4.2 24.6z"></path>
            </svg>
        """,
        "name": "Icône par défaut"
    }
    icon_data = {
        **icon_data,
        "hard_code_flag": generate_label_to_flag(icon_data['name'])
    }
    try:
        result = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.REF_ICON,
            filter_data={"is_default": icon_data["is_default"]},
            update_data=icon_data
        )
        DebugService.app_debug_print("Default icon has been upserted.", result)
    except ValueError as e:
        DebugService.app_debug_print(f"Error: {e}")
    except PermissionError as e:
        DebugService.app_debug_print(f"Permission Error: {e}")

async def create_default_countries():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Upsert default countries - update if they exist, insert if they don't.
    """
    countries_array = [
    {
        "code": "93",
        "name": "Afghanistan",
        "nationality": "afghane",
        "alpha_code_2": "AF",
        "alpha_code_3": "AFG",
        "flag": "🇦🇫",
        "unique_key": "AF-93",
    },
    {
        "code": "27",
        "name": "Afrique du Sud",
        "nationality": "sud-africaine",
        "alpha_code_2": "ZA",
        "alpha_code_3": "ZAF",
        "flag": "🇿🇦",
        "unique_key": "ZA-27",
    },
    {
        "code": "213",
        "name": "Algérie",
        "nationality": "algérienne",
        "alpha_code_2": "DZ",
        "alpha_code_3": "DZA",
        "flag": "🇩🇿",
        "unique_key": "DZ-213",
    },
    {
        "code": "49",
        "name": "Allemagne",
        "nationality": "allemande",
        "alpha_code_2": "DE",
        "alpha_code_3": "DEU",
        "flag": "🇩🇪",
        "unique_key": "DE-49",
    },
    {
        "code": "244",
        "name": "Angola",
        "nationality": "angolaise",
        "alpha_code_2": "AO",
        "alpha_code_3": "AGO",
        "flag": "🇦🇴",
        "unique_key": "AO-244",
    },
    {
        "code": "966",
        "name": "Arabie saoudite",
        "nationality": "saoudienne",
        "alpha_code_2": "SA",
        "alpha_code_3": "SAU",
        "flag": "🇸🇦",
        "unique_key": "SA-966",
    },
    {
        "code": "54",
        "name": "Argentine",
        "nationality": "argentine",
        "alpha_code_2": "AR",
        "alpha_code_3": "ARG",
        "flag": "🇦🇷",
        "unique_key": "AR-54",
    },
    {
        "code": "61",
        "name": "Australie",
        "nationality": "australienne",
        "alpha_code_2": "AU",
        "alpha_code_3": "AUS",
        "flag": "🇦🇺",
        "unique_key": "AU-61",
    },
    {
        "code": "43",
        "name": "Autriche",
        "nationality": "autrichienne",
        "alpha_code_2": "AT",
        "alpha_code_3": "AUT",
        "flag": "🇦🇹",
        "unique_key": "AT-43",
    },
    {
        "code": "501",
        "name": "Belize",
        "nationality": "belizienne",
        "alpha_code_2": "BZ",
        "alpha_code_3": "BLZ",
        "flag": "🇧🇿",
        "unique_key": "BZ-501",
    },
    {
        "code": "375",
        "name": "Biélorussie",
        "nationality": "biélorusse",
        "alpha_code_2": "BY",
        "alpha_code_3": "BLR",
        "flag": "🇧🇾",
        "unique_key": "BY-375",
    },
    {
        "code": "32",
        "name": "Belgique",
        "nationality": "belge",
        "alpha_code_2": "BE",
        "alpha_code_3": "BEL",
        "flag": "🇧🇪",
        "unique_key": "BE-32",
    },
    {
        "code": "229",
        "name": "Bénin",
        "nationality": "béninoise",
        "alpha_code_2": "BJ",
        "alpha_code_3": "BEN",
        "flag": "🇧🇯",
        "unique_key": "BJ-229",
    },
    {
        "code": "591",
        "name": "Bolivie",
        "nationality": "bolivienne",
        "alpha_code_2": "BO",
        "alpha_code_3": "BOL",
        "flag": "🇧🇴",
        "unique_key": "BO-591",
    },
    {
        "code": "267",
        "name": "Botswana",
        "nationality": "botswanaise",
        "alpha_code_2": "BW",
        "alpha_code_3": "BWA",
        "flag": "🇧🇼",
        "unique_key": "BW-267",
    },
    {
        "code": "55",
        "name": "Brésil",
        "nationality": "brésilienne",
        "alpha_code_2": "BR",
        "alpha_code_3": "BRA",
        "flag": "🇧🇷",
        "unique_key": "BR-55",
    },
    {
        "code": "387",
        "name": "Bosnie-Herzégovine",
        "nationality": "bosnienne",
        "alpha_code_2": "BA",
        "alpha_code_3": "BIH",
        "flag": "🇧🇦",
        "unique_key": "BA-387",
    },
    {
        "code": "855",
        "name": "Cambodge",
        "nationality": "cambodienne",
        "alpha_code_2": "KH",
        "alpha_code_3": "KHM",
        "flag": "🇰🇭",
        "unique_key": "KH-855",
    },
    {
        "code": "385",
        "name": "Croatie",
        "nationality": "croate",
        "alpha_code_2": "HR",
        "alpha_code_3": "HRV",
        "flag": "🇭🇷",
        "unique_key": "HR-385",
    },
    {
        "code": "357",
        "name": "Chypre",
        "nationality": "chypriote",
        "alpha_code_2": "CY",
        "alpha_code_3": "CYP",
        "flag": "🇨🇾",
        "unique_key": "CY-357",
    },
    {
        "code": "880",
        "name": "Bangladesh",
        "nationality": "bangladaise",
        "alpha_code_2": "BD",
        "alpha_code_3": "BGD",
        "flag": "🇧🇩",
        "unique_key": "BD-880",
    },
    {
        "code": "95",
        "name": "Myanmar (ex-Birmanie)",
        "nationality": "birmane",
        "alpha_code_2": "MM",
        "alpha_code_3": "MMR",
        "flag": "🇲🇲",
        "unique_key": "MM-95",
    },
    {
        "code": "226",
        "name": "Burkina Faso",
        "nationality": "burkinabée",
        "alpha_code_2": "BF",
        "alpha_code_3": "BFA",
        "flag": "🇧🇫",
        "unique_key": "BF-226",
    },
    {
        "code": "975",
        "name": "Bhoutan",
        "nationality": "bhoutanais",
        "alpha_code_2": "BT",
        "alpha_code_3": "BTN",
        "flag": "🇧🇹",
        "unique_key": "BT-975",
    },
    {
        "code": "257",
        "name": "Burundi",
        "nationality": "burundaise",
        "alpha_code_2": "BI",
        "alpha_code_3": "BDI",
        "flag": "🇧🇮",
        "unique_key": "BI-257",
    },
    {
        "code": "237",
        "name": "Cameroun",
        "nationality": "camerounaise",
        "alpha_code_2": "CM",
        "alpha_code_3": "CMR",
        "flag": "🇨🇲",
        "unique_key": "CM-237",
    },
    {
        "code": "1",
        "name": "Canada",
        "nationality": "canadienne",
        "alpha_code_2": "CA",
        "alpha_code_3": "CAN",
        "flag": "🇨🇦",
        "unique_key": "CA-1",
    },
    {
        "code": "236",
        "name": "République centrafricaine",
        "nationality": "centrafricaine",
        "alpha_code_2": "CF",
        "alpha_code_3": "CAF",
        "flag": "🇨🇫",
        "unique_key": "CF-236",
    },
    {
        "code": "56",
        "name": "Chili",
        "nationality": "chilienne",
        "alpha_code_2": "CL",
        "alpha_code_3": "CHL",
        "flag": "🇨🇱",
        "unique_key": "CL-56",
    },
    {
        "code": "36",
        "name": "Hongrie",
        "nationality": "hongroise",
        "alpha_code_2": "HU",
        "alpha_code_3": "HUN",
        "flag": "🇭🇺",
        "unique_key": "HU-36",
    },
    {
        "code": "86",
        "name": "Chine",
        "nationality": "chinoise",
        "alpha_code_2": "CN",
        "alpha_code_3": "CHN",
        "flag": "🇨🇳",
        "unique_key": "CN-86",
    },
    {
        "code": "57",
        "name": "Colombie",
        "nationality": "colombienne",
        "alpha_code_2": "CO",
        "alpha_code_3": "COL",
        "flag": "🇨🇴",
        "unique_key": "CO-57",
    },
    {
        "code": "243",
        "name": "République démocratique du Congo",
        "nationality": "congolaise (Kinshasa)",
        "alpha_code_2": "CD",
        "alpha_code_3": "COD",
        "flag": "🇨🇩",
        "unique_key": "CD-243",
    },
    {
        "code": "242",
        "name": "République du Congo",
        "nationality": "congolaise (Brazzaville)",
        "alpha_code_2": "CG",
        "alpha_code_3": "COG",
        "flag": "🇨🇬",
        "unique_key": "CG-242",
    },
    {
        "code": "850",
        "name": "Corée du Nord",
        "nationality": "nord-coréenne",
        "alpha_code_2": "KP",
        "alpha_code_3": "PRK",
        "flag": "🇰🇵",
        "unique_key": "KP-850",
    },
    {
        "code": "82",
        "name": "Corée du Sud",
        "nationality": "sud-coréenne",
        "alpha_code_2": "KR",
        "alpha_code_3": "KOR",
        "flag": "🇰🇷",
        "unique_key": "KR-82",
    },
    {
        "code": "225",
        "name": "Côte d'Ivoire",
        "nationality": "ivoirienne",
        "alpha_code_2": "CI",
        "alpha_code_3": "CIV",
        "flag": "🇨🇮",
        "unique_key": "CI-225",
    },
    {
        "code": "45",
        "name": "Danemark",
        "nationality": "danoise",
        "alpha_code_2": "DK",
        "alpha_code_3": "DNK",
        "flag": "🇩🇰",
        "unique_key": "DK-45",
    },
    {
        "code": "253",
        "name": "Djibouti",
        "nationality": "djiboutienne",
        "alpha_code_2": "DJ",
        "alpha_code_3": "DJI",
        "flag": "🇩🇯",
        "unique_key": "DJ-253",
    },
    {
        "code": "20",
        "name": "Égypte",
        "nationality": "égyptienne",
        "alpha_code_2": "EG",
        "alpha_code_3": "EGY",
        "flag": "🇪🇬",
        "unique_key": "EG-20",
    },
    {
        "code": "971",
        "name": "Émirats arabes unis",
        "nationality": "émiratie",
        "alpha_code_2": "AE",
        "alpha_code_3": "ARE",
        "flag": "🇦🇪",
        "unique_key": "AE-971",
    },
    {
        "code": "593",
        "name": "Équateur",
        "nationality": "équatorienne",
        "alpha_code_2": "EC",
        "alpha_code_3": "ECU",
        "flag": "🇪🇨",
        "unique_key": "EC-593",
    },
    {
        "code": "291",
        "name": "Érythrée",
        "nationality": "érythréenne",
        "alpha_code_2": "ER",
        "alpha_code_3": "ERI",
        "flag": "🇪🇷",
        "unique_key": "ER-291",
    },
    {
        "code": "34",
        "name": "Espagne",
        "nationality": "espagnole",
        "alpha_code_2": "ES",
        "alpha_code_3": "ESP",
        "flag": "🇪🇸",
        "unique_key": "ES-34",
    },
    {
        "code": "372",
        "name": "Estonie",
        "nationality": "estonienne",
        "alpha_code_2": "EE",
        "alpha_code_3": "EST",
        "flag": "🇪🇪",
        "unique_key": "EE-372",
    },
    {
        "code": "1",
        "name": "États-Unis",
        "nationality": "américaine",
        "alpha_code_2": "US",
        "alpha_code_3": "USA",
        "flag": "🇺🇸",
        "unique_key": "US-1",
    },
    {
        "code": "251",
        "name": "Éthiopie",
        "nationality": "éthiopienne",
        "alpha_code_2": "ET",
        "alpha_code_3": "ETH",
        "flag": "🇪🇹",
        "unique_key": "ET-251",
    },
    {
        "code": "358",
        "name": "Finlande",
        "nationality": "finlandaise",
        "alpha_code_2": "FI",
        "alpha_code_3": "FIN",
        "flag": "🇫🇮",
        "unique_key": "FI-358",
    },
    {
        "code": "33",
        "name": "France",
        "nationality": "française",
        "alpha_code_2": "FR",
        "alpha_code_3": "FRA",
        "flag": "🇫🇷",
        "unique_key": "FR-33",
    },
    {
        "code": "241",
        "name": "Gabon",
        "nationality": "gabonaise",
        "alpha_code_2": "GA",
        "alpha_code_3": "GAB",
        "flag": "🇬🇦",
        "unique_key": "GA-241",
    },
    {
        "code": "220",
        "name": "Gambie",
        "nationality": "gambienne",
        "alpha_code_2": "GM",
        "alpha_code_3": "GMB",
        "flag": "🇬🇲",
        "unique_key": "GM-220",
    },
    {
        "code": "995",
        "name": "Géorgie",
        "nationality": "géorgienne",
        "alpha_code_2": "GE",
        "alpha_code_3": "GEO",
        "flag": "🇬🇪",
        "unique_key": "GE-995",
    },
    {
        "code": "233",
        "name": "Ghana",
        "nationality": "ghanéenne",
        "alpha_code_2": "GH",
        "alpha_code_3": "GHA",
        "flag": "🇬🇭",
        "unique_key": "GH-233",
    },
    {
        "code": "30",
        "name": "Grèce",
        "nationality": "grecque",
        "alpha_code_2": "GR",
        "alpha_code_3": "GRC",
        "flag": "🇬🇷",
        "unique_key": "GR-30",
    },
    {
        "code": "299",
        "name": "Groenland",
        "nationality": "groenlandais",
        "alpha_code_2": "GL",
        "alpha_code_3": "GRL",
        "flag": "🇬🇱",
        "unique_key": "GL-299",
    },
    {
        "code": "224",
        "name": "Guinée",
        "nationality": "guinéenne",
        "alpha_code_2": "GN",
        "alpha_code_3": "GIN",
        "flag": "🇬🇳",
        "unique_key": "GN-224",
    },
    {
        "code": "240",
        "name": "Guinée équatoriale",
        "nationality": "équato-guinéenne",
        "alpha_code_2": "GQ",
        "alpha_code_3": "GNQ",
        "flag": "🇬🇶",
        "unique_key": "GQ-240",
    },
    {
        "code": "245",
        "name": "Guinée-Bissau",
        "nationality": "bissau-guinéenne",
        "alpha_code_2": "GW",
        "alpha_code_3": "GNB",
        "flag": "🇬🇼",
        "unique_key": "GW-245",
    },
    {
        "code": "592",
        "name": "Guyana",
        "nationality": "guyanaise",
        "alpha_code_2": "GY",
        "alpha_code_3": "GUY",
        "flag": "🇬🇾",
        "unique_key": "GY-592",
    },
    {
        "code": "91",
        "name": "Inde",
        "nationality": "indienne",
        "alpha_code_2": "IN",
        "alpha_code_3": "IND",
        "flag": "🇮🇳",
        "unique_key": "IN-91",
    },
    {
        "code": "354",
        "name": "Islande",
        "nationality": "islandaise",
        "alpha_code_2": "IS",
        "alpha_code_3": "ISL",
        "flag": "🇮🇸",
        "unique_key": "IS-354",
    },
    {
        "code": "62",
        "name": "Indonésie",
        "nationality": "indonésienne",
        "alpha_code_2": "ID",
        "alpha_code_3": "IDN",
        "flag": "🇮🇩",
        "unique_key": "ID-62",
    },
    {
        "code": "964",
        "name": "Irak",
        "nationality": "irakienne",
        "alpha_code_2": "IQ",
        "alpha_code_3": "IRQ",
        "flag": "🇮🇶",
        "unique_key": "IQ-964",
    },
    {
        "code": "98",
        "name": "Iran",
        "nationality": "iranienne",
        "alpha_code_2": "IR",
        "alpha_code_3": "IRN",
        "flag": "🇮🇷",
        "unique_key": "IR-98",
    },
    {
        "code": "353",
        "name": "Irlande",
        "nationality": "irlandaise",
        "alpha_code_2": "IE",
        "alpha_code_3": "IRL",
        "flag": "🇮🇪",
        "unique_key": "IE-353",
    },
    {
        "code": "972",
        "name": "Israël",
        "nationality": "israélienne",
        "alpha_code_2": "IL",
        "alpha_code_3": "ISR",
        "flag": "🇮🇱",
        "unique_key": "IL-972",
    },
    {
        "code": "39",
        "name": "Italie",
        "nationality": "italienne",
        "alpha_code_2": "IT",
        "alpha_code_3": "ITA",
        "flag": "🇮🇹",
        "unique_key": "IT-39",
    },
    {
        "code": "1876",
        "name": "Jamaïque",
        "nationality": "jamaïcaine",
        "alpha_code_2": "JM",
        "alpha_code_3": "JAM",
        "flag": "🇯🇲",
        "unique_key": "JM-1876",
    },
    {
        "code": "81",
        "name": "Japon",
        "nationality": "japonaise",
        "alpha_code_2": "JP",
        "alpha_code_3": "JPN",
        "flag": "🇯🇵",
        "unique_key": "JP-81",
    },
    {
        "code": "962",
        "name": "Jordanie",
        "nationality": "jordannienne",
        "alpha_code_2": "JO",
        "alpha_code_3": "JOR",
        "flag": "🇯🇴",
        "unique_key": "JO-962",
    },
    {
        "code": "7",
        "name": "Kazakhstan",
        "nationality": "kazakhstanaise",
        "alpha_code_2": "KZ",
        "alpha_code_3": "KAZ",
        "flag": "🇰🇿",
        "unique_key": "KZ-7",
    },
    {
        "code": "254",
        "name": "Kenya",
        "nationality": "kenyane",
        "alpha_code_2": "KE",
        "alpha_code_3": "KEN",
        "flag": "🇰🇪",
        "unique_key": "KE-254",
    },
    {
        "code": "996",
        "name": "Kyrgyzstan",
        "nationality": "kirghize",
        "alpha_code_2": "KG",
        "alpha_code_3": "KGZ",
        "flag": "🇰🇬",
        "unique_key": "KG-996",
    },
    {
        "code": "965",
        "name": "Koweït",
        "nationality": "koweïtienne",
        "alpha_code_2": "KW",
        "alpha_code_3": "KWT",
        "flag": "🇰🇼",
        "unique_key": "KW-965",
    },
    {
        "code": "231",
        "name": "Liberia",
        "nationality": "libérienne",
        "alpha_code_2": "LR",
        "alpha_code_3": "LBR",
        "flag": "🇱🇷",
        "unique_key": "LR-231",
    },
    {
        "code": "371",
        "name": "Lettonie",
        "nationality": "lettonne",
        "alpha_code_2": "LV",
        "alpha_code_3": "LVA",
        "flag": "🇱🇻",
        "unique_key": "LV-371",
    },
    {
        "code": "856",
        "name": "Laos",
        "nationality": "laotienne",
        "alpha_code_2": "LA",
        "alpha_code_3": "LAO",
        "flag": "🇱🇦",
        "unique_key": "LA-856",
    },
    {
        "code": "266",
        "name": "Lesotho",
        "nationality": "mosotho",
        "alpha_code_2": "LS",
        "alpha_code_3": "LSO",
        "flag": "🇱🇸",
        "unique_key": "LS-266",
    },
    {
        "code": "218",
        "name": "Libye",
        "nationality": "libyenne",
        "alpha_code_2": "LY",
        "alpha_code_3": "LBY",
        "flag": "🇱🇾",
        "unique_key": "LY-218",
    },
    {
        "code": "370",
        "name": "Lituanie",
        "nationality": "lituanienne",
        "alpha_code_2": "LT",
        "alpha_code_3": "LTU",
        "flag": "🇱🇹",
        "unique_key": "LT-370",
    },
    {
        "code": "352",
        "name": "Luxembourg",
        "nationality": "luxembourgeoise",
        "alpha_code_2": "LU",
        "alpha_code_3": "LUX",
        "flag": "🇱🇺",
        "unique_key": "LU-352",
    },
    {
        "code": "261",
        "name": "Madagascar",
        "nationality": "malgache",
        "alpha_code_2": "MG",
        "alpha_code_3": "MDG",
        "flag": "🇲🇬",
        "unique_key": "MG-261",
    },
    {
        "code": "222",
        "name": "Mauritanie",
        "nationality": "mauritanienne",
        "alpha_code_2": "MR",
        "alpha_code_3": "MRT",
        "flag": "🇲🇷",
        "unique_key": "MR-222",
    },
    {
        "code": "60",
        "name": "Malaisie",
        "nationality": "malaisienne",
        "alpha_code_2": "MY",
        "alpha_code_3": "MYS",
        "flag": "🇲🇾",
        "unique_key": "MY-60",
    },
    {
        "code": "265",
        "name": "Malawi",
        "nationality": "malawienne",
        "alpha_code_2": "MW",
        "alpha_code_3": "MWI",
        "flag": "🇲🇼",
        "unique_key": "MW-265",
    },
    {
        "code": "223",
        "name": "Mali",
        "nationality": "malienne",
        "alpha_code_2": "ML",
        "alpha_code_3": "MLI",
        "flag": "🇲🇱",
        "unique_key": "ML-223",
    },
    {
        "code": "212",
        "name": "Maroc",
        "nationality": "marocaine",
        "alpha_code_2": "MA",
        "alpha_code_3": "MAR",
        "flag": "🇲🇦",
        "unique_key": "MA-212",
    },
    {
        "code": "52",
        "name": "Mexique",
        "nationality": "mexicaine",
        "alpha_code_2": "MX",
        "alpha_code_3": "MEX",
        "flag": "🇲🇽",
        "unique_key": "MX-52",
    },
    {
        "code": "976",
        "name": "Mongolie",
        "nationality": "mongole",
        "alpha_code_2": "MN",
        "alpha_code_3": "MNG",
        "flag": "🇲🇳",
        "unique_key": "MN-976",
    },
    {
        "code": "258",
        "name": "Mozambique",
        "nationality": "mozambicaine",
        "alpha_code_2": "MZ",
        "alpha_code_3": "MOZ",
        "flag": "🇲🇿",
        "unique_key": "MZ-258",
    },
    {
        "code": "264",
        "name": "Namibie",
        "nationality": "namibienne",
        "alpha_code_2": "NA",
        "alpha_code_3": "NAM",
        "flag": "🇳🇦",
        "unique_key": "NA-264",
    },
    {
        "code": "977",
        "name": "Népal",
        "nationality": "népalaise",
        "alpha_code_2": "NP",
        "alpha_code_3": "NPL",
        "flag": "🇳🇵",
        "unique_key": "NP-977",
    },
    {
        "code": "64",
        "name": "Nouvelle-Zélande",
        "nationality": "néo-zélandaise",
        "alpha_code_2": "NZ",
        "alpha_code_3": "NZL",
        "flag": "🇳🇿",
        "unique_key": "NZ-64",
    },
    {
        "code": "227",
        "name": "Niger",
        "nationality": "nigérienne",
        "alpha_code_2": "NE",
        "alpha_code_3": "NER",
        "flag": "🇳🇪",
        "unique_key": "NE-227",
    },
    {
        "code": "234",
        "name": "Nigéria",
        "nationality": "nigériane",
        "alpha_code_2": "NG",
        "alpha_code_3": "NGA",
        "flag": "🇳🇬",
        "unique_key": "NG-234",
    },
    {
        "code": "47",
        "name": "Norvège",
        "nationality": "norvégienne",
        "alpha_code_2": "NO",
        "alpha_code_3": "NOR",
        "flag": "🇳🇴",
        "unique_key": "NO-47",
    },
    {
        "code": "968",
        "name": "Oman",
        "nationality": "omanaise",
        "alpha_code_2": "OM",
        "alpha_code_3": "OMN",
        "flag": "🇴🇲",
        "unique_key": "OM-968",
    },
    {
        "code": "256",
        "name": "Ouganda",
        "nationality": "ougandaise",
        "alpha_code_2": "UG",
        "alpha_code_3": "UGA",
        "flag": "🇺🇬",
        "unique_key": "UG-256",
    },
    {
        "code": "92",
        "name": "Pakistan",
        "nationality": "pakistanaise",
        "alpha_code_2": "PK",
        "alpha_code_3": "PAK",
        "flag": "🇵🇰",
        "unique_key": "PK-92",
    },
    {
        "code": "675",
        "name": "Papouasie-Nouvelle-Guinée",
        "nationality": "papouasienne",
        "alpha_code_2": "PG",
        "alpha_code_3": "PNG",
        "flag": "🇵🇬",
        "unique_key": "PG-675",
    },
    {
        "code": "595",
        "name": "Paraguay",
        "nationality": "paraguayenne",
        "alpha_code_2": "PY",
        "alpha_code_3": "PRY",
        "flag": "🇵🇾",
        "unique_key": "PY-595",
    },
    {
        "code": "31",
        "name": "Pays-Bas",
        "nationality": "néerlandaise",
        "alpha_code_2": "NL",
        "alpha_code_3": "NLD",
        "flag": "🇳🇱",
        "unique_key": "NL-31",
    },
    {
        "code": "51",
        "name": "Pérou",
        "nationality": "péruvienne",
        "alpha_code_2": "PE",
        "alpha_code_3": "PER",
        "flag": "🇵🇪",
        "unique_key": "PE-51",
    },
    {
        "code": "63",
        "name": "Philippines",
        "nationality": "philippine",
        "alpha_code_2": "PH",
        "alpha_code_3": "PHL",
        "flag": "🇵🇭",
        "unique_key": "PH-63",
    },
    {
        "code": "48",
        "name": "Pologne",
        "nationality": "polonaise",
        "alpha_code_2": "PL",
        "alpha_code_3": "POL",
        "flag": "🇵🇱",
        "unique_key": "PL-48",
    },
    {
        "code": "351",
        "name": "Portugal",
        "nationality": "portugaise",
        "alpha_code_2": "PT",
        "alpha_code_3": "PRT",
        "flag": "🇵🇹",
        "unique_key": "PT-351",
    },
    {
        "code": "974",
        "name": "Qatar",
        "nationality": "qatari",
        "alpha_code_2": "QA",
        "alpha_code_3": "QAT",
        "flag": "🇶🇦",
        "unique_key": "QA-974",
    },
    {
        "code": "355",
        "name": "Albanie",
        "nationality": "albanaise",
        "alpha_code_2": "AL",
        "alpha_code_3": "ALB",
        "flag": "🇦🇱",
        "unique_key": "AL-355",
    },
    {
        "code": "40",
        "name": "Roumanie",
        "nationality": "roumaine",
        "alpha_code_2": "RO",
        "alpha_code_3": "ROU",
        "flag": "🇷🇴",
        "unique_key": "RO-40",
    },
    {
        "code": "44",
        "name": "Royaume-Uni",
        "nationality": "britannique",
        "alpha_code_2": "GB",
        "alpha_code_3": "GBR",
        "flag": "🇬🇧",
        "unique_key": "GB-44",
    },
    {
        "code": "7",
        "name": "Russie",
        "nationality": "russe",
        "alpha_code_2": "RU",
        "alpha_code_3": "RUS",
        "flag": "🇷🇺",
        "unique_key": "RU-7",
    },
    {
        "code": "250",
        "name": "Rwanda",
        "nationality": "rwandaise",
        "alpha_code_2": "RW",
        "alpha_code_3": "RWA",
        "flag": "🇷🇼",
        "unique_key": "RW-250",
    },
    {
        "code": "221",
        "name": "Sénégal",
        "nationality": "sénégalaise",
        "alpha_code_2": "SN",
        "alpha_code_3": "SEN",
        "flag": "🇸🇳",
        "unique_key": "SN-221",
    },
    {
        "code": "232",
        "name": "Sierra Leone",
        "nationality": "sierra-léonaise",
        "alpha_code_2": "SL",
        "alpha_code_3": "SLE",
        "flag": "🇸🇱",
        "unique_key": "SL-232",
    },
    {
        "code": "252",
        "name": "Somalie",
        "nationality": "somalienne",
        "alpha_code_2": "SO",
        "alpha_code_3": "SOM",
        "flag": "🇸🇴",
        "unique_key": "SO-252",
    },
    {
        "code": "249",
        "name": "Soudan",
        "nationality": "soudanaise du Nord",
        "alpha_code_2": "SD",
        "alpha_code_3": "SDN",
        "flag": "🇸🇩",
        "unique_key": "SD-249",
    },
    {
        "code": "211",
        "name": "Soudan du Sud",
        "nationality": "soudanaise du Sud",
        "alpha_code_2": "SS",
        "alpha_code_3": "SSD",
        "flag": "🇸🇸",
        "unique_key": "SS-211",
    },
    {
        "code": "597",
        "name": "Suriname",
        "nationality": "surinamienne",
        "alpha_code_2": "SR",
        "alpha_code_3": "SUR",
        "flag": "🇸🇷",
        "unique_key": "SR-597",
    },
    {
        "code": "94",
        "name": "Sri Lanka",
        "nationality": "srilankaise",
        "alpha_code_2": "LK",
        "alpha_code_3": "LKA",
        "flag": "🇱🇰",
        "unique_key": "LK-94",
    },
    {
        "code": "46",
        "name": "Suède",
        "nationality": "suédoise",
        "alpha_code_2": "SE",
        "alpha_code_3": "SWE",
        "flag": "🇸🇪",
        "unique_key": "SE-46",
    },
    {
        "code": "41",
        "name": "Suisse",
        "nationality": "suisse",
        "alpha_code_2": "CH",
        "alpha_code_3": "CHE",
        "flag": "🇨🇭",
        "unique_key": "CH-41",
    },
    {
        "code": "963",
        "name": "Syrie",
        "nationality": "syrienne",
        "alpha_code_2": "SY",
        "alpha_code_3": "SYR",
        "flag": "🇸🇾",
        "unique_key": "SY-963",
    },
    {
        "code": "886",
        "name": "Taiwan",
        "nationality": "taïwanaise",
        "alpha_code_2": "TW",
        "alpha_code_3": "TWN",
        "flag": "🇹🇼",
        "unique_key": "TW-886",
    },
    {
        "code": "255",
        "name": "Tanzanie",
        "nationality": "tanzanienne",
        "alpha_code_2": "TZ",
        "alpha_code_3": "TZA",
        "flag": "🇹🇿",
        "unique_key": "TZ-255",
    },
    {
        "code": "235",
        "name": "Tchad",
        "nationality": "tchadienne",
        "alpha_code_2": "TD",
        "alpha_code_3": "TCD",
        "flag": "🇹🇩",
        "unique_key": "TD-235",
    },
    {
        "code": "420",
        "name": "République tchèque",
        "nationality": "tchèque",
        "alpha_code_2": "CZ",
        "alpha_code_3": "CZE",
        "flag": "🇨🇿",
        "unique_key": "CZ-420",
    },
    {
        "code": "228",
        "name": "Togo",
        "nationality": "togolaise",
        "alpha_code_2": "TG",
        "alpha_code_3": "TGO",
        "flag": "🇹🇬",
        "unique_key": "TG-228",
    },
    {
        "code": "66",
        "name": "Thaïlande",
        "nationality": "thaïlandaise",
        "alpha_code_2": "TH",
        "alpha_code_3": "THA",
        "flag": "🇹🇭",
        "unique_key": "TH-66",
    },
    {
        "code": "216",
        "name": "Tunisie",
        "nationality": "tunisienne",
        "alpha_code_2": "TN",
        "alpha_code_3": "TUN",
        "flag": "🇹🇳",
        "unique_key": "TN-216",
    },
    {
        "code": "90",
        "name": "Turquie",
        "nationality": "turque",
        "alpha_code_2": "TR",
        "alpha_code_3": "TUR",
        "flag": "🇹🇷",
        "unique_key": "TR-90",
    },
    {
        "code": "993",
        "name": "Turkménistan",
        "nationality": "turkmène",
        "alpha_code_2": "TM",
        "alpha_code_3": "TKM",
        "flag": "🇹🇲",
        "unique_key": "TM-993",
    },
    {
        "code": "380",
        "name": "Ukraine",
        "nationality": "ukrainienne",
        "alpha_code_2": "UA",
        "alpha_code_3": "UKR",
        "flag": "🇺🇦",
        "unique_key": "UA-380",
    },
    {
        "code": "598",
        "name": "Uruguay",
        "nationality": "uruguayenne",
        "alpha_code_2": "UY",
        "alpha_code_3": "URY",
        "flag": "🇺🇾",
        "unique_key": "UY-598",
    },
    {
        "code": "998",
        "name": "Ouzbékistan",
        "nationality": "ouzbek",
        "alpha_code_2": "UZ",
        "alpha_code_3": "UZB",
        "flag": "🇺🇿",
        "unique_key": "UZ-998",
    },
    {
        "code": "58",
        "name": "Vénézuela",
        "nationality": "vénézuélienne",
        "alpha_code_2": "VE",
        "alpha_code_3": "VEN",
        "flag": "🇻🇪",
        "unique_key": "VE-58",
    },
    {
        "code": "84",
        "name": "Vietnam",
        "nationality": "vietnamienne",
        "alpha_code_2": "VN",
        "alpha_code_3": "VNM",
        "flag": "🇻🇳",
        "unique_key": "VN-84",
    },
    {
        "code": "967",
        "name": "Yémen",
        "nationality": "yéménite",
        "alpha_code_2": "YE",
        "alpha_code_3": "YEM",
        "flag": "🇾🇪",
        "unique_key": "YE-967",
    },
    {
        "code": "260",
        "name": "Zambie",
        "nationality": "zambienne",
        "alpha_code_2": "ZM",
        "alpha_code_3": "ZMB",
        "flag": "🇿🇲",
        "unique_key": "ZM-260",
    },
    {
        "code": "263",
        "name": "Zimbabwe",
        "nationality": "zimbabwéenne",
        "alpha_code_2": "ZW",
        "alpha_code_3": "ZWE",
        "flag": "🇿🇼",
        "unique_key": "ZW-263",
    },
    # Extra countries not in the original array:
    {
        "code": "379",
        "name": "Vatican",
        "nationality": "vatican",
        "alpha_code_2": "VA",
        "alpha_code_3": "VAT",
        "flag": "🇻🇦",
        "unique_key": "VA-379",
    },
    {
        "code": "378",
        "name": "Saint-Marin",
        "nationality": "saint-marinais",
        "alpha_code_2": "SM",
        "alpha_code_3": "SMR",
        "flag": "🇸🇲",
        "unique_key": "SM-378",
    },
    {
        "code": "377",
        "name": "Monaco",
        "nationality": "monégasque",
        "alpha_code_2": "MC",
        "alpha_code_3": "MCO",
        "flag": "🇲🇨",
        "unique_key": "MC-377",
    },
    {
        "code": "423",
        "name": "Liechtenstein",
        "nationality": "liechtensteinois",
        "alpha_code_2": "LI",
        "alpha_code_3": "LIE",
        "flag": "🇱🇮",
        "unique_key": "LI-423",
    },
    {
        "code": "382",
        "name": "Monténégro",
        "nationality": "monténégrin",
        "alpha_code_2": "ME",
        "alpha_code_3": "MNE",
        "flag": "🇲🇪",
        "unique_key": "ME-382",
    },
]

    try:
        for country in countries_array:
            # country["flag"] = get_country_flag(country["alpha_code_2"])
            country["unique_key"] = str(country["unique_key"]).strip()
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                filter_data={"unique_key": country["unique_key"]},
                update_data=country
            )
            DebugService.app_debug_print("Default countries has been upserted.", result)

    except ValueError as e:
        DebugService.app_debug_print(f"Error: {e}")
    except PermissionError as e:
        DebugService.app_debug_print(f"Permission Error: {e}")

async def create_default_blood_types():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Upsert default blood types - update if they exist, insert if they don't.
    """
    blood_types = [
    {
        "name": "O+",
        "description_str": "Le type O positif, le plus courant, peut donner à O+, A+, B+ et AB+.",
        "description_html": "<p>Le type O positif, le plus courant, peut donner à O+, A+, B+ et AB+.</p>",
        "rh_factor": "Positive",
        "universal_donor": False,
        "universal_recipient": False,
        "flag": "o_positive"
    },
    {
        "name": "O-",
        "description_str": "Le type O négatif est reconnu comme donneur universel de globules rouges, car il peut être transfusé à tous les groupes sanguins.",
        "description_html": "<p>Le type O négatif est reconnu comme donneur universel de globules rouges, car il peut être transfusé à tous les groupes sanguins.</p>",
        "rh_factor": "Negative",
        "universal_donor": True,
        "universal_recipient": False,
        "flag": "o_negative"
    },
    {
        "name": "A+",
        "description_str": "Le type A positif peut recevoir de A+ et O+, et donner à A+ et AB+.",
        "description_html": "<p>Le type A positif peut recevoir de A+ et O+, et donner à A+ et AB+.</p>",
        "rh_factor": "Positive",
        "universal_donor": False,
        "universal_recipient": False,
        "flag": "a_positive"
    },
    {
        "name": "A-",
        "description_str": "Le type A négatif peut recevoir de A- et O-, et donner à A+, A-, AB+ et AB-.",
        "description_html": "<p>Le type A négatif peut recevoir de A- et O-, et donner à A+, A-, AB+ et AB-.</p>",
        "rh_factor": "Negative",
        "universal_donor": False,
        "universal_recipient": False,
        "flag": "a_negative"
    },
    {
        "name": "B+",
        "description_str": "Le type B positif peut recevoir de B+ et O+, et donner à B+ et AB+.",
        "description_html": "<p>Le type B positif peut recevoir de B+ et O+, et donner à B+ et AB+.</p>",
        "rh_factor": "Positive",
        "universal_donor": False,
        "universal_recipient": False,
        "flag": "b_positive"
    },
    {
        "name": "B-",
        "description_str": "Le type B négatif peut recevoir de B- et O-, et donner à B+, B-, AB+ et AB-.",
        "description_html": "<p>Le type B négatif peut recevoir de B- et O-, et donner à B+, B-, AB+ et AB-.</p>",
        "rh_factor": "Negative",
        "universal_donor": False,
        "universal_recipient": False,
        "flag": "b_negative"
    },
    {
        "name": "AB+",
        "description_str": "Le type AB positif est le receveur universel, pouvant recevoir de tous les groupes sanguins, mais il ne peut donner qu'à AB+.",
        "description_html": "<p>Le type AB positif est le receveur universel, pouvant recevoir de tous les groupes sanguins, mais il ne peut donner qu'à AB+.</p>",
        "rh_factor": "Positive",
        "universal_donor": False,
        "universal_recipient": True,
        "flag": "ab_positive"
    },
    {
        "name": "AB-",
        "description_str": "Le type AB négatif peut recevoir de tous les groupes négatifs et donner à AB+ et AB-.",
        "description_html": "<p>Le type AB négatif peut recevoir de tous les groupes négatifs et donner à AB+ et AB-.</p>",
        "rh_factor": "Negative",
        "universal_donor": False,
        "universal_recipient": False,
        "flag": "ab_negative"
    }
]

    for blood_type in blood_types:
        try:
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_BLOOD_TYPE,
                filter_data={"flag": blood_type["flag"].lower()},
                update_data=blood_type
            )
            # DebugService.app_debug_print("upserted result:", result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")

async def create_default_eye_colors():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Upsert default eyes colors - update if they exist, insert if they don't.
    """
    eye_colors = [
    {
        "name": "Noir",
        "description_str": "Les yeux noirs sont caractérisés par une forte concentration en mélanine, donnant une apparence très foncée à l'iris. Cette couleur est particulièrement commune dans certaines populations d'Asie et d'Afrique.",
        "flag": "noir"
    },
    {
        "name": "Bleu",
        "description_str": "Les yeux bleus se caractérisent par une faible teneur en mélanine et sont souvent associés aux personnes d'origine nord-européenne.",
        "flag": "bleu"
    },
    {
        "name": "Vert",
        "description_str": "Les yeux verts sont relativement rares, affichant souvent un mélange de nuances vertes et dorées, typiques des origines celtes ou germaniques.",
        "flag": "vert"
    },
    {
        "name": "Marron",
        "description_str": "Les yeux marron sont les plus courants dans le monde, avec des variations allant du marron clair au marron foncé en raison d'une plus forte teneur en mélanine.",
        "flag": "marron"
    },
    {
        "name": "Noisette",
        "description_str": "Les yeux noisette présentent une combinaison subtile de teintes marron, vertes et parfois dorées, pouvant varier selon l'éclairage.",
        "flag": "noisette"
    },
    {
        "name": "Gris",
        "description_str": "Les yeux gris, une variante rare, ressemblent aux yeux bleus mais avec une tonalité plus atténuée qui peut changer en fonction de la lumière.",
        "flag": "gris"
    }
]

    for eye_color in eye_colors:
        try:
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_EYE_COLOR,
                filter_data={"flag": eye_color["flag"].lower()},
                update_data=eye_color
            )
            # DebugService.app_debug_print("upserted result:", result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")


async def create_default_religions():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Upsert default religion - update if they exist, insert if they don't.
    """
    religions = [
        {
            "name": "Christianisme",
            "description_str": "Religion monothéiste basée sur les enseignements de Jésus-Christ, avec des branches comme le catholicisme, le protestantisme et l'orthodoxie.",
            "flag": "christianity"
        },
        {
            "name": "Islam",
            "description_str": "Religion monothéiste fondée sur les enseignements du prophète Mahomet, avec des courants principaux tels que le sunnisme et le chiisme.",
            "flag": "islam"
        },
        {
            "name": "Hindouisme",
            "description_str": "Ensemble de traditions religieuses et philosophiques originaires du sous-continent indien, caractérisées par une diversité de dieux et de pratiques spirituelles.",
            "flag": "hinduism"
        },
        {
            "name": "Bouddhisme",
            "description_str": "Philosophie et religion fondée sur les enseignements de Siddhartha Gautama (Bouddha), visant à comprendre la nature de la souffrance et atteindre l'illumination.",
            "flag": "buddhism"
        },
        {
            "name": "Judaïsme",
            "description_str": "Religion monothéiste des peuples juifs, fondée sur l'alliance entre Dieu et Abraham et guidée par la Torah et d'autres textes sacrés.",
            "flag": "judaism"
        },
        {
            "name": "Sikhisme",
            "description_str": "Religion monothéiste fondée au XVe siècle dans la région du Punjab, qui prône la dévotion à un Dieu unique et l'égalité entre tous les êtres humains.",
            "flag": "sikhism"
        }
    ]

    for religion in religions:
        try:
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_RELIGION,
                filter_data={"flag": religion["flag"].lower()},
                update_data=religion
            )
            # DebugService.app_debug_print("upserted result:", result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")

async def create_default_saas_config():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Upsert default SaaS config - update if they exist, insert if they don't.
    """
    default_theme_data = {
        "name": "senat_digit apps",
        "is_default": True,
        "is_current_theme": True,
    }
    try:
        # Perform upsert for theme data
        result = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.REF_THEME,
            filter_data={"is_default": default_theme_data["is_default"]},
            update_data=default_theme_data,
        )
        DebugService.app_debug_print(f"\n\n default_theme : {result}")

        contact_infos = [
            {
                "contact_info": "support@senat_digit.digipublic.app",
                "is_activated": True,
                "purpose": ESaasConfigPurpose.CUSTOMER_SUPPORT.value,
                "info_kind": ESaasConfigInfoKind.EMAIL_ADDRESS.value,
                "ref_entity_id": None,
            },
            {
                "contact_info": "243 997 854 422",
                "is_activated": True,
                "purpose": ESaasConfigPurpose.CUSTOMER_SUPPORT.value,
                "info_kind": ESaasConfigInfoKind.PHONE_NUMBER.value,
                "ref_entity_id": None,
            },
            {
                "contact_info": "info@senat_digit.digipublic.app",
                "is_activated": True,
                "purpose": ESaasConfigPurpose.GLOBAL.value,
                "info_kind": ESaasConfigInfoKind.EMAIL_ADDRESS.value,
                "ref_entity_id": None,
            },
            {
                "contact_info": "243 997 854 422",
                "is_activated": True,
                "purpose": ESaasConfigPurpose.GLOBAL.value,
                "info_kind": ESaasConfigInfoKind.PHONE_NUMBER.value,
                "ref_entity_id": None,
            },
            {
                "contact_info": "Kinshasa, R.D. Congo.",
                "is_activated": True,
                "purpose": ESaasConfigPurpose.GLOBAL.value,
                "info_kind": ESaasConfigInfoKind.ADDRESS.value,
                "ref_entity_id": None,
            },
        ]
        saas_config_info = {
            "theme_id": result["id"],
            "sms_sender_name": "SenatDigit",
            "contact_info": contact_infos,
            "currency_exchange_setup_scope": CurrencyExchangeSetupScope.SYSTEM.value,
        }



        # Perform upsert for SaaS config
        result = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            filter_data={"sms_sender_name": saas_config_info["sms_sender_name"]},
            update_data=saas_config_info,
        )
        DebugService.app_debug_print(f"Upsert result: {result}")
    except ValueError as e:
        DebugService.app_debug_print(f"Error: {e}")
    except PermissionError as e:
        DebugService.app_debug_print(f"Permission Error: {e}")


async def create_default_colors():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default colors if they do not already exist.
    """
    color_datas = [
    {"name":"rouge", "hex_code":"FF0000", "description":"Couleur rouge", "flag":"rouge"},
    {"name":"vert", "hex_code":"00FF00", "description":"Couleur verte", "flag":"vert"},
    {"name":"bleu", "hex_code":"0000FF", "description":"Couleur bleue", "flag":"bleu"},
    {"name":"jaune", "hex_code":"FFFF00", "description":"Couleur jaune", "flag":"jaune"},
    {"name":"noir", "hex_code":"000000", "description":"Couleur noire", "flag":"noir"},
    {"name":"blanc", "hex_code":"FFFFFF", "description":"Couleur blanche", "flag":"blanc"},
    {"name":"gris", "hex_code":"808080", "description":"Couleur grise", "flag":"gris"},
    {"name":"rose", "hex_code":"FFC0CB", "description":"Couleur rose", "flag":"rose"},
    {"name":"orange", "hex_code":"FFA500", "description":"Couleur orange", "flag":"orange"},
    {"name":"violet", "hex_code":"800080", "description":"Couleur violette", "flag":"violet"},
    {"name":"marron", "hex_code":"A52A2A", "description":"Couleur marron", "flag":"marron"},
    {"name":"cyan", "hex_code":"00FFFF", "description":"Couleur cyan", "flag":"cyan"},
    {"name":"magenta", "hex_code":"FF00FF", "description":"Couleur magenta", "flag":"magenta"},
    {"name":"turquoise", "hex_code":"40E0D0", "description":"Couleur turquoise", "flag":"turquoise"},
    {"name":"beige", "hex_code":"F5F5DC", "description":"Couleur beige", "flag":"beige"},
    {"name":"bleu ciel", "hex_code":"87CEEB", "description":"Couleur bleu ciel", "flag":"bleu_ciel"},
    {"name":"vert clair", "hex_code":"90EE90", "description":"Couleur vert clair", "flag":"vert_clair"},
    {"name":"rouge foncé", "hex_code":"8B0000", "description":"Couleur rouge foncé", "flag":"rouge_fonce"},
    {"name":"bleu marine", "hex_code":"000080", "description":"Couleur bleu marine", "flag":"bleu_marine"},
    {"name":"or", "hex_code":"FFD700", "description":"Couleur dorée", "flag":"or"},
]
    for color in color_datas:
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_COLOR,filter_data={"flag":color['flag']},update_data=color)
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")


async def create_default_marital_statuses():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default marital statuses if they do not already exist.
    """
    marital_statuses = [
        {'name': 'célibataire', 'description': "Personne qui n'est pas mariée.", 'flag': 'celibataire'},
        {'name': 'marié (e)', 'description': 'Personne engagée dans une union matrimoniale.', 'flag': 'marie_e'},
        {'name': 'divorcé (e)', 'description': 'Personne dont le mariage a été légalement dissous.', 'flag': 'divorce_e'},
        {'name': 'veuf/veuve', 'description': 'Personne dont le conjoint est décédé.', 'flag': 'veuf_veuve'},
        {'name': 'pacsé (e)', 'description': 'Personne engagée dans un pacte civil de solidarité.', 'flag': 'pacse_e'},
        {'name': 'séparé (e)', 'description': 'Personne légalement ou de fait séparée de son conjoint.', 'flag': 'separe_e'},
        {'name': 'concubinage/union libre', 'description': 'Personne vivant en union libre sans être mariée.', 'flag': 'concubinage_union_libre'},
        {'name': 'non précisé', 'description': 'Statut marital non précisé ou inconnu.', 'flag': 'non_precise'}

    ]
    for marital in marital_statuses:
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_MARITAL_STATUS,filter_data={"flag":marital['flag']},update_data=marital)
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")
    # DebugService.app_debug_print("Default marital statuses created or updated.")

async def create_default_fields_of_study():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default fields of study if they do not already exist.
    """
    fields_of_studies = [
        {"name": "informatique", "description": "Étude des systèmes informatiques, logiciels et réseaux.", "flag": "informatique"},
        {"name": "médecine", "description": "Étude de la science médicale et des soins de santé.", "flag": "medecine"},
        {"name": "droit", "description": "Étude des systèmes juridiques et des lois.", "flag": "droit"},
        {"name": "génie civil", "description": "Étude de la conception, construction et maintenance des infrastructures.", "flag": "genie_civil"},
        {"name": "économie", "description": "Étude des systèmes économiques, finances et marchés.", "flag": "economie"},
        {"name": "littérature", "description": "Étude des œuvres littéraires et de l'analyse des textes.", "flag": "litterature"},
        {"name": "biologie", "description": "Étude des organismes vivants et des systèmes biologiques.", "flag": "biologie"},
        {"name": "mathématiques", "description": "Étude des concepts mathématiques et des algorithmes.", "flag": "mathematiques"},
        {"name": "physique", "description": "Étude des propriétés fondamentales de la matière et de l'énergie.", "flag": "physique"},
        {"name": "chimie", "description": "Étude des propriétés, transformations et réactions chimiques.", "flag": "chimie"},
        {"name": "architecture", "description": "Étude de la conception et de la construction des bâtiments.", "flag": "architecture"},
        {"name": "psychologie", "description": "Étude des comportements et processus mentaux humains.", "flag": "psychologie"},
        {"name": "histoire", "description": "Étude des événements passés de l'humanité.", "flag": "histoire"},
        {"name": "sciences politiques", "description": "Étude des systèmes politiques et des relations internationales.", "flag": "sciences_politiques"},
        {"name": "sociologie", "description": "Étude des sociétés humaines et des interactions sociales.", "flag": "sociologie"},
        {"name": "géographie", "description": "Étude des phénomènes géographiques et des relations entre les sociétés et leur espace.", "flag": "geographie"},
        {"name": "philosophie", "description": "Étude des questions fondamentales sur l'existence, la connaissance et la morale.", "flag": "philosophie"},
        {"name": "art et design", "description": "Étude des pratiques artistiques et de la création visuelle.", "flag": "art_et_design"},
        {"name": "ingénierie électrique", "description": "Étude des concepts liés à l'électricité et aux systèmes électroniques.", "flag": "ingenierie_electrique"},
        {"name": "gestion des affaires", "description": "Étude des stratégies de gestion, marketing et finance.", "flag": "gestion_des_affaires"},
        {"name": "langues étrangères", "description": "Étude des langues non maternelles et des cultures associées.", "flag": "langues_etrangeres"},
        {"name": "arts", "description": "Ensemble des disciplines artistiques incluant la peinture, la sculpture, la danse, etc.", "flag": "arts"},
        {"name": "communication", "description": "Étude des processus de communication et des médias.", "flag": "communication"},
        {"name": "marketing", "description": "Étude des stratégies de promotion et de mise sur le marché de produits ou services.", "flag": "marketing"},
        {"name": "finance", "description": "Étude des systèmes financiers, investissements et gestion des capitaux.", "flag": "finance"},
        {"name": "sciences de la santé", "description": "Étude des disciplines liées aux soins de santé et à la prévention.", "flag": "sciences_de_la_sante"},
        {"name": "sciences de l'information", "description": "Étude de la gestion de l'information et des systèmes informatiques.", "flag": "sciences_de_linformation"},
        {"name": "sciences de la terre", "description": "Étude des structures, des processus et de l'histoire de la Terre.", "flag": "sciences_de_la_terre"},
        {"name": "sciences de la vie", "description": "Étude des organismes vivants et des processus biologiques.", "flag": "sciences_de_la_vie"},
        {"name": "sciences sociales", "description": "Étude des comportements humains dans les contextes sociaux.", "flag": "sciences_sociales"},
        {"name": "sciences humaines", "description": "Étude des disciplines centrées sur l'humain comme l'histoire, la philosophie, etc.", "flag": "sciences_humaines"},
        {"name": "sciences appliquées", "description": "Application des connaissances scientifiques à des problématiques pratiques.", "flag": "sciences_appliquees"},
        {"name": "sciences naturelles", "description": "Étude des phénomènes naturels à travers les disciplines comme la biologie, la chimie.", "flag": "sciences_naturelles"},
        {"name": "sciences formelles", "description": "Étude des disciplines basées sur des systèmes formels comme les mathématiques et la logique.", "flag": "sciences_formelles"},
        {"name": "sciences de l'ingénieur", "description": "Étude des principes d'ingénierie pour la conception et la fabrication.", "flag": "sciences_de_lingenieur"},
        {"name": "sciences de la communication", "description": "Étude approfondie des techniques et théories de communication.", "flag": "sciences_de_la_communication"},
        {"name": "sciences de la gestion", "description": "Étude des méthodes de gestion et de prise de décision dans les organisations.", "flag": "sciences_de_la_gestion"},
        {"name": "sciences de la santé publique", "description": "Étude de la santé au niveau communautaire et populationnel.", "flag": "sciences_de_la_sante_publique"},
        {"name": "sciences de la nutrition", "description": "Étude des apports nutritionnels et de leur impact sur la santé.", "flag": "sciences_de_la_nutrition"},
        {"name": "sciences de la sécurité", "description": "Étude des mesures et stratégies pour assurer la sécurité des individus et des données.", "flag": "sciences_de_la_securite"},
        {"name": "sciences de la technologie", "description": "Étude des technologies et de leur impact sur la société.", "flag": "sciences_de_la_technologie"},
        {"name": "sciences de la culture", "description": "Étude des cultures humaines et de leurs interactions.", "flag": "sciences_de_la_culture"},
        {"name": "sciences de la société", "description": "Étude des structures sociales et des dynamiques sociétales.", "flag": "sciences_de_la_societe"},
        {"name": "sciences de la philosophie", "description": "Étude approfondie des courants philosophiques et des concepts fondamentaux.", "flag": "sciences_de_la_philosophie"},
        {"name": "sciences de la littérature", "description": "Analyse des œuvres littéraires et des courants littéraires.", "flag": "sciences_de_la_litterature"},
        {"name": "sciences de la linguistique", "description": "Étude scientifique des langues et de leurs structures.", "flag": "sciences_de_la_linguistique"},
        {"name": "sciences de la musique", "description": "Étude des aspects théoriques et pratiques de la musique.", "flag": "sciences_de_la_musique"},
        {"name": "sciences de l'art", "description": "Étude des disciplines artistiques et des pratiques créatives.", "flag": "sciences_de_lart"},
        {"name": "sciences de la danse", "description": "Étude des pratiques chorégraphiques et des performances dansées.", "flag": "sciences_de_la_danse"},
        {"name": "sciences de la théologie", "description": "Étude des doctrines religieuses et des traditions spirituelles.", "flag": "sciences_de_la_theologie"},
        {"name": "sciences de la religion", "description": "Étude des systèmes religieux et de leurs interactions dans les sociétés.", "flag": "sciences_de_la_religion"},
        {"name": "sciences de la spiritualité", "description": "Étude des pratiques spirituelles et des croyances associées.", "flag": "sciences_de_la_spiritualite"},
        {"name": "sciences de la mythologie", "description": "Étude des récits mythologiques et de leur symbolisme.", "flag": "sciences_de_la_mythologie"},
        {"name": "sciences de la folkloristique", "description": "Étude des traditions orales et des pratiques culturelles populaires.", "flag": "sciences_de_la_folkloristique"},
        {"name": "sciences de la philologie", "description": "Étude des textes anciens et de l'évolution des langues.", "flag": "sciences_de_la_philologie"},
        {"name": "sciences de la paléontologie", "description": "Étude des fossiles et des anciennes formes de vie sur Terre.", "flag": "sciences_de_la_paleontologie"}
    ]
    for field_of in fields_of_studies :
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_FIELD_OF_STUDY,filter_data={"flag":field_of['flag']},update_data=field_of)
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")
    # DebugService.app_debug_print("Default fields of study created or updated.")


async def create_default_documents():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default document types if they do not already exist.
    """
    documents = [
        {"name": "passeport", "description_str": "Document de voyage délivré par un gouvernement pour voyager à l'étranger.", "description_html": "<p>Document de voyage délivré par un gouvernement pour voyager à l'étranger.</p>", "flag": "passeport"},
        {"name": "carte nationale d'identité", "description_str": "Document officiel prouvant l'identité d'une personne.", "description_html": "<p>Document officiel prouvant l'identité d'une personne.</p>", "flag": "carte_nationale_didentite"},
        {"name": "carte de creuseur", "description_str": "Document officiel délivré aux creuseurs autorisés à exercer leur activité.", "description_html": "<p>Document officiel délivré aux creuseurs autorisés à exercer leur activité.</p>", "flag": "carte_de_creuseur"},
        {"name": "permis de séjour", "description_str": "Document permettant à un étranger de résider légalement dans un pays.", "description_html": "<p>Document permettant à un étranger de résider légalement dans un pays.</p>", "flag": "permis_de_sejour"},
        {"name": "justificatif de domicile", "description_str": "Document prouvant le lieu de résidence (facture d'électricité, de gaz, etc.).", "description_html": "<p>Document prouvant le lieu de résidence (facture d'électricité, de gaz, etc.).</p>", "flag": "justificatif_de_domicile"},
        {"name": "cv (curriculum vitae)", "description_str": "Document listant les expériences professionnelles et compétences.", "description_html": "<p>Document listant les expériences professionnelles et compétences.</p>", "flag": "cv"},
        {"name": "lettre de motivation", "description_str": "Document écrit pour expliquer la motivation à occuper un poste.", "description_html": "<p>Document écrit pour expliquer la motivation à occuper un poste.</p>", "flag": "lettre_de_motivation"},
        {"name": "diplômes et certificats de formation", "description_str": "Documents prouvant la réussite à un examen ou à une formation.", "description_html": "<p>Documents prouvant la réussite à un examen ou à une formation.</p>", "flag": "diplomes_et_certificats"},
        {"name": "lettres de recommandation", "description_str": "Documents recommandant une personne pour un poste ou une fonction.", "description_html": "<p>Documents recommandant une personne pour un poste ou une fonction.</p>", "flag": "lettres_de_recommandation"},
        {"name": "certificats de travail précédents", "description_str": "Documents attestant les emplois occupés précédemment.", "description_html": "<p>Documents attestant les emplois occupés précédemment.</p>", "flag": "certificats_de_travail"},
        {"name": "numéro de sécurité sociale", "description_str": "Document indiquant le numéro de sécurité sociale d'une personne.", "description_html": "<p>Document indiquant le numéro de sécurité sociale d'une personne.</p>", "flag": "numero_securite_sociale"},
        {"name": "relevé d'identité bancaire (rib)", "description_str": "Document contenant les informations bancaires pour effectuer des transactions.", "description_html": "<p>Document contenant les informations bancaires pour effectuer des transactions.</p>", "flag": "rib"},
        {"name": "attestation de mutuelle ou d'assurance santé", "description_str": "Document prouvant l'affiliation à une mutuelle ou assurance santé.", "description_html": "<p>Document prouvant l'affiliation à une mutuelle ou assurance santé.</p>", "flag": "attestation_assurance_sante"},
        {"name": "carte vitale", "description_str": "Carte permettant d'accéder aux services de sécurité sociale.", "description_html": "<p>Carte permettant d'accéder aux services de sécurité sociale.</p>", "flag": "carte_vitale"},
        {"name": "déclaration fiscale", "description_str": "Document déclarant les revenus annuels aux services fiscaux.", "description_html": "<p>Document déclarant les revenus annuels aux services fiscaux.</p>", "flag": "declaration_fiscale"},
        {"name": "numéro de contribuable", "description_str": "Document contenant le numéro fiscal d'une personne.", "description_html": "<p>Document contenant le numéro fiscal d'une personne.</p>", "flag": "numero_contribuable"},
        {"name": "contrat de travail signé", "description_str": "Contrat de travail signé entre l'employeur et l'employé.", "description_html": "<p>Contrat de travail signé entre l'employeur et l'employé.</p>", "flag": "contrat_de_travail"},
        {"name": "accord de confidentialité", "description_str": "Document attestant l'engagement à la confidentialité des informations.", "description_html": "<p>Document attestant l'engagement à la confidentialité des informations.</p>", "flag": "accord_confidentialite"},
        {"name": "charte informatique signée", "description_str": "Document attestant l'adhésion aux règles d'utilisation du système informatique.", "description_html": "<p>Document attestant l'adhésion aux règles d'utilisation du système informatique.</p>", "flag": "charte_informatique"},
        {"name": "engagement de respect des règles de l'entreprise", "description_str": "Document attestant l'engagement à respecter le règlement intérieur.", "description_html": "<p>Document attestant l'engagement à respecter le règlement intérieur.</p>", "flag": "engagement_regles_entreprise"},
        {"name": "certificat médical d'aptitude au travail", "description_str": "Document délivré par un médecin attestant l'aptitude au travail.", "description_html": "<p>Document délivré par un médecin attestant l'aptitude au travail.</p>", "flag": "certificat_aptitude_travail"},
        {"name": "attestation de formation aux premiers secours", "description_str": "Document attestant la formation aux gestes de premiers secours.", "description_html": "<p>Document attestant la formation aux gestes de premiers secours.</p>", "flag": "attestation_premiers_secours"},
        {"name": "visa de travail", "description_str": "Document officiel autorisant une personne à travailler dans un pays étranger.", "description_html": "<p>Document officiel autorisant une personne à travailler dans un pays étranger.</p>", "flag": "visa_travail"},
        {"name": "permis de travail", "description_str": "Document officiel autorisant une personne à exercer une activité professionnelle.", "description_html": "<p>Document officiel autorisant une personne à exercer une activité professionnelle.</p>", "flag": "permis_travail"},
        {"name": "traduction des documents étrangers", "description_str": "Traduction officielle des documents rédigés dans une autre langue.", "description_html": "<p>Traduction officielle des documents rédigés dans une autre langue.</p>", "flag": "traduction_documents"},
        {"name": "photographie d'identité", "description_str": "Photo d'identité officielle conforme aux standards légaux.", "description_html": "<p>Photo d'identité officielle conforme aux standards légaux.</p>", "flag": "photo_identite"},
        {"name": "attestation de casier judiciaire", "description_str": "Document attestant l'absence ou la présence d'antécédents judiciaires.", "description_html": "<p>Document attestant l'absence ou la présence d'antécédents judiciaires.</p>", "flag": "casier_judiciaire"},
        {"name": "carte grise", "description_str": "Document prouvant l'immatriculation d'un véhicule.", "description_html": "<p>Document prouvant l'immatriculation d'un véhicule.</p>", "flag": "carte_grise"},
        {"name": "certificat de contrôle technique", "description_str": "Document attestant que le véhicule a passé le contrôle technique.", "description_html": "<p>Document attestant que le véhicule a passé le contrôle technique.</p>", "flag": "controle_technique"},
        {"name": "attestation d'assurance automobile", "description_str": "Document prouvant que le véhicule est assuré.", "description_html": "<p>Document prouvant que le véhicule est assuré.</p>", "flag": "attestation_assurance_auto"},
        {"name": "permis de conduire professionnel", "description_str": "Permis autorisant la conduite de véhicules professionnels.", "description_html": "<p>Permis autorisant la conduite de véhicules professionnels.</p>", "flag": "permis_conduire_pro"},
        {"name": "certificat de formation de chauffeur professionnel", "description_str": "Document attestant la formation professionnelle d'un chauffeur.", "description_html": "<p>Document attestant la formation professionnelle d'un chauffeur.</p>", "flag": "certificat_chauffeur_pro"},
        {"name": "attestation de capacité de transport", "description_str": "Document attestant la capacité à gérer ou conduire un transport.", "description_html": "<p>Document attestant la capacité à gérer ou conduire un transport.</p>", "flag": "capacite_transport"},
        {"name": "carte professionnelle d'agent de l'état", "description_str": "Carte officielle prouvant le statut d'agent de l'état.", "description_html": "<p>Carte officielle prouvant le statut d'agent de l'état.</p>", "flag": "carte_agent_etat"},
        {"name": "attestation de nomination ou de recrutement", "description_str": "Document officiel attestant la nomination ou le recrutement dans un poste.", "description_html": "<p>Document officiel attestant la nomination ou le recrutement dans un poste.</p>", "flag": "attestation_nomination"},
        {"name": "déclaration sur l'honneur de non-condamnation", "description_str": "Déclaration attestant que la personne n'a pas été condamnée.", "description_html": "<p>Déclaration attestant que la personne n'a pas été condamnée.</p>", "flag": "declaration_non_condamnation"},
        {"name": "attestation de formation spécifique à l'emploi", "description_str": "Document attestant la formation spécifique pour un poste.", "description_html": "<p>Document attestant la formation spécifique pour un poste.</p>", "flag": "attestation_formation_emploi"}
    ]
    for doc in documents:
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_DOCUMENT,filter_data={"flag":doc['flag']},update_data=doc)
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")
    # DebugService.app_debug_print("Default documents created or updated.")


async def create_rbac_titles():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    rbac_titles = CORE_RBAC_TITLE_DB
    print(f"initiating create_rbac_titles:")
    async def recursive_rbac_title(item: Dict[str, Any], rbac_title_id: Optional[str] = None) -> Optional[str]:
        try:
            if "label" not in item or "flag" not in item:
                print(f"Skipping item missing label or flag: {item}")
                return None

            # Add parent reference
            item['rbac_title_id'] = rbac_title_id
            
            # Save title
            saved_title = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_TITLE,
                filter_data={"flag": item['flag']},
                update_data=item
            )
            
            # Validate saved title
            if not saved_title:
                print(f"Failed to save title: {item['label']}")
                return None
                
            saved_title_id = saved_title if isinstance(saved_title, str) else saved_title.get('id')
            if not saved_title_id:
                print(f"Invalid saved title format: {saved_title}")
                return None

            # Process permissions
            has_permission = "permissions" in item and isinstance(item["permissions"], list) and len(item["permissions"]) > 0
            print(f"saved title : {item['label']} as permissions: {has_permission}")
            if "permissions" in item and isinstance(item["permissions"], list):
                for permission_item in item["permissions"]:
                    await process_permission(permission_item, saved_title_id, generic_service)

            # Process endpoints
            if "endpoints" in item and isinstance(item["endpoints"], list):
                for endpoint_item in item["endpoints"]:
                    await process_endpoint(endpoint_item, saved_title_id, generic_service)

            # Process children recursively
            if "children" in item and isinstance(item["children"], list):
                for child_item in item["children"]:
                    await recursive_rbac_title(child_item, saved_title_id)  # Fixed: added await

            return saved_title_id

        except Exception as e:
            print(f"Error processing RBAC title {item.get('label', 'unknown')}: {e}")
            # Consider whether to re-raise or continue
            return None

    # Helper functions for better organization
    async def process_permission(permission_item: Dict[str, Any], title_id: str, service: GenericService):
        try:
            permission_item.pop('core_seeds', None)
            permission_data = {
                **permission_item,
                "rbac_title_id": title_id
            }
            
            saved_permission = await service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_PERMISSION,
                filter_data={'flag': permission_data['flag'], "rbac_title_id": title_id},
                update_data=permission_data
            )
            
            if saved_permission:
                permission_id = saved_permission if isinstance(saved_permission, str) else saved_permission.get('id')
                if permission_id and permission_data.get('is_accessible_to_all_profil') is True:
                    await add_restricted_profiles(permission_id, service)
                    
        except Exception as e:
            print(f"Error processing permission: {e}")

    async def process_endpoint(
        endpoint_item: Union[Dict[str, Any], List[Dict[str, Any]]], 
        title_id: str, 
        service: GenericService
    ):
        """
        Process endpoint items. Can handle single item or batch.
        """
        try:
            # Normalize input to list
            if isinstance(endpoint_item, dict):
                items = [endpoint_item]
            elif isinstance(endpoint_item, list):
                items = endpoint_item
            else:
                raise TypeError(f"Expected dict or list of dicts, got {type(endpoint_item)}")
            
            print(f"Processing {len(items)} endpoint(s) for title_id: {title_id}")
            
            # Process each item
            success_count = 0
            error_count = 0
            
            for item in items:
                item_result = await _process_single_endpoint(item, title_id, service)
                if item_result:
                    success_count += 1
                else:
                    error_count += 1
            
            print(f"Processed {success_count} endpoint(s) successfully, {error_count} failed")
            return success_count, error_count
            
        except Exception as e:
            format = format_exception("Error in process_endpoint", e)
            print(f"Error processing endpoint: {format}")
            return 0, 1 if items else 0

    async def _process_single_endpoint(
        endpoint_item: Dict[str, Any], 
        title_id: str, 
        service: GenericService
    ) -> bool:
        """
        Helper function to process a single endpoint item.
        Returns True if successful, False if failed.
        """
        try:
            # Validate required fields
            if 'label' not in endpoint_item:
                print(f"Missing 'label' in endpoint item: {endpoint_item}")
                return False
                
            if 'url' not in endpoint_item:
                print(f"Missing 'url' in endpoint item: {endpoint_item}")
                return False

            # Handle is_link_deleted: cascade delete the endpoint and all references
            if endpoint_item.get('is_link_deleted', False):
                existing_endpoint = await service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_ENDPOINT,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={"filter__url": endpoint_item['url']}
                )
                if existing_endpoint:
                    from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
                    rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
                    await rbac_role_service.cascade_delete_endpoint_references(service, existing_endpoint['id'])
                    print(f"🗑️ Cascade deleted endpoint (is_link_deleted=True): {endpoint_item['label']}")
                else:
                    print(f"⏭️  Endpoint already absent (is_link_deleted=True): {endpoint_item['url']}")
                return True

            # Create endpoint data with title_id
            endpoint_data = {
                **endpoint_item,
                "rbac_title_id": title_id
            }
            
            print(f"Processing endpoint: {endpoint_data['label']}")
            
            # Upsert to database
            await service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                filter_data={'url': endpoint_data['url'], "rbac_title_id": title_id},
                update_data=endpoint_data
            )
            
            return True
            
        except Exception as e:
            format = format_exception(f"Error processing endpoint: {endpoint_item.get('label', 'Unknown')}", e)
            print(f"Error: {format}")
            return False
    
    async def add_restricted_profiles(permission_id: str, service: GenericService):
        try:
            restricted_profil_list = await service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT,
                query={"filter__is_activated": True},
                all_data=True
            )
            
            for profil_item in restricted_profil_list:
                new_data = {
                    "rbac_profile_id": str(profil_item['id']),
                    "targeted_id": str(permission_id),
                }
                await service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={
                        "targeted_id": new_data['targeted_id'],
                        'rbac_profile_id': new_data['rbac_profile_id']
                    },
                    update_data=new_data
                )
        except Exception as e:
            print(f"Error adding restricted profiles: {e}")

    # Main execution
    try:
        # Assuming rbac_titles is a list of root items
        for index,title_item in enumerate(rbac_titles):
            print(f" rbac_title name : {title_item['label']} index : {index}")
            await recursive_rbac_title(title_item)
            
    except Exception as e:
        print(f"Fatal error in create_rbac_titles: {e}")
        raise


async def create_budget_years():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default budget year records if they do not already exist.
    """
    budget_years = [
        {
            "year": 2024,
            "is_current_year":True,
            "order_by":0
        },
        {
            "year": 2025,
            "is_current_year":False,
            "order_by":1
        },

    ]
    for index,year in enumerate(budget_years):
        try:
            # print(f"\n\n index : {index} | year :  {year} \n")
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_BUDGET_YEAR,
                filter_data={"year":year['year'],"is_current_year":year['is_current_year']},
                update_data=year
            )
            # print(f"\n\n result : {result} \n")
            if index == 1 :
                new_year = {
                    **year,
                    "last_year_id":result['id']
                }
                result = await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.REF_BUDGET_YEAR,
                    filter_data={"year":year['year'],"is_current_year":year['is_current_year']},
                    update_data=new_year
                )
                # print(f"upserted result. : {result}")
        except ValueError as e:
            print(f"Error: {e}")
        except PermissionError as e:
            print(f"Permission Error: {e}")
    # DebugService.app_debug_print("Default langs created or updated.")

async def create_languages():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default languages records if they do not already exist.
    """
    langs = [
        {
            "name": "English",
            "short_code": "en",
            "long_code": "en-US"
        },
        {
            "name": "Français",
            "short_code": "fr",
            "long_code": "fr-FR"
        },
        {
            "name": "Deutsch",
            "short_code": "de",
            "long_code": "de-DE"
        },
        {
            "name": "Español",
            "short_code": "es",
            "long_code": "es-ES"
        },
        {
            "name": "Italiano",
            "short_code": "it",
            "long_code": "it-IT"
        },
        {
            "name": "Русский",
            "short_code": "ru",
            "long_code": "ru-RU"
        },
        {
            "name": "हिंदी",
            "short_code": "hi",
            "long_code": "hi-IN"
        },
        {
            "name": "日本語",
            "short_code": "ja",
            "long_code": "ja-JP"
        },
        {
            "name": "中文（普通话）",
            "short_code": "zh",
            "long_code": "zh-CN"
        },
        {
            "name": "Lingala",
            "short_code": "ln",
            "long_code": "ln-CD"
        }
    ]
    for lang in langs:
        try:
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_LANGUAGE,
                filter_data={"name":lang['name']},
                update_data=lang)
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")
    # DebugService.app_debug_print("Default langs created or updated.")


async def create_sudo_action_types():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default period types records if they do not already exist.
    """
    sudo_action_types = [
        {
            "name": "Golden number",
            "flag":ESudoActionTypeFlag.GOLDEN_NUMBER.value,
            "description_str":"Dans votre application SenatDigit Auth, cliquer le nombre identique qui s'affiche sur votre écran afin de confirmer l'opération",
            "totp_app_description_str":"Appuyez le nombre identique à celui qui s'affiche afin de confirmer l'opération",
            "title":"Confirmation de l'opération par un nombre identique",
        },
        {
            "name": "TOTP",
            "flag":ESudoActionTypeFlag.TOTP.value,
            "description_str":"Dans votre application SenatDigit Auth, appuyer sur le nombre à minuteur afin de confirmer l'opération",
            "totp_app_description_str":"Appuyer sur le nombre à minuteur afin de confirmer l'opération",
            "title":"Confirmation de l'opération par TOTP",
        },
        {
            "name": "Local auth",
            "flag":ESudoActionTypeFlag.LOCAL_AUTH.value,
            "description_str":"Dans votre application SenatDigit Auth, utilisez l'une de vos méthodes d'authentification locale(FaceID, emprunte digitale, Code PIN,...) afin de confirmer l'opération",
            "totp_app_description_str":"Veuillez confirmer l'opération en utilisant l'une de vos méthodes d'authentification locale(FaceID, emprunte digitale, Code PIN,...)",
            "title":"Confirmation de l'opération par authentification locale (FaceID, emprunte digitale, Code PIN,...)",
        },
        # {
        #     "name": "QR Code",
        #     "flag":ESudoActionTypeFlag.QR_CODE.value,
        #     "description_str":"Scannez le code QR avec votre application SenatDigit Auth pour confirmer l'opération",
        #     "totp_app_description_str":"Scannez le code QR afin de confirmer l'opération",
        #     "title":"Confirmation de l'opération par code QR",
        # },
        {
            "name": "Phone",
            "flag":ESudoActionTypeFlag.PHONE.value,
            "description_str":"Un code de vérification sera envoyé par SMS à votre numéro de téléphone afin de confirmer l'opération",
            "totp_app_description_str":"Entrez le code de vérification reçu par SMS afin de confirmer l'opération",
            "title":"Confirmation de l'opération par SMS",
        },
        {
            "name": "Email",
            "flag":ESudoActionTypeFlag.EMAIL.value,
            "description_str":"Un code de vérification sera envoyé à votre adresse email afin de confirmer l'opération",
            "totp_app_description_str":"Entrez le code de vérification reçu par email afin de confirmer l'opération",
            "title":"Confirmation de l'opération par email",
        },
        
    ]
    for data in sudo_action_types:
        try:
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
                filter_data={"flag":data['flag']},
                update_data=data
            )
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")
 
async def create_bank_types():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default access records if they do not already exist.
    """
    bank_account_types = [
        {
            "name": "Banque commerciale",
            "flag": "commercial_bank",
            "description_str":"Banque classique, offre des services bancaires traditionnels : comptes courants, épargne, prets, etc."
        },
        {
            "name": "Banque centrale",
            "flag":"central_bank",
            "description_str":"Gestionnaire de la monnaie nationale, contrôle la politique monétaire, assure la stabilité monétaire."
        },
        {
            "name": "Banques coopératives ou mutualistes",
            "flag": "cooperative_bank",
            "description_str":"Appartiennent à leurs clients (sociétaires) et fonctionnent sur un modèle coopératif. But : servir les membres, pas maximiser les profits."
        },
        {
            "name": "Banques en ligne / néobanques",
            "flag": "online_bank",
            "description_str":"Opèrent principalement ou uniquement via Internet. Frais réduits, applications mobiles, services rapides."
        },
        {
            "name": "Banques offshore",
            "flag":"offshore_bank",
            "description_str":"Basées dans des juridictions à faible fiscalité. Utilisées pour l'optimisation fiscale ou la confidentialité."
        },
        {
            "name": "Banque d'investissement",
            "flag": "investment_bank",
            "description_str":"Spécialisées dans les opérations financières complexes : fusions-acquisitions, levées de fonds, introduction en bourse, etc."
        },
        {
            "name": "Banque d'assurance",
            "flag": "insurance_bank",
            "description_str":"Offrent des produits d'assurance et peuvent gérer des fonds d'assurance."
        },
        {
            "name": "Banque de développement",
            "flag": "development_bank",
            "description_str":"Financement à long terme pour des projets de développement (infrastructure, énergie, éducation). Souvent soutenues par l'État ou des institutions internationales."
        },
        {
            "name": "Banque de réserve",
            "flag": "reserve_bank",
            "description_str":"Gestionnaire des réserves monétaires d'un pays. Assure la stabilité monétaire."
        },
        {
            "name": "Banque de crédit",
            "flag": "credit_bank",
            "description_str":"Pret d'argent à des particuliers ou des entreprises."
        },
        {
            "name": "Banque de dépôt",
            "flag": "deposit_bank",
            "description_str":"Gestionnaire de trésorerie. Pret d'argent à des particuliers ou des entreprises."
        },
        {
            "name": "Banque de placement",
            "flag": "investment_bank",
            "description_str":"Gestionnaire de trésorerie. Pret d'argent à des particuliers ou des entreprises."
        },


    ]
    for bat in bank_account_types:
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_BANK_TYPE,filter_data={"flag":bat['flag']},update_data=bat)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")

async def create_rbac_actions():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default rbac actions records if they do not already exist.
    """
    rbac_actions = [
        {
            "label": "Créer",
            "flag":ERbacActionFlag.TABLE_ACTION_ADD.value,
            "hard_code_flag":"creation_action_flag",
            "is_standalone":True,
            "description_str":"Action de créer"
        },
        {
            "label": "Aperçu",
            "flag":ERbacActionFlag.TABLE_ACTION_VIEW.value,
            "hard_code_flag":"overview_action_flag",
            "is_standalone":True,
            "description_str":"Action de voir l'aperçu"
        },
        {
            "label": "Modifier",
            "flag":ERbacActionFlag.TABLE_ACTION_UPDATE.value,
            "hard_code_flag":"table_action_update_flag",
            "is_standalone":True,
            "description_str":"Action de modifier"
        },
        {
            "label": "Supprimer",
            "flag":ERbacActionFlag.TABLE_ACTION_DELETE.value,
            "hard_code_flag":"table_action_delete_flag",
            "is_standalone":True,
            "description_str":"Action de supprimer"
        },
        {
            "label": "Créer l'enfant",
            "flag":ERbacActionFlag.TABLE_ACTION_ADD_CHILD.value,
            "hard_code_flag":"table_action_add_child_flag",
            "is_standalone":True,
            "description_str":"Action de créer un enfant"
        },
        {
            "label": "Télécharger",
            "flag":ERbacActionFlag.COMMON_DOWNLOAD_ACTION.value,
            "hard_code_flag":"common_action_download_flag",
            "is_standalone":True,
            "description_str":"Action de créer un enfant"
        },
        {
            "label":"Téléverser",
            "flag":ERbacActionFlag.COMMON_UPLOAD_ACTION_FILE.value,
            "hard_code_flag":"common_action_upload_file_flag",
            "is_standalone":True,
            "description_str":"Action de téléverser un fichier"
        },
        {
            "label": "Verrouiller",
            "flag":ERbacActionFlag.COMMON_LOCK_ACTION.value,
            "hard_code_flag":"common_lock_action_flag",
            "is_standalone":True,
            "description_str":"Action de verrouiller"
        },
        {
            "label": "Déverrouiller",
            "flag":ERbacActionFlag.COMMON_UNLOCK_ACTION.value,
            "hard_code_flag":"common_unlock_action_flag",
            "is_standalone":True,
            "description_str":"Action de déverrouiller"
        },
    ]
    for data in rbac_actions:
        try:
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                filter_data={"hard_code_flag":data['hard_code_flag']},
                update_data=data
            )
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")

async def create_collections():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default collections if they do not already exist.
    """
    for collection_tuple in COLLECTIONS:
        try:
            key = collection_tuple[0]
            collection_name = collection_tuple[1]
            exposed = collection_tuple[3]

            # Get verbose if it exists, otherwise use a default value
            verbose = collection_tuple[4] if len(collection_tuple) > 4 else f"Collection {collection_name}"

            # Generate a flag from the verbose name
            import re
            flag = re.sub(r"[^a-zA-Z0-9]", "_", verbose.lower())
            flag = f"{flag}_{len(verbose)}"

            DebugService.app_debug_print(f"\n collection_name : {collection_name} | verbose : {verbose} | key : {key} | exposed : {exposed} | flag: {flag}",True)

            new_data = {
                "collection_key": key,
                "collection_name": collection_name,
                "is_exposed": exposed,
                "verbose": verbose,
                "flag": flag
            }

            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_COLLECTION,
                filter_data={"collection_key": new_data['collection_key']},
                update_data=new_data
            )
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}",True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}",True)

async def create_children_display_types():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default children display types if they do not already exist.
    """
    children_display_types = [
        {
            "flag": EMenuChildrenDisplayFlag.NONE.value,
            "label": "Aucun",
            "is_default":False,
        },
        {
            "flag": EMenuChildrenDisplayFlag.LEFT_SIDE_MENU.value,
            "label": "Menu gauche",
            "is_default":False,
        },
        {
            "flag": EMenuChildrenDisplayFlag.RIGHT_SIDE_MENU.value,
            "label": "Menu droit",
            "is_default":False,
        },
        {
            "flag": EMenuChildrenDisplayFlag.TOP_BAR_MENU.value,
            "label": "Menu barre supérieure",
            "is_default":False,
        },
        {
            "flag": EMenuChildrenDisplayFlag.CENTERED_CARD_MENU.value,
            "label": "Menu carte centrale",
            "is_default":True,
        },
        {
            "flag": EMenuChildrenDisplayFlag.GRID_CHILDREN_CONTENT.value,
            "label": "Contenu en grille des enfants",
            "is_default":False,
        },
    ]
    for d_type in children_display_types:
        try: 
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_CHILDREN_DISPLAY_TYPE,
                filter_data={"flag": d_type['flag']},
                update_data=d_type
            )
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}",True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}",True)

async def create_data_display_types():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default children display types if they do not already exist.
    """
    data_display_types = [
        {
             "flag": EDataDisplayTypeFlag.NONE.value,
             "label": "Aucun"
        },
        {
             "flag": EDataDisplayTypeFlag.REGULAR_TABLE.value,
             "label": "Tableau régulier"
        },
        {
             "flag": EDataDisplayTypeFlag.LIST_TILE.value,
             "label": "Liste en tuile"
        },
        {
             "flag": EDataDisplayTypeFlag.CARD.value,
             "label": "Carte"
        },
        {
             "flag": EDataDisplayTypeFlag.TREE_TABLE.value,
             "label": "Tableau arborescent"
        },
        {
             "flag": EDataDisplayTypeFlag.ORG_CHART.value,
             "label": "Organigramme"
        },
         
    ]
    for data_display_type in data_display_types:
        try: 
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_DATA_DISPLAY_TYPE,
                filter_data={"flag": data_display_type['flag']},
                update_data=data_display_type
            )
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}",True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}",True)


async def create_senat_digit_module_rbac():
    """Seed RBAC for every Senat-Digit feature module.

    Reads the JSON catalogues in each module's `seeds/` directory through
    the `*_seed_loader.py` bridge functions, then drives them through the
    same `RbacRoleService.seed_rbac_from_module` path the legacy reference
    catalogue uses.

    Closes the F2 wiring gap surfaced by the live seed run on 2026-04-29:
    the loaders existed since §3.5 but `init_data()` never called them, so
    `/verb/resource` endpoints were silently absent from `rbac_endpoint`
    after a fresh deploy.
    """
    from app.modules.core.seeds.senat_digit_modules_rbac import (
        build_senat_digit_modules_rbac_title_db,
    )
    from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService

    rbac_title_db = build_senat_digit_modules_rbac_title_db()
    rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
    print(
        f"\n📦 [Senat-Digit modules] Seeding RBAC for "
        f"{len(rbac_title_db)} modules..."
    )
    await rbac_role_service.seed_rbac_from_module(rbac_title_db)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()  # Get the current event loop
    loop.run_until_complete(init_data())  # Run without creating a nested loop


