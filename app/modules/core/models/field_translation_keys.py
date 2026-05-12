from app.modules.core.enums.type_enum import EGlobalStatus

#app/constants/field_translation_keys.py
from copy import deepcopy
from enum import Enum
# Translation dictionary for properties
from app.modules.auth.enums.auth import ELoginStatus
from app.modules.auth.enums.common import ERbacActionFlag, ERbacComponentFlag
from app.modules.core.enums.type_enum import AccountStatusFlag, AppGeneratorType, EAccountMovementFlag, EAccountMovementStatus, EAccountMovementType, EAppGroupFlag, ECollectionCrudInfoFlag, ECoolBoxStatus, EDataDisplayTypeFlag, EExChainInstDesignation, EExpenseAccountType, EExpenseChainBeneficiaryType, EExpenseClacificationStatusFlag, EExpenseOpsBeneficiaryType, EExpenseOpsPaymentActorType, EExpensePaymentBeneficiaryReceiverType, EExpensePaymentType, EExpenseVerificatorType, EGender, EGlobalStatus, EJWTTokenType, ELoginResetPasswordFailStatus, EMenuChildrenDisplayFlag, EMultipleValidationStatus, EMultipleValidationType, EOperationStatus, EParentChildHead, ERegistrationOrigin, ERestoreStatus, ESrcAttachment, ESubmissionOperationStatusFlag, ETemplateEngineType, ETransactionStatus, EUserDeviceStatus, ExpenseChainTransactionStatusFlag, EOperationStatusFlag, ExpenseTransactionStatusFlag, OutputDataType
from app.modules.auth.enums.mfa import EMfaPurpose, MFaFlag
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag, ERlsAccessTypeFlag, ESudoActionAccessTargetedTypeFlag, ESudoActionAccessTypeFlag


DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGE_CODES = ("en", "fr", "de", "es", "it", "ru", "hi", "ja", "zh", "ln")
FALLBACK_LANGUAGE = DEFAULT_LANGUAGE

MONTH_NAMES = {
    "en": ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"],
    "fr": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "es": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
    "it": ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"],
    "ru": ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
            "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    "ja": ["1月", "2月", "3月", "4月", "5月", "6月",
            "7月", "8月", "9月", "10月", "11月", "12月"],
    "zh": ["1月", "2月", "3月", "4月", "5月", "6月",
            "7月", "8月", "9月", "10月", "11月", "12月"],
    "ln": ["Sanza ya yambo", "Sanza ya mibale", "Sanza ya misato", "Sanza ya minei", "Sanza ya mitano", "Sanza ya motoba",
            "Sanza ya nsambo", "Sanza ya mwambe", "Sanza ya libwa", "Sanza ya zomi", "Sanza ya zomi na moko", "Sanza ya zomi na mibale"]
}

DAY_NAMES = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "fr": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
    "it": ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"],
    "ru": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
    "hi": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"],
    "ja": ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
    "zh": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
    "ln": ["Mokolo ya mosala", "Mokolo ya mibale", "Mokolo ya misato", "Mokolo ya minei", "Mokolo ya mitano", "Mokolo ya mposo", "Lomingo"]
}

TERMS_ABR = {
    "en": {"today": "Today", "yesterday": "Yesterday", "tomorrow": "Tomorrow"},
    "fr": {"today": "Aujourd'hui", "yesterday": "Hier", "tomorrow": "Demain"},
    "de": {"today": "Heute", "yesterday": "Gestern", "tomorrow": "Morgen"},
    "es": {"today": "Hoy", "yesterday": "Ayer", "tomorrow": "Mañana"},
    "it": {"today": "Oggi", "yesterday": "Ieri", "tomorrow": "Domani"},
    "ru": {"today": "Сегодня", "yesterday": "Вчера", "tomorrow": "Завтра"},
    "hi": {"today": "आज", "yesterday": "बीता कल", "tomorrow": "कल"},
    "ja": {"today": "今日", "yesterday": "昨日", "tomorrow": "明日"},
    "zh": {"today": "今天", "yesterday": "昨天", "tomorrow": "明天"},
    "ln": {"today": "Lelo", "yesterday": "Lobi eleki", "tomorrow": "Lobi ekoya"}
}

# Map language codes to num2words supported languages
LANGUAGE_MAPPING = {
    "fr": "fr",  # French
    "ln": "ln",  # French
    "en": "en",  # English
    "ru": "ru",  # Russian
    "es": "es",  # Spanish
    "de": "de",  # German
    "it": "it",  # Italian
    "hi": "hi",  # Hindi
    "pt": "pt",  # Portuguese
    "zh": "zh",  # Chinese
    "ja": "ja",  # Japanese
    # "ar": "ar",  # Arabic
}

# Mapping from language codes to full locale codes
LOCALE_MAPPING = {
    "en": "en_US.UTF-8",  # English (United States)
    "fr": "fr_FR.UTF-8",  # French (France)
    "ru": "ru_RU.UTF-8",  # Russian (Russia)
    "es": "es_ES.UTF-8",  # Spanish (Spain)
    "de": "de_DE.UTF-8",  # German (Germany)
    "it": "it_IT.UTF-8",  # Italian (Italy)
    "hi": "hi_IN.UTF-8",  # Hindi (India)
    "pt": "pt_PT.UTF-8",  # Portuguese (Portugal)
    "zh": "zh_CN.UTF-8",  # Chinese (China)
    "ja": "ja_JP.UTF-8",  # Japanese (Japan)
    "ar": "ar_SA.UTF-8",  # Arabic (Saudi Arabia)
    "ln": "fr_CD.UTF-8",  # Lingala (Congo) - using French Congo locale as fallback
}

# Custom date formats for each locale
DATE_FORMATS = {
    "en": {
        "date": "%m/%d/%Y",  # English date format: MM/DD/YYYY
        "datetime": "%m/%d/%Y %I:%M %p",  # English datetime format: MM/DD/YYYY HH:MM AM/PM
    },
    "fr": {
        "date": "%d/%m/%Y",  # French date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # French datetime format: DD/MM/YYYY HH:MM
    },
    "ru": {
        "date": "%d.%m.%Y",  # Russian date format: DD.MM.YYYY
        "datetime": "%d.%m.%Y %H:%M",  # Russian datetime format: DD.MM.YYYY HH:MM
    },
    "es": {
        "date": "%d/%m/%Y",  # Spanish date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # Spanish datetime format: DD/MM/YYYY HH:MM
    },
    "de": {
        "date": "%d.%m.%Y",  # German date format: DD.MM.YYYY
        "datetime": "%d.%m.%Y %H:%M",  # German datetime format: DD.MM.YYYY HH:MM
    },
    "it": {
        "date": "%d/%m/%Y",  # Italian date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # Italian datetime format: DD/MM/YYYY HH:MM
    },
    "hi": {
        "date": "%d/%m/%Y",  # Hindi date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # Hindi datetime format: DD/MM/YYYY HH:MM
    },
    "pt": {
        "date": "%d/%m/%Y",  # Portuguese date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # Portuguese datetime format: DD/MM/YYYY HH:MM
    },
    "zh": {
        "date": "%Y年%m月%d日",  # Chinese date format: YYYY年MM月DD日
        "datetime": "%Y年%m月%d日 %H:%M",  # Chinese datetime format: YYYY年MM月DD日 HH:MM
    },
    "ja": {
        "date": "%Y/%m/%d",  # Japanese date format: YYYY/MM/DD
        "datetime": "%Y/%m/%d %H:%M",  # Japanese datetime format: YYYY/MM/DD HH:MM
    },
    "ar": {
        "date": "%d/%m/%Y",  # Arabic date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # Arabic datetime format: DD/MM/YYYY HH:MM
    },
    "ln": {
        "date": "%d/%m/%Y",  # Lingala date format: DD/MM/YYYY
        "datetime": "%d/%m/%Y %H:%M",  # Lingala datetime format: DD/MM/YYYY HH:MM
    },
}

STATIC_HEADING_TITLE_KEYS = {
    "DRC_REPUBLIC": {
        "fr": "République démocratique du congo",
        "en": "Republic democratic of congo",
        "ln": "Republiki demokratiki ya Kongo",
    },
    "BUDGET_MINISTRY": {
        "fr": "Ministère de l'économie nationale",
        "en": "Ministry of National Economy",
        "ln": "Ministère ya budget",
    },
    "SUB_KIVU_PROVINCE": {
        "fr": "Province de kinshasa",
        "en": "Kinshasa province",
        "ln": "Province ya Sud-Kivu",
    },
    "EXPENSE_CHAIN_TITLE": {
        "fr": "Suivi de dépense",
        "en": "Expense tracking",
        "ln": "Chaine ya dépense",
    },
    "ELECTRONIC_COMMITMENT_FORM": {
        "fr": "Bon de saisie de la dépense",
        "en": "Expense entry form",
        "ln": "Mokanda ya engagement électronique",
    },
    "EXPENDITURE_CASE_NO": {
        "fr": "DOSSIER DE LA DEPENSE Nº",
        "en": "EXPENDITURE CASE NO.",
        "ln": "DOSSIER YA DEPENSE Nº",
    },
    "VOUCHER_NO": {
        "fr": "BDE Nº :",
        "en": "EXPENDITURE COMMITMENT NO.",
        "ln": "BDE Nº :",
    },
    "EXPENSE_COMMITMENT_DATE": {
        "fr": "Date BDE :",
        "en": "EXP. COM. DATE",
        "ln": "Mokolo ya BDE :",
    },
    "OPENING_DATE": {
        "fr": "Date d'ouverture :",
        "en": "Opening date :",
        "ln": "Mokolo ya bofungoli :",
    },
}



# Update the dictionary with frequency translations
# The structure of TRANSLATION_KEYS is different from our FREQUENCY_TYPE_TRANSLATIONS
# so we'll handle that during initialization of the TRANSLATION_KEYS dictionary

TRANSLATION_KEYS = {
    "created_at": {
        "fr": "Date de création",
        "en": "Creation Date",
        "ln": "Mokolo ya bokeli",
    },
    "updated_at": {
        "fr": "Date de mise à jour",
        "en": "Update Date",
        "ln": "Mokolo ya bobongisi",
    },
    "username": {
        "fr": "Nom d'utilisateur",
        "en": "Username",
        "ln": "Kombo ya mosaleli",
    },
    "password": {
        "fr": "Mot de passe",
        "en": "Password",
        "ln": "Mot de passe",
    },
    "account_status": {
        "fr": "État du compte",
        "en": "Account Status",
        "ln": "Lolenge ya compte",
    },
    "identifier": {
        "fr": "Identifiant",
        "en": "Identifier",
        "ln": "Elembo ya kotalisa",
    },
    "_id": {
        "fr": "ID",
        "en": "ID",
        "ln": "ID",
    },
    "id": {
        "fr": "ID",
        "en": "ID",
        "ln": "ID",
    },
    "description": {
        "fr": "Description",
        "en": "Description",
        "ln": "Maloba ya kotalisa",
    },
    "usage_description": {
        "fr": "Description d'usage",
        "en": "Usage Description",
        "ln": "Maloba ya kotalisa bosaleli",
    },
    "config_description": {
        "fr": "Description de la configuration",
        "en": "Config Description",
        "ln": "Maloba ya kotalisa configuration",
    },
    "is_default": {
        "fr": "Est par défaut",
        "en": "Is Default",
        "ln": "Ezali ya mbala nionso"
    },
    "purpose": {
        "fr": "Est par défaut",
        "en": "Is Default",
        "ln": "Ntina"
    },
    "flag": {
        "fr": "Flag",
        "en": "Flag",
        "ln": "Bendele"
    },
    "name": {
        "fr": "Nom",
        "en": "Name",
        "ln": "Kombo"
    },
    "ref_language_id": {
        "fr": "Langue(s)",
        "en": "Language(s)",
        "ln": "Lokota"
    },
    "label": {
        "fr": "Intitulé",
        "en": "Label",
        "ln": "Etiketi"
    },
    "description_html": {
        "fr": "Description Html",
        "en": "Html Description",
        "ln": "Maloba ya kotalisa HTML"
    },
    "description_str": {
        "fr": "Description",
        "en": "Description",
        "ln": "Maloba ya kotalisa"
    },
    "ref_named_entity_id": {
        "fr": "Entité nommée",
        "en": "Named entity",
        "ln": "Entité na kombo"
    },
    "ref_entity_id": {
        "fr": "Entité",
        "en": "Entity",
        "ln": "Entité"
    },
    "name_or_company_name": {
        "fr": "Nom ou raison social",
        "en": "Name or Company name",
        "ln": "Kombo to kombo ya entreprise"
    },
    "id_nat": {
        "fr": "Id. Nat",
        "en": "Id. Nat",
        "ln": "Id. Nat"
    },
    "bank_account_number": {
        "fr": "Num. compte bancaire",
        "en": "Bank account number",
        "ln": "Numéro ya compte ya banque"
    },
    "phone_number": {
        "fr": "Numéro de téléphone",
        "en": "Phone number",
        "ln": "Numéro ya telefone"
    },
    "email": {
        "fr": "Adresse mail",
        "en": "E-mail address",
        "ln": "Adresse ya email"
    },
    "address": {
        "fr": "Adresse",
        "en": "Address",
        "ln": "Adresse"
    },
    "ref_bank_id": {
        "fr": "Banque",
        "en": "Bank",
        "ln": "Banque"
    },
    "cfg_bank_id": {
        "fr": "Banque",
        "en": "Bank",
        "ln": "Banque"
    },
     
    "sys_organization_id": {
        "fr": "Organisation",
        "en": "Organization",
        "ln": "Organisation"
    },
    "cfg_function_id": {
        "fr": "Fonction",
        "en": "Position",
        "ln": "Mosala"
    },
    "cfg_grade_id": {
        "fr": "Grade",
        "en": "Grade",
        "ln": "Grade"
    },
    "cfg_organism_chart_id": {
        "fr": "Organigramme",
        "en": "Organizational chart",
        "ln": "Organigramme"
    },
    "birth_date": {
        "fr": "Date de naissance",
        "en": "Birth date",
        "ln": "Mokolo ya mbotama"
    },
    "birth_city": {
        "fr": "Ville de naissance",
        "en": "City of birth",
        "ln": "Engumba ya mbotama"
    },
    "ref_birth_country_id": {
        "fr": "Pays de naissance",
        "en": "Country of birth",
        "ln": "Mboka ya mbotama"
    },
    "ref_nationality_id": {
        "fr": "Nationalité",
        "en": "Nationality",
        "ln": "Bokoko"
    },
    "ref_marital_status_id": {
        "fr": "Status matrimonial",
        "en": "Marital status",
        "ln": "Ezalela ya libala"
    },
    "number_of_children": {
        "fr": "Nombre d'enfants",
        "en": "Number of kids",
        "ln": "Motango ya bana"
    },
    "ref_religion_id": {
        "fr": "Confession religieuse",
        "en": "Religious confession",
        "ln": "Losambo"
    },
    "address_line1": {
        "fr": "Adresse principale",
        "en": "Main address",
        "ln": "Adresse ya liboso"
    },
    "address_line2": {
        "fr": "Adresse secondaire",
        "en": "Secondary address",
        "ln": "Adresse ya mibale"
    },
    "home_town": {
        "fr": "Ville de résidence",
        "en": "Home town",
        "ln": "Engumba ya kovanda"
    },
    "ref_home_country_id": {
        "fr": "Pays de résidence",
        "en": "Home country",
        "ln": "Mboka ya kovanda"
    },
    "national_id_number": {
        "fr": "Num. carte d'id. national",
        "en": "National ID card no.",
        "ln": "Numéro ya mokanda ya identité"
    },
    "passport_number": {
        "fr": "Num. du passport",
        "en": "Passport no.",
        "ln": "Numéro ya passeport"
    },
    "driving_license_number": {
        "fr": "Num. permis de conduire",
        "en": "Driving licence no.",
        "ln": "Numéro ya permis ya kotambwisa"
    },
    "ref_eye_color_id": {
        "fr": "Couleur des yeux",
        "en": "Eye color",
        "ln": "Langi ya miso"
    },
    "ref_blood_type_id": {
        "fr": "Groupe sanguin",
        "en": "Blood type",
        "ln": "Groupe ya makila"
    },
    "height_in_cm": {
        "fr": "Hauteur en cm",
        "en": "height in cm",
        "ln": "Molayi na cm"
    },
    "weight_in_kg": {
        "fr": "poids en kg",
        "en": "Weight in kg",
        "ln": "Kilo na kg"
    },

    "first_name": {
        "fr": "Prénom",
        "en": "First name",
        "ln": "Kombo ya liboso"
    },
    "last_name": {
        "fr": "Nom",
        "en": "Last name",
        "ln": "Kombo ya suka"
    },
    "sur_name": {
        "fr": "Postnom",
        "en": "Sur name",
        "ln": "Kombo ya kati"
    },
    "gender": {
        "fr": "Genre",
        "en": "Gender",
        "ln": "Mobali to mwasi"
    },
    "cfg_photo_id": {
        "fr": "Photo de profil",
        "en": "Profile picture",
        "ln": "Foto ya profil"
    },
    "ref_color_id": {
        "fr": "Couleur",
        "en": "Color",
        "ln": "Langi"
    },
    "ref_country_id": {
        "fr": "Pays",
        "en": "Country",
        "ln": "Mboka"
    },
    "rbac_role_id": {
        "fr": "Rôle",
        "en": "Role",
        "ln": "Mosala"
    },
    "email_address": {
        "fr": "Adresse mail",
        "en": "E-mail Address",
        "ln": "Adresse ya email"
    },
    "ref_expense_chain_institution_id": {
        "fr": "Institution",
        "en": "Institution",
        "ln": "Institution"
    },
    "sys_person_id": {
        "fr": "Id.",
        "en": "Id.",
        "ln": "Id."
    },

    "html_content": {
        "fr": "Contenu en HTML",
        "en": "HTML content",
        "ln": "Makomi na HTML",
    },
    "rbac_title_id": {
        "fr": "Titre Rbac",
        "en": "Rbac Title",
        "ln": "Titre ya Rbac",
    },

    "expense_account_type":{
        "fr": "Type de compte de dépense",
        "en": "Expense account type",
        "ln": "Lolenge ya compte ya dépense",
    },
    "total_amount":{
        "fr": "Montant total",
        "en": "Total amount",
        "ln": "Motango mobimba",
    },
    "ref_bank_type_id":{
        "fr": "Type de banque",
        "en": "Bank type",
        "ln": "Lolenge ya banque",
    },
    "is_activated":{
        "fr": "Est activé",
        "en": "Is activated",
        "ln": "Ezali activé",
    },
    "ref_collection_id":{
        "fr": "Collection (Table)",
        "en": "Collection (Table)",
        "ln": "Collection (Table)",
    },
    "ref_children_display_type_id":{
        "fr": "Type d'affichage des enfants",
        "en": "Children display type",
        "ln": "Lolengo ya kobimisa bana",
    },
    "ref_currency_id":{
        "fr": "Devise",
        "en": "Currency",
        "ln": "Devise",
    },
    "ref_data_display_type_id":{
        "fr": "Type d'affichage des données",
        "en": "Data display type",
        "ln": "Lolengo ya kobimisa bana",
    },
    "template_engine_type":{
        "fr": "Type de moteur de template",
        "en": "Template engine type",
        "ln": "Lolenge ya moteur de template",
    },
    "classification_status":{
        "fr": "Classification",
        "en": "Classification",
        "ln": "Lolenge ya ko landisa",
    },
    "has_row_level_security":{
        "fr": "Sécurité au niveau des lignes (RLS)",
        "en": "Row-Level Security (RLS)",
        "ln": "Lolenge ya ko landisa (RLS)",
    },
    "case_number":{
        "fr": "Réf. de la dépense",
        "en": "Expense reference",
        "ln": "Numéro ya dépense",
    },
    "account_movement_flag":{
        "fr": "Status du processus",
        "en": "Process status",
        "ln": "Status ya processi",
    },
    "account_movement_type":{
        "fr": "Type d'opération",
        "en": "Operation type",
        "ln": "Lolenge ya processi",
    },
    "initial_solde":{
        "fr": "Solde initial",
        "en": "Initial solde",
        "ln": "Mosolo ya ebandeli",
    },
    "opening_date":{
        "fr": "Date d'ouverture",
        "en": "Opening date",
        "ln": "Mokolo ya ebandeli",
    },
    "converted_amount":{
        "fr": "Montant converti",
        "en": "Converted amount",
        "ln": "Mokoka ya ebandeli",
    },
    "exchange_rate":{
        "fr": "Taux de change",
        "en": "Exchange rate",
        "ln": "Taux ya change",
    },
    "dest_currency_id":{
        "fr": "Devise cible",
        "en": "Target currency",
        "ln": "Devise cible",
    },
    "operation_date":{
        "fr": "Date de l'opération",
        "en": "Operation date",
        "ln": "Mokolo ya processi",
    },
    "operation_motif":{
        "fr": "Motif de l'opération",
        "en": "Operation motif",
        "ln": "Mosala ya processi",
    },
    "has_rib_nomenclature_constraint":{
        "fr": "A une nomenclature spécifique ?",
        "en": "Has rib nomenclature constraint",
        "ln": "Ezali nomenclature ya rib",
    },
    "rib_account_number_format_str":{
        "fr": "Format du numéro de compte",
        "en": "Account number format",
        "ln": "Format ya nomero ya compte",
    },
    "has_prefixes_constraint":{
        "fr": "A une contrainte de préfixes ?",
        "en": "Has prefixes constraint",
        "ln": "Ezali contrainte ya préfixes",
    },
    "bank_account_number_prefixes":{
        "fr": "Préfixes du numéro de compte",
        "en": "Account number prefixes",
        "ln": "Préfixes ya nomero ya compte",
    },
    "prefix_caracters_number":{
        "fr": "Nombre de caractères des préfixes",
        "en": "Number of prefix characters",
        "ln": "Nomero ya caractères ya préfixes",
    },
    "order_by":{
        "fr": "Ordre d'affichage",
        "en": "Display order",
        "ln": "Lolengo ya kobimisa",
    },
    "ref_document_template_type_id":{
        "fr": "Type de template",
        "en": "Template type",
        "ln": "Lolenge ya template",
    },
    "template_engine_type":{
        "fr": "Type de moteur de template",
        "en": "Template engine type",
        "ln": "Lolenge ya moteur de template",
    },
    "ref_basic_expense_step_id":{
        "fr": "Etape de la dépense",
        "en": "Expense step",
        "ln": "Lolenge ya etape ya dépense",
    },
    "auth_email":{
        "fr": "Adresse mail d'authentification",
        "en": "Authentication email address",
        "ln": "Adresse ya email ya authentification",
    },
    "auth_phone_number":{
        "fr": "Numéro de téléphone d'authentification",
        "en": "Authentication phone number",
        "ln": "Numéro ya telefone ya authentification",
    },
    "ewallet_placeholder_name":{
        "fr": "Nom du wallet",
        "en": "Wallet name",
        "ln": "Kombo ya wallet",
    },
    
    "ref_telephone_network_id":{
        "fr": "Réseau téléphonique",
        "en": "Telephone network",
        "ln": "Réseau téléphonique",
    },
    "tarification_type":{
        "fr": "Type de tarification",
        "en": "Tarification type",
        "ln": "Lolenge ya tarification",
    },
    "price":{
        "fr": "Prix",
        "en": "Price",
        "ln": "Prix",
    },

}


FIELD_ERROR_TRANSLATED = {
    "en": {
        
        # General errors
        "missing": "Field is required",
        "value_error": "Invalid value",
        "type_error": "Invalid type",

        # String validation errors
        "string_too_short": "String should have at least {min_length} characters",
        "string_too_long": "String should have at most {max_length} characters",
        "string_pattern_mismatch": "String does not match the required pattern",

        # Password validation errors
        "password_complexity_uppercase": "Password must contain at least one uppercase letter",
        "password_complexity_lowercase": "Password must contain at least one lowercase letter",
        "password_complexity_digit": "Password must contain at least one digit",
        "password_complexity_special": "Password must contain at least one special character",
        "passwords_do_not_match": "Passwords do not match",

        # Email validation errors
        "value_error.email": "Invalid email address",

        # List validation errors
        "list_min_items": "List must have at least {min_items} items",
        "list_max_items": "List must have at most {max_items} items",

        # Birth date validation errors
        "invalid_date_format": "Invalid date format. Expected format: YYYY-MM-DD",
        "user_not_major": "User must be at least 18 years old",

        # Custom errors
        "user_name_already_taken": "Username '{username}' is already taken",
        "data_add_success": "Data added successfully",

        "gender_missing_enum": "Gender must be either 'm' or 'f'",
    },
    "fr": {
        # General errors
        "missing": "Champ requis",
        "value_error": "Valeur invalide",
        "type_error": "Type invalide",

        # String validation errors
        "string_too_short": "La chaîne doit contenir au moins {min_length} caractères",
        "string_too_long": "La chaîne doit contenir au plus {max_length} caractères",
        "string_pattern_mismatch": "La chaîne ne correspond pas au modèle requis",

        # Password validation errors
        "password_complexity_uppercase": "Le mot de passe doit contenir au moins une lettre majuscule",
        "password_complexity_lowercase": "Le mot de passe doit contenir au moins une lettre minuscule",
        "password_complexity_digit": "Le mot de passe doit contenir au moins un chiffre",
        "password_complexity_special": "Le mot de passe doit contenir au moins un caractère spécial",
        "passwords_do_not_match": "Les mots de passe ne correspondent pas",

        # Email validation errors
        "value_error.email": "Adresse email invalide",

        # List validation errors
        "list_min_items": "La liste doit contenir au moins {min_items} éléments",
        "list_max_items": "La liste doit contenir au plus {max_items} éléments",

        # Birth date validation errors
        "invalid_date_format": "Format de date invalide. Format attendu : AAAA-MM-JJ",
        "user_not_major": "L'utilisateur doit avoir au moins 18 ans",

        # Custom errors
        "user_name_already_taken": "Le nom d'utilisateur '{username}' est déjà pris",
        "data_add_success": "Données ajoutées avec succès",

        "gender_missing_enum": "Le sexe doit être « m » ou « f ».",
    },
    "ln": {
        # General errors
        "missing": "Esengeli kotondisa",
        "value_error": "Valeur ezali malamu te",
        "type_error": "Type ezali malamu te",

        # String validation errors
        "string_too_short": "Esengeli kozala na ba caractères {min_length} to koleka",
        "string_too_long": "Esengeli kozala na ba caractères {max_length} to moke",
        "string_pattern_mismatch": "Ekokani na modèle oyo basengaki te",

        # Password validation errors
        "password_complexity_uppercase": "Mot de passe esengeli kozala na lettre moko ya monene",
        "password_complexity_lowercase": "Mot de passe esengeli kozala na lettre moko ya moke",
        "password_complexity_digit": "Mot de passe esengeli kozala na chiffre moko",
        "password_complexity_special": "Mot de passe esengeli kozala na caractère spécial moko",
        "passwords_do_not_match": "Ba mot de passe ekokani te",

        # Email validation errors
        "value_error.email": "Adresse email ezali malamu te",

        # List validation errors
        "list_min_items": "Liste esengeli kozala na biloko {min_items} to koleka",
        "list_max_items": "Liste esengeli kozala na biloko {max_items} to moke",

        # Birth date validation errors
        "invalid_date_format": "Format ya date ezali malamu te. Format oyo basengaki: YYYY-MM-DD",
        "user_not_major": "Mosaleli asengeli kozala na mbula 18 to koleka",

        # Custom errors
        "user_name_already_taken": "Kombo ya mosaleli '{username}' ezali kosalema",
        "data_add_success": "Babakisi ba données malamu",

        "gender_missing_enum": "Genre esengeli kozala 'm' to 'f'",
    },
}


# Define translation mappings for each language
TRANSLATIONS = {
    "en": {
        ERlsAccessTypeFlag:{
            ERlsAccessTypeFlag.GLOBAL_ACCESS: "Global access",
            ERlsAccessTypeFlag.REVOKED_ACCESS: "Revoked access",
            ERlsAccessTypeFlag.CUSTOM_ACCESS: "Custom access",
        },
        ESudoActionAccessTypeFlag:{
            ESudoActionAccessTypeFlag.GLOBAL_ACCESS: "Global access",
            ESudoActionAccessTypeFlag.GROUPED_ACCESS: "Grouped access",
            ESudoActionAccessTypeFlag.DELEGATED_ACCESS: "Delegated access",
            ESudoActionAccessTypeFlag.GROUPED_CROSS_VALIDATION_ACCESS: "Grouped cross validation access",
            ESudoActionAccessTypeFlag.GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS: "Grouped inter connected organization validation access",
        },
        EConfigSudoActionTypeFlag:{
            EConfigSudoActionTypeFlag.IS_SUDO_ACTION: "Is sudo action",
            EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION: "Is sudo delegated action",
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION: "Is sudo group action",
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION: "Is sudo group cross organization validation action",
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION: "Is sudo group inter connected organization validation action",
        },
        ESudoActionAccessTargetedTypeFlag:{
            ESudoActionAccessTargetedTypeFlag.USER: "User",
            ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP: "Sudo RLS Security Group",
            ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION: "Cross organization",
            ESudoActionAccessTargetedTypeFlag.INTER_CONNECTED_ORGANIZATION: "Inter connected organization",
        }, 
        EMfaPurpose: {
            EMfaPurpose.LOGIN_ONLY: "Login only",
            EMfaPurpose.LOGIN_AND_RESET_PASSWORD: "Login and reset password",
            EMfaPurpose.RESET_PASSWORD_ONLY: "Reset password only",
            EMfaPurpose.LOCKED_SCREEN_ONLY: "Locked screen only",
            EMfaPurpose.LOGIN_AND_LOCKED_SCREEN: "Login and locked screen",
            EMfaPurpose.LOCKED_SCREEN_AND_RESET_PASSWORD: "Locked screen and reset password",
            EMfaPurpose.LOCKED_SCREEN_AND_LOGIN: "Locked screen and login",
            EMfaPurpose.ALL: "All",
        },
        MFaFlag:{
            MFaFlag.EMAIL: "Email",
            MFaFlag.PHONE_NUMBER: "Phone number",
            MFaFlag.COMMON_2FA_APP: "Common 2FA app",
            MFaFlag.SYCAMORE_2FA_APP: "SenatDigit 2FA app",
            MFaFlag.QUESTION_RESPONSE: "Question response",
            MFaFlag.PASS_CODE: "Pass code",
            MFaFlag.PIN: "Pin",
        }, 
        EGlobalStatus: {
            EGlobalStatus.ACTIVE: "Active",
            EGlobalStatus.INACTIVE: "Inactive",
            EGlobalStatus.DRAFT: "Draft",
            EGlobalStatus.PENDING: "Pending",
            EGlobalStatus.APPROVED: "Approved",
            EGlobalStatus.PAID: "Paid",
            EGlobalStatus.INSTALLMENT_PAID: "Installment Paid",
            EGlobalStatus.IN_PROGRESS: "In Progress",
            EGlobalStatus.PROCESSING: "Processing",
            EGlobalStatus.VALIDATED: "Validated",
            EGlobalStatus.REJECTED: "Rejected",
            EGlobalStatus.CANCELLED: "Cancelled",
            EGlobalStatus.LOCKED: "Locked",
            EGlobalStatus.EXPIRED: "Expired",
            EGlobalStatus.COMPLETED: "Completed",
            EGlobalStatus.FROZEN: "Frozen",
            EGlobalStatus.REVOQUED: "Revoqued",
            EGlobalStatus.BANNED: "Banned",
            EGlobalStatus.LEAVED: "Leaved",
            EGlobalStatus.LINKED: "Linked",
            EGlobalStatus.REMOVED: "Removed",
            EGlobalStatus.NONE: "None",
            EGlobalStatus.MEMBERSHIP_REQUESTED: "Membership Requested",
            EGlobalStatus.PENDING_VALIDATION: "Pending Validation",
            EGlobalStatus.PENDING_ACTIVATION: "Pending Activation",
            EGlobalStatus.PENDING_LINK_VALIDATION: "Pending Link Validation",
            EGlobalStatus.PENDING_REBATE_GROUP_LINK: "Pending Rebate Group Link",
            EGlobalStatus.PENDING_PAYMENT: "Pending Payment",
            EGlobalStatus.PENDING_VERIFICATION: "Pending Verification",
            EGlobalStatus.FAILED: "Failed",
            EGlobalStatus.DELIVERED: "Delivered",
            EGlobalStatus.HOLD_PAYMENT: "Hold Payment",
            EGlobalStatus.PAYMENT_HOLD_RELEASED: "Payment Hold Released",
            EGlobalStatus.PAYMENT_HOLD_RELEASED_REFUNDED: "Payment Hold Released Refunded",
        }, 
        ERegistrationOrigin: {
            ERegistrationOrigin.REGISTRATION: "Registration",
            ERegistrationOrigin.GOOGLE: "Google",
            ERegistrationOrigin.FACEBOOK: "Facebook",
            ERegistrationOrigin.TWITTER: "Twitter",
            ERegistrationOrigin.GITHUB: "GitHub",
        },
        EGender: {
            EGender.MALE: "Male",
            EGender.FEMALE: "Female",
            EGender.OTHER: "Other",
        },
        ECollectionCrudInfoFlag:{
            ECollectionCrudInfoFlag.NONE: "None",
            ECollectionCrudInfoFlag.CREATE_CHILD_HEAD_PROCESS_URL: "[CREATE CHILD] Head URL for child creation",
            ECollectionCrudInfoFlag.CREATE_CHILD_PROCESSING_URL: "[CREATE CHILD] Processing URL for child creation",
            ECollectionCrudInfoFlag.FETCH_URL: "[FETCH] Fetch URL",
            ECollectionCrudInfoFlag.UPDATE_PROCESSING_URL: "[UPDATE] Processing URL for update",
            ECollectionCrudInfoFlag.UPDATE_HEAD_PROCESS_URL: "[UPDATE] Head URL for update",
            ECollectionCrudInfoFlag.PARENT_FIELD_NAME: "Parent field name",
            ECollectionCrudInfoFlag.DELETE_PROCESSING_URL: "[DELETE] Processing URL for deletion",
            ECollectionCrudInfoFlag.CREATE_PROCESSING_URL: " [CREATE] Processing URL for creation",
            ECollectionCrudInfoFlag.CREATE_HEAD_PROCESS_URL: "[CREATE] Head URL for creation",
            ECollectionCrudInfoFlag.DOWNLOAD_PROCESS_URL: "Download Process URL",
            ECollectionCrudInfoFlag.FETCH_ONE_INFO_URL: "[FETCH ONE] Fetch one info URL",
            ECollectionCrudInfoFlag.FETCH_ONE_INFO_FOR_VIEWING_URL: "[FETCH ONE] Fetch one info for viewing URL",
            ECollectionCrudInfoFlag.PUT_PROCESSING_URL: "[PUT] Put Processing URL",
            ECollectionCrudInfoFlag.PATCH_PROCESSING_URL: "[PATCH] Patch Processing URL",
        },
        ECoolBoxStatus: {
            ECoolBoxStatus.ACTIVE: "Active",
            ECoolBoxStatus.INACTIVE: "Inactive",
            ECoolBoxStatus.IN_SERVICE: "In Service",
            ECoolBoxStatus.OUT_OF_SERVICE: "Out of Service",
        },
        ESrcAttachment: {
            ESrcAttachment.GENERATED: "Generated",
            ESrcAttachment.UPLOADED: "Uploaded",
        },
        EParentChildHead: {
            EParentChildHead.PARENT_HEAD: "Parent Head",
            EParentChildHead.CHILD_HEAD: "Child Head",
            EParentChildHead.NO_SPECIFICATION: "No Specification",
        },
        EOperationStatus: {
            EOperationStatus.PENDING: "Pending",
            EOperationStatus.REVISION: "Revision",
            EOperationStatus.REJECTED: "Rejected",
        },
        ETransactionStatus: {
            ETransactionStatus.PENDING: "Pending",
            ETransactionStatus.VALIDATED: "Validated",
            ETransactionStatus.REJECTED: "Rejected",
        },
        AppGeneratorType: {
            AppGeneratorType.HASH_FROM_NAME: "Hash from Name",
            AppGeneratorType.UUID: "UUID",
            AppGeneratorType.CUSTOM: "Custom",
        },
        OutputDataType: {
            OutputDataType.DATA_TABLE: "Data Table",
            OutputDataType.INPUT_SELECT: "Input Select",
            OutputDataType.CASCADE: "Cascade",
            OutputDataType.CASCADE_ALL: "Cascade All",
            OutputDataType.TREE: "Tree",
            OutputDataType.DEFAULT: "Default",
        },
        AccountStatusFlag: {
            AccountStatusFlag.ACTIVE: "Active",
            AccountStatusFlag.INACTIVE: "Inactive",
            AccountStatusFlag.LOCKED: "Locked",
            AccountStatusFlag.SUSPENDED: "Suspended",
            AccountStatusFlag.REVOQUED: "Revoqued",
            AccountStatusFlag.LOCKED_BY_SYSTEM: "Locked by System",
        },
        ELoginResetPasswordFailStatus: {
            ELoginResetPasswordFailStatus.NORMAL: "Normal",
            ELoginResetPasswordFailStatus.LOCKED: "Locked",
            ELoginResetPasswordFailStatus.SUSPENDED: "Suspended",
            ELoginResetPasswordFailStatus.LOCKED_BY_SYSTEM: "Locked by System",
        },
        EJWTTokenType: {
            EJWTTokenType.MFA_VERIFICATION: "MFA Verification",
            EJWTTokenType.LOGIN: "Login",
            EJWTTokenType.REFRESH_TOKEN: "Refresh Token",
            EJWTTokenType.PASSWORD_INIT_PROCESS: "Password Init Process",
            EJWTTokenType.PASSWORD_RESET_PROCESS: "Password Reset Process",
            EJWTTokenType.PASSWORD_RESET_REDIRECTED: "Password Reset Redirected",
        },
        EUserDeviceStatus: {
            EUserDeviceStatus.PENDING_VALIDATION: "Pending Validation",
            EUserDeviceStatus.ALLOWED: "Allowed",
            EUserDeviceStatus.REVOQUED: "Revoqued",
            EUserDeviceStatus.LOCKED: "Locked",
        },
        EOperationStatusFlag: {
            EOperationStatusFlag.DRAFT: "Draft",
            EOperationStatusFlag.PENDING_VALIDATION: "Pending Validation",
            EOperationStatusFlag.IN_PROGRESS: "In Progress",
            EOperationStatusFlag.COMPLETED: "Completed",
        },
        ESubmissionOperationStatusFlag: {
            ESubmissionOperationStatusFlag.DRAFT: "Draft",
            ESubmissionOperationStatusFlag.SUBMITED: "Submited",
        },
         ExpenseChainTransactionStatusFlag: {
            ExpenseChainTransactionStatusFlag.PENDING_VALIDATION: "Pending",
            ExpenseChainTransactionStatusFlag.VALIDATED: "Validated",
            ExpenseChainTransactionStatusFlag.REJECTED: "Rejected",
        },
        EExChainInstDesignation: {
            EExChainInstDesignation.INSTITUTION: "Institution",
            EExChainInstDesignation.SECTION: "Section",
            EExChainInstDesignation.CHAPTER: "Chapter",
        },
        EExpenseChainBeneficiaryType: {
            EExpenseChainBeneficiaryType.INNER_BENEFICIARY: "Inner beneficiary",
            EExpenseChainBeneficiaryType.OUTER_BENEFICIARY: "Outer beneficiary",
        },
        EMultipleValidationType: {
            EMultipleValidationType.CREATE: "Creation",
            EMultipleValidationType.HARD_DELETE: "Deletion",
            EMultipleValidationType.DOWNLOAD: "Download",
            EMultipleValidationType.SHARE: "Share",
            EMultipleValidationType.UPDATE: "update",
        },
        EMultipleValidationStatus: {
            EMultipleValidationStatus.PENDING: "Pending",
            EMultipleValidationStatus.APPROVED: "Approved",
            EMultipleValidationStatus.IN_PROGRESS: "In progress",
            EMultipleValidationStatus.REJECTED: "Rejected",
        },
        ERbacActionFlag: {
            ERbacActionFlag.TABLE_ACTION_ADD: "Add",
            ERbacActionFlag.TABLE_ACTION_ADD_CHILD: "Add Child",
            ERbacActionFlag.TABLE_ACTION_UPDATE: "Update",
            ERbacActionFlag.TABLE_ACTION_DELETE: "Delete",
            ERbacActionFlag.TABLE_ACTION_VIEW: "View",
            ERbacActionFlag.STANDALONE_ACTION: "Standalone Action",
            ERbacActionFlag.COMMON_LOCK_ACTION: "Lock",
            ERbacActionFlag.COMMON_UNLOCK_ACTION: "Unlock",
            ERbacActionFlag.COMMON_DOWNLOAD_ACTION: "Download",
            ERbacActionFlag.COMMON_UPLOAD_ACTION_FILE: "Upload File",
        },
        ERbacComponentFlag: {
            ERbacComponentFlag.DATA_LIST_COMPONENT: "Data list", 
            ERbacComponentFlag.OWN_INFO_COMPONENT: "Own info", 
            ERbacComponentFlag.STANDARD_COMPONENT: "Standard component", 
        },
        EExpenseAccountType:{
            EExpenseAccountType.INTERNAL:"Internal",
            EExpenseAccountType.EXTERNAL:"External",
            EExpenseAccountType.TRANSIT:"Transit",
        },
        EExpenseVerificatorType:{
            EExpenseVerificatorType.GLOBAL:"Global",
            EExpenseVerificatorType.ASSOCIATED_TO_ACCOUNT:"Associated to account",
        },
        EAccountMovementType:{
            EAccountMovementType.DEBIT: "Debit",
            EAccountMovementType.CREDIT: "Credit",
            EAccountMovementType.TRANSFER_IN: "Transfer Received",
            EAccountMovementType.TRANSFER_OUT: "Transfer Issued",
            EAccountMovementType.NONE: "None",
        },
        EAccountMovementStatus:{
            EAccountMovementStatus.PENDING: "Pending",
            EAccountMovementStatus.VALIDATED: "Validated",
            EAccountMovementStatus.REJECTED: "Rejected",
            EAccountMovementStatus.CANCELLED: "Cancelled",
            EAccountMovementStatus.NONE: "None",
        }, 
        EExpenseClacificationStatusFlag:{
            EExpenseClacificationStatusFlag.NORMAL: "Normal",
            EExpenseClacificationStatusFlag.URGENT: "Urgent",
            EExpenseClacificationStatusFlag.MORE_URGENT: "More Urgent",
            # EExpenseClacificationStatusFlag.LESS_URGENT: "Less Urgent",
        },
        EAccountMovementFlag:{
            EAccountMovementFlag.PENDING: "Pending",
            EAccountMovementFlag.VALIDATED: "Validated",
            EAccountMovementFlag.REJECTED: "Rejected",
        },
        ESubmissionOperationStatusFlag:{
            ESubmissionOperationStatusFlag.DRAFT: "Draft",
            ESubmissionOperationStatusFlag.SUBMITED: "Submited",
        },
        ExpenseTransactionStatusFlag:{
            ExpenseTransactionStatusFlag.PENDING_VALIDATION: "Pending Validation",
            ExpenseTransactionStatusFlag.PENDING_BANK_VALIDATION: "Pending Bank Validation",
            ExpenseTransactionStatusFlag.VALIDATED: "Validated",
            ExpenseTransactionStatusFlag.REJECTED: "Rejected",
        },
        EExpensePaymentBeneficiaryReceiverType:{
            EExpensePaymentBeneficiaryReceiverType.SAME_BENEFICIARY: "Same beneficiary",
            EExpensePaymentBeneficiaryReceiverType.DELEGATED_PERSON: "Delegated person",
            EExpensePaymentBeneficiaryReceiverType.NONE :'None'
        },
        EExpenseOpsBeneficiaryType:{
            EExpenseOpsBeneficiaryType.AGENT_BENEFICIARY: "Agent beneficiary",
            EExpenseOpsBeneficiaryType.PHYSICAL_BENEFICIARY: "Physical beneficiary",
            EExpenseOpsBeneficiaryType.LEGAL_BENEFICIARY: "Legal beneficiary",
            EExpenseOpsBeneficiaryType.NONE :'None'
        },
        EExpenseOpsPaymentActorType:{
            EExpenseOpsPaymentActorType.FINANCER: "Financer",
            EExpenseOpsPaymentActorType.ACCOUNTANT: "Accountant",
            EExpenseOpsPaymentActorType.BANK: "Bank",
            EExpenseOpsPaymentActorType.NONE :'None'
        },
        EExpensePaymentType:{
            EExpensePaymentType.INSTALLMENT_PAYMENT: "Installment Payment",
            EExpensePaymentType.ONE_TIME_PAYMENT: "One Time Payment",
            EExpensePaymentType.NONE :'None'
        },
        EMenuChildrenDisplayFlag:{
            EMenuChildrenDisplayFlag.NONE: "None",
            EMenuChildrenDisplayFlag.LEFT_SIDE_MENU: "Left Side Menu",
            EMenuChildrenDisplayFlag.RIGHT_SIDE_MENU: "Right Side Menu",
            EMenuChildrenDisplayFlag.TOP_BAR_MENU: "Top Bar Menu",
            EMenuChildrenDisplayFlag.CENTERED_CARD_MENU: "Centered Card Menu",
            EMenuChildrenDisplayFlag.GRID_CHILDREN_CONTENT: "Grid Children Content",
        },
        EDataDisplayTypeFlag:{
            EDataDisplayTypeFlag.NONE: "None",
            EDataDisplayTypeFlag.REGULAR_TABLE: "Regular Table",
            EDataDisplayTypeFlag.LIST_TILE: "List Tile",
            EDataDisplayTypeFlag.CARD: "Card",
            EDataDisplayTypeFlag.TREE_TABLE: "Tree Table",
            EDataDisplayTypeFlag.ORG_CHART: "Org Chart",
        },
        ETemplateEngineType:{
            ETemplateEngineType.HTML: "HTML",
            ETemplateEngineType.JINJA: "Jinja",
            ETemplateEngineType.CANVAS: "Canvas",
            ETemplateEngineType.MARKDOWN: "Markdown",
        },
        
        ELoginStatus:{
            ELoginStatus.NONE: "None",
            ELoginStatus.LOGGED_IN: "Logged In",
            ELoginStatus.LOGGED_OUT: "Logged Out",
            ELoginStatus.INIT_LOGIN: "Init Login",
            ELoginStatus.INIT_PASSWORD_PROCESS: "Init Password Process",
            ELoginStatus.RESET_PASSWORD_PROCESS_VALIDATED: "Reset Password Process Validated",
            ELoginStatus.RESET_PASSWORD_PROCESS_COMPLETED: "Reset Password Process Completed",
        },
        EAppGroupFlag:{
            EAppGroupFlag.COMMON: "Common",
        },
         
        ERestoreStatus:{
            ERestoreStatus.NOT_RESTORED: "Not Restored",
            ERestoreStatus.RESTORED: "Restored",
            ERestoreStatus.PARTIALLY_RESTORED: "Partially Restored",
        }
    },
    "fr": {
        ERlsAccessTypeFlag:{
            ERlsAccessTypeFlag.GLOBAL_ACCESS: "Accès global",
            ERlsAccessTypeFlag.REVOKED_ACCESS: "Accès révoqué",
            ERlsAccessTypeFlag.CUSTOM_ACCESS: "Accès personnalisé",
        },
        ESudoActionAccessTypeFlag:{
            ESudoActionAccessTypeFlag.GLOBAL_ACCESS: "Accès global",
            ESudoActionAccessTypeFlag.GROUPED_ACCESS: "Accès groupé",
            ESudoActionAccessTypeFlag.DELEGATED_ACCESS: "Accès délégué",
            ESudoActionAccessTypeFlag.GROUPED_CROSS_VALIDATION_ACCESS: "Accès groupé de validation croisée",
            ESudoActionAccessTypeFlag.GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS: "Accès groupé de validation inter organisation connectée",
        },
        EConfigSudoActionTypeFlag:{
            EConfigSudoActionTypeFlag.IS_SUDO_ACTION: "Est une action sudo",
            EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION: "Est une action sudo déléguée",
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION: "Est une action sudo de groupe",
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION: "Est une action sudo de groupe de validation croisée d'organisation",
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION: "Est une action sudo de groupe de validation inter organisation connectée",
        },
        ESudoActionAccessTargetedTypeFlag:{
            ESudoActionAccessTargetedTypeFlag.USER: "Utilisateur",
            ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP: "Groupe de sécurité sudo/rls",
            ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION: "Organisation croisée",
            ESudoActionAccessTargetedTypeFlag.INTER_CONNECTED_ORGANIZATION: "Organisation connectée",
        }, 
        ERbacActionFlag: {
            ERbacActionFlag.TABLE_ACTION_ADD: "Ajouter",
            ERbacActionFlag.TABLE_ACTION_ADD_CHILD: "Ajouter un enfant",
            ERbacActionFlag.TABLE_ACTION_UPDATE: "Mettre à jour",
            ERbacActionFlag.TABLE_ACTION_DELETE: "Supprimer",
            ERbacActionFlag.TABLE_ACTION_VIEW: "Voir",
            ERbacActionFlag.STANDALONE_ACTION: "Action autonome",
            ERbacActionFlag.COMMON_LOCK_ACTION: "Verrouiller",
            ERbacActionFlag.COMMON_UNLOCK_ACTION: "Déverrouiller",
            ERbacActionFlag.COMMON_DOWNLOAD_ACTION: "Télécharger",
            ERbacActionFlag.COMMON_UPLOAD_ACTION_FILE: "Téléverser un fichier",
        }, 
        EMfaPurpose: {
            EMfaPurpose.LOGIN_ONLY: "Connexion seule",
            EMfaPurpose.LOGIN_AND_RESET_PASSWORD: "Connexion et réinitialisation du mot de passe",
            EMfaPurpose.RESET_PASSWORD_ONLY: "Réinitialisation du mot de passe seule",
            EMfaPurpose.LOCKED_SCREEN_ONLY: "Ecran verrouillé seul",
            EMfaPurpose.LOGIN_AND_LOCKED_SCREEN: "Connexion et écran verrouillé",
            EMfaPurpose.LOCKED_SCREEN_AND_RESET_PASSWORD: "Ecran verrouillé et réinitialisation du mot de passe",
            EMfaPurpose.LOCKED_SCREEN_AND_LOGIN: "Ecran verrouillé et connexion",
            EMfaPurpose.ALL: "Tous",
        },
        MFaFlag:{
            MFaFlag.EMAIL: "Email",
            MFaFlag.PHONE_NUMBER: "Numéro de téléphone",
            MFaFlag.COMMON_2FA_APP: "Application 2FA commune",
            MFaFlag.SYCAMORE_2FA_APP: "Application 2FA SenatDigit",
            MFaFlag.QUESTION_RESPONSE: "Question réponse",
            MFaFlag.PASS_CODE: "Code à usage unique",
            MFaFlag.PIN: "Code PIN",
        }, 
        EGlobalStatus: {
            EGlobalStatus.ACTIVE: "Actif",
            EGlobalStatus.INACTIVE: "Inactif",
            EGlobalStatus.DRAFT: "Brouillon",
            EGlobalStatus.PENDING: "En Attente",
            EGlobalStatus.APPROVED: "Approuvé",
            EGlobalStatus.PAID: "Payé",
            EGlobalStatus.INSTALLMENT_PAID: "Payé en échéances",
            EGlobalStatus.IN_PROGRESS: "En Cours",
            EGlobalStatus.PROCESSING: "En Cours",
            EGlobalStatus.VALIDATED: "Validé",
            EGlobalStatus.REJECTED: "Rejeté",
            EGlobalStatus.CANCELLED: "Annulé",
            EGlobalStatus.LOCKED: "Verrouillé", 
            EGlobalStatus.EXPIRED: "Expiré",
            EGlobalStatus.COMPLETED: "Terminé",
            EGlobalStatus.FROZEN: "Gelé",
            EGlobalStatus.REVOQUED: "Révoqué",
            EGlobalStatus.BANNED: "Banni",
            EGlobalStatus.LEAVED: "Démissionné",
            EGlobalStatus.LINKED: "Lié",
            EGlobalStatus.REMOVED: "Supprimé",
            EGlobalStatus.NONE: "Aucun",
            EGlobalStatus.MEMBERSHIP_REQUESTED: "Demande de Cotisation",
            EGlobalStatus.PENDING_VALIDATION: "En Attente de Validation",
            EGlobalStatus.PENDING_ACTIVATION: "En Attente d'Activation",
            EGlobalStatus.PENDING_LINK_VALIDATION: "En Attente de Validation de Liaison",
            EGlobalStatus.PENDING_REBATE_GROUP_LINK: "En Attente de Liaison de Groupe de Remboursement",
            EGlobalStatus.PENDING_PAYMENT: "En Attente de Paiement",
            EGlobalStatus.PENDING_VERIFICATION: "En Attente de Vérification",
            EGlobalStatus.FAILED: "Échoué",
            EGlobalStatus.DELIVERED: "Livré",
            EGlobalStatus.HOLD_PAYMENT: "Paiement en Attente",
            EGlobalStatus.PAYMENT_HOLD_RELEASED: "Paiement en Attente Libéré",
            EGlobalStatus.PAYMENT_HOLD_RELEASED_REFUNDED: "Paiement en Attente Libéré et Remboursé",
        }, 
        ERegistrationOrigin: {
            ERegistrationOrigin.REGISTRATION: "Inscription",
            ERegistrationOrigin.GOOGLE: "Google",
            ERegistrationOrigin.FACEBOOK: "Facebook",
            ERegistrationOrigin.TWITTER: "Twitter",
            ERegistrationOrigin.GITHUB: "GitHub",
        },
        EGender: {
            EGender.MALE: "Homme",
            EGender.FEMALE: "Femme",
            EGender.OTHER: "Autre",
        },
        ECoolBoxStatus: {
            ECoolBoxStatus.ACTIVE: "Actif",
            ECoolBoxStatus.INACTIVE: "Inactif",
            ECoolBoxStatus.IN_SERVICE: "En Service",
            ECoolBoxStatus.OUT_OF_SERVICE: "Hors Service",
        },
        ESrcAttachment: {
            ESrcAttachment.GENERATED: "Généré",
            ESrcAttachment.UPLOADED: "Téléchargé",
        },
        EParentChildHead: {
            EParentChildHead.PARENT_HEAD: "Tête Parent",
            EParentChildHead.CHILD_HEAD: "Tête Enfant",
            EParentChildHead.NO_SPECIFICATION: "Pas de Spécification",
        },
        EOperationStatus: {
            EOperationStatus.PENDING: "En Attente",
            EOperationStatus.REVISION: "Révision",
            EOperationStatus.REJECTED: "Rejeté",
        },
        ETransactionStatus: {
            ETransactionStatus.PENDING: "En Attente",
            ETransactionStatus.VALIDATED: "Validé",
            ETransactionStatus.REJECTED: "Rejeté",
        },
        AppGeneratorType: {
            AppGeneratorType.HASH_FROM_NAME: "Hash à partir du Nom",
            AppGeneratorType.UUID: "UUID",
            AppGeneratorType.CUSTOM: "Personnalisé",
        },
        OutputDataType: {
            OutputDataType.DATA_TABLE: "Table de Données",
            OutputDataType.INPUT_SELECT: "Sélection d'Entrée",
            OutputDataType.CASCADE: "Cascade",
            OutputDataType.CASCADE_ALL: "Cascade Totale",
            OutputDataType.TREE: "Arbre",
            OutputDataType.DEFAULT: "Par Défaut",
        },
        AccountStatusFlag: {
            AccountStatusFlag.ACTIVE: "Actif",
            AccountStatusFlag.INACTIVE: "Inactif",
            AccountStatusFlag.LOCKED: "Verrouillé",
            AccountStatusFlag.SUSPENDED: "Suspendu",
            AccountStatusFlag.REVOQUED: "Révoqué",
            AccountStatusFlag.LOCKED_BY_SYSTEM: "Verrouillé par le Système",
        },
        ELoginResetPasswordFailStatus: {
            ELoginResetPasswordFailStatus.NORMAL: "Normal",
            ELoginResetPasswordFailStatus.LOCKED: "Verrouillé",
            ELoginResetPasswordFailStatus.SUSPENDED: "Suspendu",
            ELoginResetPasswordFailStatus.LOCKED_BY_SYSTEM: "Verrouillé par le Système",
        },
        EJWTTokenType: {
            EJWTTokenType.MFA_VERIFICATION: "Vérification MFA",
            EJWTTokenType.LOGIN: "Connexion",
            EJWTTokenType.REFRESH_TOKEN: "Rafraichir le token",
            EJWTTokenType.PASSWORD_INIT_PROCESS: "Processus d'Initialisation du Mot de Passe",
            EJWTTokenType.PASSWORD_RESET_PROCESS: "Processus de Réinitialisation du Mot de Passe",
            EJWTTokenType.PASSWORD_RESET_REDIRECTED: "Réinitialisation du Mot de Passe Redirigée",
        },
        EUserDeviceStatus: {
            EUserDeviceStatus.PENDING_VALIDATION: "Validation en Attente",
            EUserDeviceStatus.ALLOWED: "Autorisé",
            EUserDeviceStatus.REVOQUED: "Révoqué",
            EUserDeviceStatus.LOCKED: "Verrouillé",
        },
        EOperationStatusFlag: {
            EOperationStatusFlag.DRAFT: "Brouillon",
            EOperationStatusFlag.PENDING_VALIDATION: "Validation en Attente",
            EOperationStatusFlag.IN_PROGRESS: "En Cours",
            EOperationStatusFlag.COMPLETED: "Terminé",
        },
        ESubmissionOperationStatusFlag: {
            ESubmissionOperationStatusFlag.DRAFT: "Brouillon",
            ESubmissionOperationStatusFlag.SUBMITED: "Soumis",
        },
        ExpenseChainTransactionStatusFlag: {
            ExpenseChainTransactionStatusFlag.PENDING_VALIDATION: "En attente",
            ExpenseChainTransactionStatusFlag.VALIDATED: "Validé",
            ExpenseChainTransactionStatusFlag.REJECTED: "Rejecté",
        },
        EExChainInstDesignation: {
            EExChainInstDesignation.INSTITUTION: "Institution",
            EExChainInstDesignation.SECTION: "Section",
            EExChainInstDesignation.CHAPTER: "Chapitre",
        },
        EExpenseChainBeneficiaryType: {
            EExpenseChainBeneficiaryType.INNER_BENEFICIARY: "Bénéficiaire interne",
            EExpenseChainBeneficiaryType.OUTER_BENEFICIARY: "Bénéficiaire extérieur",
        },
        EMultipleValidationType: {
            EMultipleValidationType.CREATE: "Création",
            EMultipleValidationType.HARD_DELETE: "Suppression",
            EMultipleValidationType.DOWNLOAD: "Téléchargement",
            EMultipleValidationType.SHARE: "Partage",
            EMultipleValidationType.UPDATE: "Mise à jour",
        },
        EMultipleValidationStatus: {
            EMultipleValidationStatus.PENDING: "En attente",
            EMultipleValidationStatus.APPROVED: "Approuvé",
            EMultipleValidationStatus.IN_PROGRESS: "En cours",
            EMultipleValidationStatus.REJECTED: "Rejeté",
        },
        ERbacActionFlag: {
            ERbacActionFlag.TABLE_ACTION_ADD: "Ajouter",
            ERbacActionFlag.TABLE_ACTION_ADD_CHILD: "Ajouter un enfant",
            ERbacActionFlag.TABLE_ACTION_UPDATE: "Mettre à jour",
            ERbacActionFlag.TABLE_ACTION_DELETE: "Supprimer",
            ERbacActionFlag.TABLE_ACTION_VIEW: "Voir",
            ERbacActionFlag.STANDALONE_ACTION: "Action autonome",
            ERbacActionFlag.COMMON_LOCK_ACTION: "Verrouiller",
            ERbacActionFlag.COMMON_UNLOCK_ACTION: "Déverrouiller",
            ERbacActionFlag.COMMON_DOWNLOAD_ACTION: "Télécharger",
            ERbacActionFlag.COMMON_UPLOAD_ACTION_FILE: "Téléverser un fichier",
        },
        ERbacComponentFlag: {
            ERbacComponentFlag.DATA_LIST_COMPONENT: "Liste de données", 
            ERbacComponentFlag.OWN_INFO_COMPONENT: "Info. personnelle", 
            ERbacComponentFlag.STANDARD_COMPONENT: "Composant standard", 
        },
        EExpenseAccountType:{
            EExpenseAccountType.INTERNAL:"Interne",
            EExpenseAccountType.EXTERNAL:"Externe",
            EExpenseAccountType.TRANSIT:"Transitaire",
        },
        EExpenseVerificatorType:{
            EExpenseVerificatorType.GLOBAL:"Global",
            EExpenseVerificatorType.ASSOCIATED_TO_ACCOUNT:"Associé à un compte",
        },
        EAccountMovementType:{
            EAccountMovementType.DEBIT: "Débit",
            EAccountMovementType.CREDIT: "Crédit",
            EAccountMovementType.TRANSFER_IN: "Virement Reçu",
            EAccountMovementType.TRANSFER_OUT: "Virement Émis",
            EAccountMovementType.NONE: "Aucun",
        },
        EAccountMovementStatus:{
            EAccountMovementStatus.PENDING: "En Attente",
            EAccountMovementStatus.VALIDATED: "Validé",
            EAccountMovementStatus.REJECTED: "Rejeté",
            EAccountMovementStatus.CANCELLED: "Annulé",
            EAccountMovementStatus.NONE: "Aucun",
        }, 
        EExpenseClacificationStatusFlag:{
            EExpenseClacificationStatusFlag.NORMAL: "Normal",
            EExpenseClacificationStatusFlag.URGENT: "Urgent",
            EExpenseClacificationStatusFlag.MORE_URGENT: "Très urgent",
            # EExpenseClacificationStatusFlag.LESS_URGENT: "Moins urgent",
        },
        EAccountMovementFlag:{
            EAccountMovementFlag.PENDING: "En attente",
            EAccountMovementFlag.VALIDATED: "Validé",
            EAccountMovementFlag.REJECTED: "Rejeté",
        },
        ESubmissionOperationStatusFlag:{
            ESubmissionOperationStatusFlag.DRAFT: "Brouillon",
            ESubmissionOperationStatusFlag.SUBMITED: "Soumis",
        },
        ExpenseTransactionStatusFlag:{
            ExpenseTransactionStatusFlag.PENDING_VALIDATION: "En attente de validation",
            ExpenseTransactionStatusFlag.PENDING_BANK_VALIDATION: "En attente de validation par la banque",
            ExpenseTransactionStatusFlag.VALIDATED: "Validé",
            ExpenseTransactionStatusFlag.REJECTED: "Rejeté",
        },
        EExpensePaymentBeneficiaryReceiverType:{
            EExpensePaymentBeneficiaryReceiverType.SAME_BENEFICIARY: "Même bénéficiaire",
            EExpensePaymentBeneficiaryReceiverType.DELEGATED_PERSON: "Personne délégée",
            EExpensePaymentBeneficiaryReceiverType.NONE :'Aucun'
        },
        ExpenseChainTransactionStatusFlag:{
            ExpenseChainTransactionStatusFlag.PENDING_VALIDATION: "En attente de validation",
            ExpenseChainTransactionStatusFlag.VALIDATED: "Validé",
            ExpenseChainTransactionStatusFlag.REJECTED: "Rejeté",
        },
        EExpenseOpsBeneficiaryType:{
            EExpenseOpsBeneficiaryType.AGENT_BENEFICIARY: "Agent Bénéficiaire",
            EExpenseOpsBeneficiaryType.PHYSICAL_BENEFICIARY: "Bénéficiaire physique",
            EExpenseOpsBeneficiaryType.LEGAL_BENEFICIARY: "Bénéficiaire légal",
            EExpenseOpsBeneficiaryType.NONE : 'Aucun'
        },
        EExpenseOpsPaymentActorType:{
            EExpenseOpsPaymentActorType.FINANCER: "Financier",
            EExpenseOpsPaymentActorType.ACCOUNTANT: "Comptable",
            EExpenseOpsPaymentActorType.BANK: "Banque",
            EExpenseOpsPaymentActorType.NONE : 'Aucun'
        },
        EExpensePaymentType:{
            EExpensePaymentType.INSTALLMENT_PAYMENT: "Paiement à terme",
            EExpensePaymentType.ONE_TIME_PAYMENT: "Paiement unique",
            EExpensePaymentType.NONE : 'Aucun'
        },
        ECollectionCrudInfoFlag:{
            ECollectionCrudInfoFlag.NONE: "Aucun",
            ECollectionCrudInfoFlag.CREATE_CHILD_HEAD_PROCESS_URL:"[CREATE CHILD] L'url head pour la création d'un enfant",
            ECollectionCrudInfoFlag.CREATE_CHILD_PROCESSING_URL: "[CREATE CHILD] L'url de traitement pour la création d'un enfant",
            ECollectionCrudInfoFlag.FETCH_URL: "[FETCH] L'url de récupération",
            ECollectionCrudInfoFlag.UPDATE_PROCESSING_URL: "[UPDATE] L'url de traitement pour la mise à jour",
            ECollectionCrudInfoFlag.UPDATE_HEAD_PROCESS_URL: "[UPDATE] L'url head pour la mise à jour",
            ECollectionCrudInfoFlag.PARENT_FIELD_NAME: "Nom du champ parent",
            ECollectionCrudInfoFlag.DELETE_PROCESSING_URL: "[DELETE] L'url de traitement pour la suppression",
            ECollectionCrudInfoFlag.CREATE_PROCESSING_URL: "[CREATE] L'url de traitement pour la création",
            ECollectionCrudInfoFlag.CREATE_HEAD_PROCESS_URL: "[CREATE] L'url head pour la création",
            ECollectionCrudInfoFlag.DOWNLOAD_PROCESS_URL: "[DOWNLOAD] L'url de téléchargement",
            ECollectionCrudInfoFlag.FETCH_ONE_INFO_URL: "[FETCH ONE] L'url de récupération d'un élément",
            ECollectionCrudInfoFlag.FETCH_ONE_INFO_FOR_VIEWING_URL: "[FETCH ONE] L'url de récupération d'un élément pour la vue",
            ECollectionCrudInfoFlag.PUT_PROCESSING_URL: "[PUT] L'url de traitement pour la mise à jour",
            ECollectionCrudInfoFlag.PATCH_PROCESSING_URL: "[PATCH] L'url de traitement pour la mise à jour",
        },
        EMenuChildrenDisplayFlag:{
            EMenuChildrenDisplayFlag.NONE: "Aucun",
            EMenuChildrenDisplayFlag.LEFT_SIDE_MENU: "Menu gauche",
            EMenuChildrenDisplayFlag.RIGHT_SIDE_MENU: "Menu droit",
            EMenuChildrenDisplayFlag.TOP_BAR_MENU: "Menu barre supérieure",
            EMenuChildrenDisplayFlag.CENTERED_CARD_MENU: "Menu carte centrale",
            EMenuChildrenDisplayFlag.GRID_CHILDREN_CONTENT: "Contenu en grille des enfants",
        },
        EDataDisplayTypeFlag:{
            EDataDisplayTypeFlag.NONE: "Aucun",
            EDataDisplayTypeFlag.REGULAR_TABLE: "Tableau régulier",
            EDataDisplayTypeFlag.LIST_TILE: "Liste en tuile",
            EDataDisplayTypeFlag.CARD: "Carte",
            EDataDisplayTypeFlag.TREE_TABLE: "Tableau arborescent",
            EDataDisplayTypeFlag.ORG_CHART: "Organigramme",
        },
        ETemplateEngineType:{
            ETemplateEngineType.HTML: "HTML",
            ETemplateEngineType.JINJA: "Jinja",
            ETemplateEngineType.CANVAS: "Canvas",
            ETemplateEngineType.MARKDOWN: "Markdown",
        },
        ELoginStatus:{
            ELoginStatus.NONE: "Aucun",
            ELoginStatus.LOGGED_IN: "Connecté",
            ELoginStatus.LOGGED_OUT: "Déconnecté",
            ELoginStatus.INIT_LOGIN: "Initialisation de la connexion",
            ELoginStatus.INIT_PASSWORD_PROCESS: "Initialisation du processus de mot de passe",
            ELoginStatus.RESET_PASSWORD_PROCESS_VALIDATED: "Processus de réinitialisation du mot de passe validé",
            ELoginStatus.RESET_PASSWORD_PROCESS_COMPLETED: "Processus de réinitialisation du mot de passe terminé",
        },
        EAppGroupFlag:{
            EAppGroupFlag.COMMON: "Common",
        }, 
        ERestoreStatus:{
            ERestoreStatus.NOT_RESTORED: "Non restauré",
            ERestoreStatus.RESTORED: "Restauré",
            ERestoreStatus.PARTIALLY_RESTORED: "Partiellement restauré",
        }
    },
    "ln": { 
        ERegistrationOrigin: {
            ERegistrationOrigin.REGISTRATION: "Bokomi",
            ERegistrationOrigin.GOOGLE: "Google",
            ERegistrationOrigin.FACEBOOK: "Facebook",
            ERegistrationOrigin.TWITTER: "Twitter",
            ERegistrationOrigin.GITHUB: "GitHub",
        },
        EGender: {
            EGender.MALE: "Mobali",
            EGender.FEMALE: "Mwasi",
            EGender.OTHER: "Mosusu",
        },
        ECollectionCrudInfoFlag:{
            ECollectionCrudInfoFlag.NONE: "Moko te",
            ECollectionCrudInfoFlag.CREATE_CHILD_HEAD_PROCESS_URL: "[CREATE CHILD] URL ya motó mpo na bokeli ya mwana",
            ECollectionCrudInfoFlag.CREATE_CHILD_PROCESSING_URL: "[CREATE CHILD] URL ya bosali mpo na bokeli ya mwana",
            ECollectionCrudInfoFlag.FETCH_URL: "[FETCH] URL ya kozwa",
            ECollectionCrudInfoFlag.UPDATE_PROCESSING_URL: "[UPDATE] URL ya bosali mpo na bobongisi",
            ECollectionCrudInfoFlag.UPDATE_HEAD_PROCESS_URL: "[UPDATE] URL ya motó mpo na bobongisi",
            ECollectionCrudInfoFlag.PARENT_FIELD_NAME: "Kombo ya eloko ya moboti",
            ECollectionCrudInfoFlag.DELETE_PROCESSING_URL: "[DELETE] URL ya bosali mpo na bolongoli",
            ECollectionCrudInfoFlag.CREATE_PROCESSING_URL: "[CREATE] URL ya bosali mpo na bokeli",
            ECollectionCrudInfoFlag.CREATE_HEAD_PROCESS_URL: "[CREATE] URL ya motó mpo na bokeli",
            ECollectionCrudInfoFlag.DOWNLOAD_PROCESS_URL: "[DOWNLOAD] URL ya bosali mpo na bokozwa",
            ECollectionCrudInfoFlag.FETCH_ONE_INFO_URL: "[FETCH ONE] URL ya kozwa",
            ECollectionCrudInfoFlag.FETCH_ONE_INFO_FOR_VIEWING_URL: "[FETCH ONE] URL ya kozwa",
            ECollectionCrudInfoFlag.PUT_PROCESSING_URL: "[PUT] URL ya bosali mpo na bokongisa",
            ECollectionCrudInfoFlag.PATCH_PROCESSING_URL: "[PATCH] URL ya bosali mpo na bokongisa",
        },
        ECoolBoxStatus: {
            ECoolBoxStatus.ACTIVE: "Ezali kosala",
            ECoolBoxStatus.INACTIVE: "Ezali kosala te",
            ECoolBoxStatus.IN_SERVICE: "Na mosala",
            ECoolBoxStatus.OUT_OF_SERVICE: "Ezali na mosala te",
        },
        ESrcAttachment: {
            ESrcAttachment.GENERATED: "Esalemi",
            ESrcAttachment.UPLOADED: "Etindami",
        },
        EParentChildHead: {
            EParentChildHead.PARENT_HEAD: "Motó ya Moboti",
            EParentChildHead.CHILD_HEAD: "Motó ya Mwana",
            EParentChildHead.NO_SPECIFICATION: "Spécification ezali te",
        },
        EOperationStatus: {
            EOperationStatus.PENDING: "Ezali kozela",
            EOperationStatus.REVISION: "Botali lisusu",
            EOperationStatus.REJECTED: "Eboyami",
        },
        ETransactionStatus: {
            ETransactionStatus.PENDING: "Ezali kozela",
            ETransactionStatus.VALIDATED: "Endimami",
            ETransactionStatus.REJECTED: "Eboyami",
        },
        AppGeneratorType: {
            AppGeneratorType.HASH_FROM_NAME: "Hash kowuta na Kombo",
            AppGeneratorType.UUID: "UUID",
            AppGeneratorType.CUSTOM: "Ya ndenge mosusu",
        },
        OutputDataType: {
            OutputDataType.DATA_TABLE: "Table ya Données",
            OutputDataType.INPUT_SELECT: "Boponi ya Entrée",
            OutputDataType.CASCADE: "Cascade",
            OutputDataType.CASCADE_ALL: "Cascade Mobimba",
            OutputDataType.TREE: "Nzete",
            OutputDataType.DEFAULT: "Ya mbala nionso",
        },
        AccountStatusFlag: {
            AccountStatusFlag.ACTIVE: "Ezali kosala",
            AccountStatusFlag.INACTIVE: "Ezali kosala te",
            AccountStatusFlag.LOCKED: "Ekangami",
            AccountStatusFlag.SUSPENDED: "Etelemi",
            AccountStatusFlag.REVOQUED: "Elongolami",
            AccountStatusFlag.LOCKED_BY_SYSTEM: "Ekangami na Système",
        },
        ELoginResetPasswordFailStatus: {
            ELoginResetPasswordFailStatus.NORMAL: "Normal",
            ELoginResetPasswordFailStatus.LOCKED: "Ekangami",
            ELoginResetPasswordFailStatus.SUSPENDED: "Etelemi",
            ELoginResetPasswordFailStatus.LOCKED_BY_SYSTEM: "Ekangami na Système",
        },
        EJWTTokenType: {
            EJWTTokenType.MFA_VERIFICATION: "Vérification MFA",
            EJWTTokenType.LOGIN: "Kokota",
            EJWTTokenType.REFRESH_TOKEN: "Kobongisa token",
            EJWTTokenType.PASSWORD_INIT_PROCESS: "Processus ya kobanda Mot de Passe",
            EJWTTokenType.PASSWORD_RESET_PROCESS: "Processus ya kobongisa Mot de Passe",
            EJWTTokenType.PASSWORD_RESET_REDIRECTED: "Kobongisa Mot de Passe Etindami",
        },
        EUserDeviceStatus: {
            EUserDeviceStatus.PENDING_VALIDATION: "Ezali kozela Validation",
            EUserDeviceStatus.ALLOWED: "Endimami",
            EUserDeviceStatus.REVOQUED: "Elongolami",
            EUserDeviceStatus.LOCKED: "Ekangami",
        },
        EOperationStatusFlag: {
            EOperationStatusFlag.DRAFT: "Ebandami",
            EOperationStatusFlag.PENDING_VALIDATION: "Ezali kozela Validation",
            EOperationStatusFlag.IN_PROGRESS: "Ezali kosalema",
            EOperationStatusFlag.COMPLETED: "Esilisami",
        },
        ESubmissionOperationStatusFlag: {
            ESubmissionOperationStatusFlag.DRAFT: "Ebandami",
            ESubmissionOperationStatusFlag.SUBMITED: "Etindami",
        },
        ExpenseChainTransactionStatusFlag: {
            ExpenseChainTransactionStatusFlag.PENDING_VALIDATION: "Ezali kozela",
            ExpenseChainTransactionStatusFlag.VALIDATED: "Endimami",
            ExpenseChainTransactionStatusFlag.REJECTED: "Eboyami",
        },
        EExChainInstDesignation: {
            EExChainInstDesignation.INSTITUTION: "Institution",
            EExChainInstDesignation.SECTION: "Section",
            EExChainInstDesignation.CHAPTER: "Chapitre",
        },
        EExpenseChainBeneficiaryType: {
            EExpenseChainBeneficiaryType.INNER_BENEFICIARY: "Mozwi mbongo ya kati",
            EExpenseChainBeneficiaryType.OUTER_BENEFICIARY: "Mozwi mbongo ya libanda",
        },
        EMultipleValidationType: {
            EMultipleValidationType.CREATE: "Bokeli",
            EMultipleValidationType.HARD_DELETE: "Bolongoli",
            EMultipleValidationType.DOWNLOAD: "Kozwa",
            EMultipleValidationType.SHARE: "Kokabola",
            EMultipleValidationType.UPDATE: "Kobongisa",
        },
        EMultipleValidationStatus: {
            EMultipleValidationStatus.PENDING: "Ezali kozela",
            EMultipleValidationStatus.APPROVED: "Endimami",
            EMultipleValidationStatus.IN_PROGRESS: "Ezali kosalema",
            EMultipleValidationStatus.REJECTED: "Eboyami",
        },
        ERbacActionFlag: {
            ERbacActionFlag.TABLE_ACTION_ADD: "Kobakisa",
            ERbacActionFlag.TABLE_ACTION_ADD_CHILD: "Kobakisa mwana",
            ERbacActionFlag.TABLE_ACTION_UPDATE: "Kobongisa",
            ERbacActionFlag.TABLE_ACTION_DELETE: "Kolongola",
            ERbacActionFlag.TABLE_ACTION_VIEW: "Kotala",
            ERbacActionFlag.STANDALONE_ACTION: "Action ya ye moko",
            ERbacActionFlag.COMMON_LOCK_ACTION: "Kokanga",
            ERbacActionFlag.COMMON_UNLOCK_ACTION: "Kofungola",
            ERbacActionFlag.COMMON_DOWNLOAD_ACTION: "Kozwa",
            ERbacActionFlag.COMMON_UPLOAD_ACTION_FILE: "Kotindami faili",
        },
        ERbacComponentFlag: {
            ERbacComponentFlag.DATA_LIST_COMPONENT: "Molongo de données", 
            ERbacComponentFlag.OWN_INFO_COMPONENT: "Info. yayo moko", 
            ERbacComponentFlag.STANDARD_COMPONENT: "Composant nyoso", 
        },
        EExpenseAccountType:{
            EExpenseAccountType.INTERNAL:"Ya kati",
            EExpenseAccountType.EXTERNAL:"Ya libanda",
            EExpenseAccountType.TRANSIT:"Ya Transit",
        },
        EExpenseVerificatorType:{
            EExpenseVerificatorType.GLOBAL:"Ya mbala nionso",
            EExpenseVerificatorType.ASSOCIATED_TO_ACCOUNT:"Ya mbongo",
        },
        EAccountMovementType:{
            EAccountMovementType.DEBIT: "Ko longola mbongo",
            EAccountMovementType.CREDIT: "Kobakisa mbongo",
            EAccountMovementType.TRANSFER_IN: "Kotinda na kati",
            EAccountMovementType.TRANSFER_OUT: "Kotinda libanda",
        },
        EExpenseClacificationStatusFlag:{
            EExpenseClacificationStatusFlag.NORMAL: "Normal",
            EExpenseClacificationStatusFlag.URGENT: "Ezali kosalema",
            EExpenseClacificationStatusFlag.MORE_URGENT: "Ezali kosalema mpo",
            # EExpenseClacificationStatusFlag.LESS_URGENT: "Ezali kosalema te",
        },
        EAccountMovementFlag:{
            EAccountMovementFlag.PENDING: "Ezali kozela",
            EAccountMovementFlag.VALIDATED: "Endimami",
            EAccountMovementFlag.REJECTED: "Eboyami",
        },
        ESubmissionOperationStatusFlag:{
            ESubmissionOperationStatusFlag.DRAFT: "Ebandami",
            ESubmissionOperationStatusFlag.SUBMITED: "Etindami",
        },
        ExpenseTransactionStatusFlag:{
            ExpenseTransactionStatusFlag.PENDING_VALIDATION: "Ezali kozela Validation",
            ExpenseTransactionStatusFlag.PENDING_BANK_VALIDATION: "Ezali kozela Validation ya Banque",
            ExpenseTransactionStatusFlag.VALIDATED: "Endimami",
            ExpenseTransactionStatusFlag.REJECTED: "Eboyami",
        },
        EExpensePaymentBeneficiaryReceiverType:{
            EExpensePaymentBeneficiaryReceiverType.SAME_BENEFICIARY: "Mozwi mbongo ya kati",
            EExpensePaymentBeneficiaryReceiverType.DELEGATED_PERSON: "Mozwi mbongo ya libanda",
            EExpensePaymentBeneficiaryReceiverType.NONE : "Moko te"
        },
        ExpenseChainTransactionStatusFlag:{
            ExpenseChainTransactionStatusFlag.PENDING_VALIDATION: "Ezali kozela Validation",
            ExpenseChainTransactionStatusFlag.VALIDATED: "Endimami",
            ExpenseChainTransactionStatusFlag.REJECTED: "Eboyami",
        },
        EExpenseOpsBeneficiaryType:{
            EExpenseOpsBeneficiaryType.AGENT_BENEFICIARY: "Agent mbongo",
            EExpenseOpsBeneficiaryType.PHYSICAL_BENEFICIARY: "Mozwi mbongo ya kati",
            EExpenseOpsBeneficiaryType.LEGAL_BENEFICIARY: "Mozwi mbongo ya libanda",
            EExpenseOpsBeneficiaryType.NONE : "Moko te"
        },
        EExpenseOpsPaymentActorType:{
            EExpenseOpsPaymentActorType.FINANCER: "Financier",
            EExpenseOpsPaymentActorType.ACCOUNTANT: "Comptable",
            EExpenseOpsPaymentActorType.BANK: "Bank",
            EExpenseOpsPaymentActorType.NONE : "Moko te"
        },
        EExpensePaymentType:{
            EExpensePaymentType.INSTALLMENT_PAYMENT: "Paiement à terme",
            EExpensePaymentType.ONE_TIME_PAYMENT: "Paiement unique",
            EExpensePaymentType.NONE : "Moko te"
        },
        EMenuChildrenDisplayFlag:{
            EMenuChildrenDisplayFlag.NONE: "Moko te",
            EMenuChildrenDisplayFlag.LEFT_SIDE_MENU: "Menu ya kati ya kati",
            EMenuChildrenDisplayFlag.RIGHT_SIDE_MENU: "Menu ya kati ya libanda",
            EMenuChildrenDisplayFlag.TOP_BAR_MENU: "Menu ya barra ya kati",
            EMenuChildrenDisplayFlag.CENTERED_CARD_MENU: "Menu ya carte ya kati",
            EMenuChildrenDisplayFlag.GRID_CHILDREN_CONTENT: "Content ya grid ya mwana",
        },
        EDataDisplayTypeFlag:{
            EDataDisplayTypeFlag.NONE: "Moko te",
            EDataDisplayTypeFlag.REGULAR_TABLE: "Table ya mbala nionso",
            EDataDisplayTypeFlag.LIST_TILE: "Liste ya tile",
            EDataDisplayTypeFlag.CARD: "Carte",
            EDataDisplayTypeFlag.TREE_TABLE: "Table ya Nzete",
            EDataDisplayTypeFlag.ORG_CHART: "Org Chart",
        },
        ETemplateEngineType:{
            ETemplateEngineType.HTML: "HTML",
            ETemplateEngineType.JINJA: "Jinja",
            ETemplateEngineType.CANVAS: "Canvas",
            ETemplateEngineType.MARKDOWN: "Markdown",
        },
        ELoginStatus:{
            ELoginStatus.NONE: "Aucun",
            ELoginStatus.LOGGED_IN: "Connecté",
            ELoginStatus.LOGGED_OUT: "Déconnecté",
            ELoginStatus.INIT_LOGIN: "Initialisation de la connexion",
            ELoginStatus.INIT_PASSWORD_PROCESS: "Initialisation du processus de mot de passe",
            ELoginStatus.RESET_PASSWORD_PROCESS_VALIDATED: "Processus de réinitialisation du mot de passe validé",
            ELoginStatus.RESET_PASSWORD_PROCESS_COMPLETED: "Processus de réinitialisation du mot de passe terminé",
        },
        EAppGroupFlag:{
            EAppGroupFlag.COMMON: "Common",
        }, 
        ERestoreStatus:{
            ERestoreStatus.NOT_RESTORED: "Ezongisami te",
            ERestoreStatus.RESTORED: "Ezongisami",
            ERestoreStatus.PARTIALLY_RESTORED: "Ezongisami mwa moke",
        }
    },
}

def _ensure_language_map(translations, fallback_language=FALLBACK_LANGUAGE):
    if not translations:
        return
    base_language = fallback_language if fallback_language in translations else (
        DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in translations else next(iter(translations))
    )
    for lang in SUPPORTED_LANGUAGE_CODES:
        translations.setdefault(lang, deepcopy(translations[base_language]))


def _ensure_nested_language_map(translations, fallback_language=FALLBACK_LANGUAGE):
    for _, lang_map in translations.items():
        if not isinstance(lang_map, dict) or not lang_map:
            continue
        base_language = fallback_language if fallback_language in lang_map else (
            DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in lang_map else next(iter(lang_map))
        )
        for lang in SUPPORTED_LANGUAGE_CODES:
            lang_map.setdefault(lang, lang_map[base_language])


_ensure_nested_language_map(TRANSLATION_KEYS)
_ensure_nested_language_map(STATIC_HEADING_TITLE_KEYS)
_ensure_language_map(FIELD_ERROR_TRANSLATED)
_ensure_language_map(TRANSLATIONS)
