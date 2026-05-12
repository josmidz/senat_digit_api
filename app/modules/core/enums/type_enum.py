from enum import Enum, auto
import enum
import string

class EPushNotificationPlatformFlag(str,enum.Enum):
    NONE = "none"
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

class ENotificationChannelFlag(str,enum.Enum):
    NONE = "none"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
 
class EGlobalFormatingFlag(str,enum.Enum):
    DEFAULT = "default"
    FULL_FORMATING_DATA = "full_formatting_data"
    RESUME_FORMATING_DATA = "resume_formatting_data"
    DATA_TABLE_FORMATING_DATA = "data_table_formatting_data"
    DATA_TABLE_FORMATING_DATA_WITH_DEFAULT_DATE_FORMAT = "data_table_formatting_data_with_default_date_format"
    NONE = "none"


class EWalletType(str,enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    
class EGlobalStatus(str,enum.Enum): 
    DRAFT = "draft"
    UNLINKED = "unlinked"
    PRINTED = "printed"
    UNPRINTED = "unprinted"
    GENERATED = "generated"
    CREATED = "created"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    INSTALLMENT_PAID = "installment_paid"
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    LOCKED = "locked"
    EXPIRED = "expired"
    COMPLETED = "completed"
    FROZEN = "frozen"
    REVOQUED = "revoqued"
    BANNED = "banned"
    LEAVED = "leaved"
    LINKED = "linked"
    REMOVED = "removed"
    NONE = "none"
    MEMBERSHIP_REQUESTED = "membership_requested"
    PENDING_VALIDATION = "pending_validation"
    PENDING_ACTIVATION = "pending_activation"
    PENDING_LINK_VALIDATION = "pending_link_validation"
    PENDING_REBATE_GROUP_LINK = "pending_rebate_group_link"
    PENDING_PAYMENT = "pending_payment"
    PENDING_VERIFICATION = "pending_verification"
    FAILED = "failed"
    DELIVERED = "delivered"
    HOLD_PAYMENT = "hold_payment"
    PAYMENT_HOLD_RELEASED = "payment_hold_released"
    PAYMENT_HOLD_RELEASED_REFUNDED = "payment_hold_released_refunded"

 

# new
class EGLOBAL_DATA_TYPE(str, enum.Enum):
    NONE = "none"
    IS_STRING = "is_string"
    IS_AMOUNT = "is_amount"
    IS_NUMBER = "is_number"
    IS_FLOAT = "is_float"
    IS_BOOLEAN = "is_boolean"
    IS_DATE = "is_date"
    IS_OBJECT = "is_object"
    IS_OBJECT_ID = "is_object_id"
    IS_ARRAY_OF_OBJECT = "is_array_of_object"
    IS_ARRAY_OF_SHORT_STRING = "is_array_of_short_string"
    IS_ARRAY = "is_array"
    IS_ENUM = "is_enum"
    IS_SELECT = "is_select"
    IS_CHECKBOX = "is_checkbox"
    IS_RADIO = "is_radio"
    IS_FILE = "is_file"
    IS_IMAGE = "is_image"
    IS_VIDEO = "is_video"
    IS_AUDIO = "is_audio"
    IS_PASSWORD = "is_password"
    IS_INT = "is_int"
    IS_EMAIL = "is_email"
    IS_HTML_EDITOR = "is_html_editor"
    IS_HTML_INPUT = "is_html_input"
    IS_CASCADE = "is_cascade"
    IS_PHONE_NUMBER = "is_phone_number"
    IS_LONG_STRING = "is_long_string"
    IS_DICT = "is_dict"
    IS_COLOR_HEX_CODE = "is_color_hex_code"
 
class EGLOBAL_DATA_TYPE_CONSTRAINTS(str,enum.Enum):
    IS_REQUIRED = "is_required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    IS_EMAIL = "is_email"
    IS_PHONE_NUMBER = "is_phone_number"
    IS_PASSWORD = "is_password"
    IS_OPTIONAL = "is_optional"
    IS_UNIQUE = "is_unique"
    IS_NULLABLE = "is_nullable"
    IS_READ_ONLY = "is_read_only"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    ONLY_FUTURE_DATE = "only_future_date"
    ONLY_PAST_DATE = "only_past_date"
    ONLY_FUTURE_DATE_AND_TODAY = "only_future_date_and_today"
    ONLY_PAST_DATE_AND_TODAY = "only_past_date_and_today"
    ONLY_TODAY_DATE = "only_today_date"
    ONLY_MINOR_AGE = "only_minor_age"
    ONLY_MAJOR_AGE = "only_major_age"
    IS_UUID = "is_uuid"
    PATTERN = "pattern"


class EGLOBAL_EXTRA_METAS(str,enum.Enum):
    STATUS_COLORS = "status_colors"
    ENUM_DATA_SOURCE = "enum_data_source"
    MODEL_REFERENCE = "model_reference"
    CASCADE_REFERENCE = "cascade_reference"
    SELECT_SOURCE_MODEL = "select_source_model"  # @deprecated - use MODEL_REFERENCE
    JOIN_ORGANIZATION_QUERY = "join_organization_query"
    JOIN_PROFIL_OR_ORGANIZATION_QUERY = "join_profil_or_organization_query"
    SKIP_ON_VIEW = "skip_on_view"
    FIELD_ORDERING = "field_ordering"
    UPPERCASED_FIELD_VALUES = "uppercased_field_values"
    DELETE_IF_NOT_USED_IN = "delete_if_not_used_in"
    DELETE_IF_NOT_USED_IN_WITH_CUSTOM_FIELD_NAME = "delete_if_not_used_in_with_custom_field_name"
    EXCLUDED_FIELDS = "excluded_fields"
    UPSERT_IF_EXIST_WITH_PROPS = "upsert_if_exist_with_props"
    REJECT_IF_EXIST = "reject_if_exist"
    HAS_EXTERNAL_INPUT_FORMAT = "has_external_input_format"
    EXTERNAL_INPUT_FORMAT_FROM_REF_BANK_ID_ON_RIB_ACCOUNT_NUMBER="external_input_format_from__ref_bank_id__on_field__rib_account_number_format_str"
    ESSENTIAL_FIELD = "essential_field"
    # @deprecated - DISPLAY_* enums are no longer used in model definitions
    # They are kept for backward compatibility with format methods
    DISPLAY_ON_OVERVIEW = "display_on_overview"
    DISPLAY_VALUE_ON_CASCADE = "display_value_on_cascade"
    DISPLAY_VALUE_ON_INPUT_SELECT = "display_value_on_input_select"
    DISPLAY_VALUE_ON_TREE = "display_value_on_tree"
    SECONDARY_DISPLAY_VALUE_ON_INPUT_SELECT = "secondary_display_value_on_input_select"
    ADDITIONAL_HEAD = "additional_head"
    CASCADE_SOURCE_MODEL = "cascade_source_model"
    DELETE_CASCADE_ON_DELETE_WITH_CUSTOM_FIELD_NAME = "delete_cascade_on_delete_with_custom_field_name"
    SEARCHABLE = "searchable"
    CURRENCY_PROPS = "currency_props"
    CURRENCY_DATA_SOURCE = "currency_data_source"
    LOCK_SINGLE_CURRENCY = "lock_single_currency"
    


class TranslationStrategy(str,enum.Enum):
    DEFAULT = "default"
    PRESERVE = "preserve"
    CASCADE = "cascade"


class ESrcAttachment(str,enum.Enum):
    GENERATED = "generated"
    UPLOADED = "uploaded"


class EParentChildHead(str,enum.Enum):
    PARENT_HEAD = "parent_head"
    CHILD_HEAD = "child_head"
    NO_SPECIFICATION = "no_specification"


class EOperationStatus(str,enum.Enum):
    PENDING = "pending"
    REVISION = "revision"
    REJECTED = "rejected"


class ETransactionStatus(str,enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class AppGeneratorType(str,enum.Enum):
    HASH_FROM_NAME = "hash_from_name"
    UUID = "uuid"
    CUSTOM = "custom"


class OutputDataType(str,enum.Enum):
    TREE_DATA_TABLE = "tree_data_table"
    DATA_TABLE = "data_table"
    INPUT_SELECT = "input_select"
    CASCADE = "cascade"
    CASCADE_ALL = "cascade_all"
    TREE = "tree"
    DEFAULT = "default"


class AccountStatusFlag(str,enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = 'locked'
    SUSPENDED = "suspended"
    REVOQUED = "revoqued"
    LOCKED_BY_SYSTEM = "locked_by_system"


class ELoginResetPasswordFailStatus(str,enum.Enum):
    NORMAL = "normal"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    LOCKED_BY_SYSTEM = "locked_by_system"


class ERegistrationOrigin(str,enum.Enum):
    REGISTRATION = "registration"
    EMAIL_REGISTRATION = "email_registration"
    PHONE_NUMBER_REGISTRATION = "phone_number_registration"
    GOOGLE = "google"
    FACEBOOK = 'facebook'
    TWITTER = 'twitter'
    GITHUB = 'github'

class EUserRegistrationAccountType(str,enum.Enum):
    PERSONAL = "personal"
    BUSINESS = "business"

class EGender(str,enum.Enum):
    # FEMALE_F = "female"
    # MALE_M = "male"
    MALE = "m",
    FEMALE = "f"
    OTHER = "other"

    @classmethod
    def from_label(cls, label: str) -> "EGender":
        """Return the enum member from a human-readable label.
        e.g. 'female' → EGender.FEMALE ('f'), 'male' → EGender.MALE ('m')
        """
        mapping = {"female": cls.FEMALE, "male": cls.MALE, "other": cls.OTHER}
        return mapping.get(label.strip().lower(), cls.OTHER)


class EMultipleValidationType(str,enum.Enum):
    CREATE = "create",
    UPSERT = "upsert",
    UPDATE = "update"
    HARD_DELETE = "hard_delete"
    SOFT_DELETE = "soft_delete"
    DOWNLOAD = "download"
    SHARE = "share"


class EMultipleValidationStatus(str,enum.Enum):
    PENDING = "PENDING",
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"


class EExChainInstDesignation(str,enum.Enum):
    INSTITUTION = "institution",
    SECTION = "section"
    CHAPTER = "chapter"


class ECoolBoxStatus(str,enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    IN_SERVICE = "in_service"
    OUT_OF_SERVICE = "out_of_service"


class EJWTTokenType(str,enum.Enum):
    MFA_VERIFICATION = "mfa_verification"
    LOGIN = "login"
    REFRESH_TOKEN = "refresh_token"
    SIGNATURE = "signature"

    """
    For first step password reset process
    """
    PASSWORD_INIT_PROCESS = "password_init_process"
    """
    For second step password reset process after checking 
    PASSWORD_RESET_REDIRECTED token passed to redirection button
    """
    PASSWORD_RESET_PROCESS = "reset_password_process"
    """
    For last step to reset real password, check token passed to header
    """
    PASSWORD_RESET_REDIRECTED = "reset_password_redirected"

    PENDING_REQUEST_VALIDATION = "pending_request_validation"

    REQUEST_DEVICE_ACTIVATION = "request_device_activation"
    INITIATE_DEVICE_ACTIVATION_PROCESS = "initiate_device_activation_process"

    REGISTRATION_PROCESS = "registration_process"

    """
    Senat-Digit forgot-password flow (unauthenticated, 3 steps).
    Step 1 — /auth/forgot-password/start returns this short-lived
    scope token that binds the next /verify call to the username
    the user typed at /start. ~5 min lifetime.
    """
    PASSWORD_RESET_SESSION = "password_reset_session"
    """
    Step 2 — /auth/forgot-password/verify returns this token after
    the user proves identity by answering their security questions.
    Spent by /auth/forgot-password/complete to rotate the password.
    ~10 min lifetime.
    """
    PASSWORD_RESET = "password_reset"

class EUserDeviceStatus(str,enum.Enum):
    PENDING_VALIDATION = "pending_validation"
    ALLOWED = "allowed"
    REVOQUED = "revoqued"
    LOCKED = "locked"


class EOperationStatusFlag(str,enum.Enum):
    DRAFT = "draft"
    PENDING_VALIDATION = "pending_validation"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class EExpenseClacificationStatusFlag(str,enum.Enum):
    NORMAL = "normal"
    URGENT = "urgent"
    MORE_URGENT = "more_urgent"
    # LESS_URGENT = "less_urgent"


class EExpenseOpsBeneficiaryType(str,enum.Enum):
    AGENT_BENEFICIARY = "agent_beneficiary"
    LEGAL_BENEFICIARY = "legal_beneficiary"
    PHYSICAL_BENEFICIARY = "physical_beneficiary"
    NONE = "none"


class EExpenseOpsPaymentActorType(str,enum.Enum):
    FINANCER = "financer"
    ACCOUNTANT = "accountant"
    BANK = "bank"
    NONE = "none"


class EExpensePaymentType(str,enum.Enum):
    INSTALLMENT_PAYMENT = "installment_payment"
    ONE_TIME_PAYMENT = "one_time_payment"
    NONE = "none"


class EExpensePaymentBeneficiaryReceiverType(str,enum.Enum):
    SAME_BENEFICIARY = "same_beneficiary"
    DELEGATED_PERSON = "delegated_person"
    NONE = "none"


class ExpenseTransactionStatusFlag(str,enum.Enum):
    PENDING_VALIDATION = "pending_validation"
    PENDING_BANK_VALIDATION = "pending_bank_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"
    NONE = "none"


class ESubmissionOperationStatusFlag(str,enum.Enum):
    DRAFT = "draft"
    SUBMITED = "submited"


class EExpenseAccountType(str,enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    TRANSIT = "transit"


class EExpenseVerificatorType(str,enum.Enum):
    GLOBAL = "global"
    ASSOCIATED_TO_ACCOUNT = "associated_to_account"


class ETemplateEngineType(str,enum.Enum):
    HTML = "html"
    JINJA = "jinja"
    CANVAS = "canvas"
    MARKDOWN = "markdown"


class EAccountMovementType(str,enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    POSTPAID_CREDIT = "postpaid_credit"
    POSTPAID_USAGE = "postpaid_usage"
    POSTPAID_REFUND = "postpaid_refund"
    NONE = "none"

class EAccountMovementStatus(str,Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    NONE = "none"

class EAccountMovementFlag(str,enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class ECollectionCrudInfoFlag(str,enum.Enum):
    NONE = "none"
    FETCH_URL = "fetch_url"
    UPDATE_PROCESSING_URL = "update_processing_url"
    UPDATE_HEAD_PROCESS_URL = "update_head_process_url"
    PARENT_FIELD_NAME = "parent_field_name"
    DELETE_PROCESSING_URL = "delete_processing_url"
    CREATE_PROCESSING_URL = "create_processing_url"
    CREATE_HEAD_PROCESS_URL = "create_head_process_url"
    CREATE_CHILD_PROCESSING_URL = "create_child_processing_url"
    DOWNLOAD_PROCESS_URL = "download_process_url"
    CREATE_CHILD_HEAD_PROCESS_URL = "create_child_head_process_url"
    FETCH_ONE_INFO_URL = "fetch_one_info_url"
    FETCH_ONE_INFO_FOR_VIEWING_URL = "fetch_one_info_for_viewing_url"
    PUT_PROCESSING_URL = "put_processing_url"
    PATCH_PROCESSING_URL = "patch_processing_url"


class EMenuChildrenDisplayFlag(str,enum.Enum):
    NONE = "none"
    LEFT_SIDE_MENU = "left_side_menu"
    RIGHT_SIDE_MENU = "right_side_menu"
    TOP_BAR_MENU = "top_bar_menu"
    CENTERED_CARD_MENU = "centered_card_menu"
    GRID_CHILDREN_CONTENT = "grid_children_content"


class EDataDisplayTypeFlag(str,enum.Enum):
    NONE = "none"
    REGULAR_TABLE = "regular_table"
    LIST_TILE = "list_tile"
    CARD = "card"
    TREE_TABLE = "tree_table"
    ORG_CHART = "org_chart"


class EExpenseChainBeneficiaryType(str,enum.Enum):
    INNER_BENEFICIARY = "inner_beneficiary"
    OUTER_BENEFICIARY = "outer_beneficiary"
    NONE = "none"


class ExpenseChainTransactionStatusFlag(str,enum.Enum):
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"


class ExpenseAttachmentFileStatusFlag(str,enum.Enum):
    GENERATED = "generated"
    UPLOADED = "uploaded"


class ExpenseChainAttachmentFileStatusFlag(str,enum.Enum):
    GENERATED = "generated"
    UPLOADED = "uploaded"


class ESudoActionTypeFlag(str,enum.Enum):
    GOLDEN_NUMBER = "goldenNumber"
    TOTP = "totp"
    LOCAL_AUTH = "localAuth"
    QR_CODE = "qrCode"
    PHONE = "phone"
    EMAIL = "email"


class EExpectedActionTypeFlag(str,enum.Enum):
    UNLOCK_SCREEN = "unlockScreen"
    LOCK_SCREEN = "lockScreen"
    SUDO_ACTION = "sudoAction"


class OutputFormat(Enum):
    """
    Enum to define the output format for the sort conversion.
    """
    DEFAULT = auto()  # Returns a list of tuples [(field, direction), ...]
    DICT = auto()     # Returns a dictionary {field: direction, ...}


class EOTPSettings:
    OTP_LENGTH = 6  # Length of the OTP
    OTP_VALIDITY_MINUTES = 5  # Valid for 5 minutes
    OTP_CHARACTERS = string.digits  # Use digits only

# EAppGroupFlag


class EAppGroupFlag(str,enum.Enum):
    COMMON = "common"
    URBAN_TRANSPORTATION = "urban_transportation"
    INTER_URBAIN_TRANSPORTATION = "inter_urbain_transportation"
    SCHOOL_TRANSPORTATION = "school_transportation"
    RENTAL_TRANSPORTATION = "rental_transportation"
    CONFIGURATION = "configuration"


class EUserThemeMode(str,enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ENotificationTunnelFlag(str,enum.Enum):
    NONE = "none"
    USER_ACCOUNT_REGISTRATION = "user_account_registration" 
    USER_ACCOUNT_PASSWORD_RESET = "user_account_password_reset" 
    PAYMENT_OPERATION_FAILED = "payment_operation_failed"
    PAYMENT_OPERATION_SUCCEEDED = "payment_operation_succeeded"
    PAYMENT_OPERATION_PENDING = "payment_operation_pending"
    PAYMENT_OPERATION_APPROVED = "payment_operation_approved"
    BUSINESS_ACCOUNT_REGISTRATION = "business_account_registration"
    WALLET_WITHDRAWAL_REQUESTED = "wallet_withdrawal_requested"
    WALLET_WITHDRAWAL_APPROVED = "wallet_withdrawal_approved"
    WALLET_WITHDRAWAL_REJECTED = "wallet_withdrawal_rejected"
    WALLET_RELOAD_SUCCEEDED = "wallet_reload_succeeded"

class ERestoreStatus(str, enum.Enum):
    NOT_RESTORED = "not_restored"
    RESTORED = "restored"
    PARTIALLY_RESTORED = "partially_restored"


class FormatedOutPut(str,enum.Enum):
    MINIMAL = "minimal"
    FULL = "full"
    DEFAULT = "default"
    RESUME = "resume"
