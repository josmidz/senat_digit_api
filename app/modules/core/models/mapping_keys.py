
from enum import Enum, EnumMeta


# Per-module collection enums proxied through CollectionKey for legacy callers
# that write `CollectionKey.REF_XXX` for a member defined in a module enum.
# Order matters: earlier entries win on name collisions.
_MODULE_COLLECTION_ENUMS: tuple = ()


class _CollectionKeyMeta(EnumMeta):
    def __getattr__(cls, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            for module_enum in _MODULE_COLLECTION_ENUMS:
                if name in module_enum.__members__:
                    return module_enum[name]
            raise

    def __call__(cls, value, names=None, *args, **kwargs):
        # Only proxy value lookup; functional-API enum creation keeps default path.
        if names is not None:
            return super().__call__(value, names, *args, **kwargs)
        try:
            return super().__call__(value)
        except ValueError:
            for module_enum in _MODULE_COLLECTION_ENUMS:
                try:
                    return module_enum(value)
                except ValueError:
                    continue
            raise

    def __contains__(cls, item):
        if super().__contains__(item):
            return True
        return any(item in module_enum for module_enum in _MODULE_COLLECTION_ENUMS)


class CollectionKey(str, Enum, metaclass=_CollectionKeyMeta):
    """Enum mapping for MongoDB collections.
    
    Each member stores both the collection name (camelCase) and model name (snake_case).
    
    Attributes:
        value: The MongoDB collection name (camelCase), e.g., "refMfas"
        model_name: The Python model name (snake_case), e.g., "ref_mfa"
    
    Usage:
        >>> CollectionKey.REF_MFAS.value
        'refMfas'
        >>> CollectionKey.REF_MFAS.model_name
        'ref_mfa'
        >>> str(CollectionKey.REF_MFAS)
        'refMfas'
    """
    
    # Authentication & Security
    REF_MFAS = ("refMfas", "ref_mfa")
    CFG_USER_MFA = ("cfgUserMfas", "cfg_user_mfa")
    CFG_USER_DEVICE = ("cfgUserDevices", "cfg_user_device")
    CFG_USER_PIN = ("cfgUserPins", "cfg_user_pin")
    CFG_USER_APP_STORE = ("cfgUserAppStores", "cfg_user_app_store")
    OPS_USER_LOGIN_HISTORY = ("opsUserLoginHistory", "ops_user_login_history")

    # Entity & Currency
    CFG_ENTITY_CURRENCY = ("cfgEntityCurrency", "cfg_entity_currency")
    CFG_CURRENT_ENTITY = ("cfgCurrentEntities", "cfg_current_entity")
    # REF_ACCESS = ("refAccesses", "ref_access")
    CFG_TRANSLATION = ("cfgTranslations", "cfg_translation")
    REF_NAMED_ENTITY = ("refNamedEntities", "ref_named_entity")
    REF_ENTITY = ("refEntities", "ref_entity")
    REF_APPLICATION_GROUP = ("refApplicationGroups", "ref_application_group")
    CFG_COUNTRY_RELATED_APPLICATION_GROUP = ("cfgCountryRelatedApplicationGroups", "cfg_country_related_application_group")
    REF_CURRENCY = ("refCurrencies", "ref_currency")
    CFG_CURRENCY_EXCHANGE = ("cfgCurrencyExchanges", "cfg_currency_exchange")
    SAAS_VERSION = ("cfgSaasVersions", "cfg_saas_version")
    CFG_SYSTEM_ORGANIZATION = ("cfgSystemOrganizations", "cfg_system_organization")
    CFG_ORGANIZATION_SUDO_ACTION = ("cfgOrganizationSudoActions", "cfg_organization_sudo_action")

    # RLS - Row Level Security
    REF_SUDO_RLS_SECURITY_GROUP = ("refSudoRlsSecurityGroups", "ref_sudo_rls_security_group")
    REF_SUDO_RLS_SECURITY_GROUP_USER = ("refSudoRlsSecurityGroupUsers", "ref_sudo_rls_security_group_user")
    CFG_ORGANIZATION_RLS = ("cfgOrganizationRls", "cfg_organization_rls")
    CFG_RLS_SETUP = ("cfgRlsSetup", "cfg_rls_setup")
    CFG_SUDO_ACTION_SETUP = ("cfgSudoActionSetup", "cfg_sudo_action_setup")
    CFG_SUDO_ACTION_ACCESS = ("cfgSudoActionAccess", "cfg_sudo_action_access")
    CFG_RLS_ACCESS = ("cfgRlsAccesses", "cfg_rls_access")
    CFG_SYSTEM_TOWN_ENTITY = ("cfgSystemTownEntities", "cfg_system_town_entity") 
    
    # Archive & Files
    ARCH_FOLDER = ("archFolders", "arch_folder")
    ARCH_FILE = ("archFiles", "arch_file")

    # RBAC - Role Based Access Control
    RBAC_PROFILE = ("rbacProfiles", "rbac_profil")
    SYS_ORGANIZATION = ("sysOrganizations", "sys_organization")
    SYS_ORGANIZATION_AGENT = ("sysOrganizationAgents", "sys_organization_agent")
    RBAC_ROLE = ("rbacRoles", "rbac_role")
    SYS_USER = ("sysUsers", "sys_user")
    SYS_MENU = ("sysMenus", "sys_menu")
    SYS_APPLICATION = ("sysApplications", "sys_application")
    CFG_USER_PROFIL_ROLE = ("cfgUserProfileRoles", "cfg_user_profile_role")

    # User Configuration
    CFG_USER_PROFILE_ROLE = ("cfgUserProfileRoles", "cfg_user_profile_role")
    CFG_USER_CONFIG = ("cfgUserConfigs", "cfg_user_config")
    CFG_USER_QUESTION = ("cfgUserQuestions", "cfg_user_question")
    REF_LANGUAGE = ("refLanguages", "ref_language")
    CFG_ICON_API_CONSUMER = ("cfgIconApiConsumers", "cfg_icon_api_consumer")
    CFG_SAAS_CONFIG = ("cfgSaasConfigs", "cfg_saas_config")
    REF_THEME = ("refThemes", "ref_theme")
    REF_PERSON_TYPE = ("refPersonTypes", "ref_person_type")
    SYS_PERSON = ("sysPersons", "sys_person")
    SYS_PERSON_TYPE = ("sysPersonTypes", "sys_person_type")
    SYS_FAMILY_UNIT = ("sysFamilyUnits", "sys_family_unit")
    SYS_PERSON_RELATIONSHIP = ("sysPersonRelationships", "sys_person_relationship")
    SYS_PERSON_GUARDIANSHIP = ("sysPersonGuardianships", "sys_person_guardianship")
    CFG_USER_QUESTION_RESPONSE = ("cfgUserQuestionResponses", "cfg_user_question_response")
    CFG_USER_AUTH_SETUP = ("cfgUserAuthSetups", "cfg_user_auth_setup")
    REF_AUTH_QUESTION_CATEGORY = ("refAuthQuestionCategories", "ref_auth_question_category")
    REF_AUTH_QUESTION = ("refAuthQuestions", "ref_auth_question")
    CFG_USER_TOTP = ("cfgUserTotp", "cfg_user_totp")

    # Data Collection
    REF_DATA_TO_COLLECT_TYPE = ("refDataToCollectTypes", "ref_data_to_collect_type")
    OPS_DATA_COLLECTED = ("opsDataCollected", "ops_data_collected")
    
    # RBAC Endpoints & Permissions
    RBAC_ENDPOINT = ("rbacEndpoints", "rbac_endpoint")
    RBAC_PRIVILEGE = ("rbacPrivileges", "rbac_privilege")
    RBAC_PERMISSION_ROLE = ("rbacPermissionRoles", "rbac_permission_role")
    RBAC_PERMISSION = ("rbacPermissions", "rbac_permission")
    
    # Documents
    CFG_DUE_DOCUMENT = ("cfgDueDocuments", "cfg_due_document")
    REF_DOCUMENT = ("refDocuments", "ref_document")
    CFG_REQUIRED_DOCUMENT = ("cfgRequiredDocuments", "cfg_required_document")
    
    # API & Contact
    REF_API_CONSUMER = ("refApiConsumers", "ref_api_consumer")
    OPS_CONTACT_US = ("opsContactUs", "ops_contact_us")
    
    # Reference Data
    REF_KINSHIP_TYPE = ("refKinshipTypes", "ref_kinship_type")
    REF_FIELD_OF_STUDY = ("refFieldOfStudies", "ref_field_of_study")
    REF_SCHOOL_LEVEL = ("refSchoolLevels", "ref_school_level")
    REF_MARITAL_STATUS = ("refMaritalStatuses", "ref_marital_status")
    REF_COLOR = ("refColors", "ref_color")
    REF_BLOOD_TYPE = ("refBloodTypes", "ref_blood_type")
    REF_ICON = ("refIcons", "ref_icon")
    
    
    # Senat-Digit feature modules (§3.5)
    SESSION_MEETING = ("sessionMeetings", "session_meeting")
    SESSION_PARTICIPANT = ("sessionParticipants", "session_participant")
    AGENDA_ITEM = ("agendaItems", "agenda_item")
    DOCUMENT_META = ("documentMetas", "document_meta")
    DOCUMENT_VERSION = ("documentVersions", "document_version")
    DOCUMENT_AMENDMENT = ("documentAmendments", "document_amendment")
    VOTE_CONFIG = ("voteConfigs", "vote_config")
    VOTE_BALLOT = ("voteBallots", "vote_ballot")
    VOTE_PROXY = ("voteProxies", "vote_proxy")
    VOTE_RESULT = ("voteResults", "vote_result")
    PRESENCE_SIGNATURE = ("presenceSignatures", "presence_signature")
    PAROLE_REQUEST = ("paroleRequests", "parole_request")
    AUDIT_EVENT = ("auditEvents", "audit_event")

    # Notifications
    NTF_NOTIFICATION = ("ntfNotifications", "ntf_notification")

    # Fiscal & Budget
    CFG_FISCAL_YEAR = ("cfgFiscalYears", "cfg_fiscal_year")
    REF_INSTITUTION = ("refInstitutions", "ref_institution")
    REF_EXPENSE = ("refExpenses", "ref_expense")
    REF_EXPENSE_NATURE = ("refExpenseNatures", "ref_expense_nature")
    REF_BUDGET_YEAR = ("refBudgetYears", "ref_budget_year")
    
    # Attachments
    SRC_ATTACHMENT = ("archAttachments", "arch_attachment")
    OPS_EXPENSE_ATTACHMENT = ("opsExpenseAttachments", "ops_expense_attachment")
    OPS_EXPENSE_ATTACH_DOC_TYPE = ("opsExpenseAttachDocTypes", "ops_expense_attach_doc_type")

    # RBAC Titles & Paths
    RBAC_TITLE = ("rbacTitles", "rbac_title")
    RBAC_PATH_GUARD = ("rbacPathGuards", "rbac_path_guard")
    RBAC_PERMISSION_TARGET = ("rbacPermissionTargets", "rbac_permission_target")
    
    # Country & Budget
    REF_COUNTRY = ("refCountries", "ref_country")
    REF_TRANSPORT_SERVICE = ("refTransportServices", "ref_transport_service")
    REF_VEHICLE_TYPE = ("refVehicleTypes", "ref_vehicle_type")
    REF_VEHICLE = ("refVehicles", "ref_vehicle")
    REF_VEHICLE_BREAKDOWN = ("refVehicleBreakdowns", "ref_vehicle_breakdown")
    CFG_VEHICLE_AFFECTATION = ("cfgVehicleAffectations", "cfg_vehicle_affectation")
    CFG_VEHICLE_DISPONIBILITY = ("cfgVehicleDisponibilities", "cfg_vehicle_disponibility")
    CFG_BUDGET_YEAR = ("cfgBudgetYears", "cfg_budget_year")

    # Organization Configuration
    CFG_GRADE = ("cfgGrades", "cfg_grade")
    CFG_FUNCTION = ("cfgFunctions", "cfg_function")
    REF_BANK = ("refBanks", "ref_bank")
    REF_BENEFICIARY = ("refBeneficiaries", "ref_beneficiary")
    CFG_BANK = ("cfgBanks", "cfg_bank")
    CFG_BANK_ACCOUNT_NUMBER = ("cfgBankAccountNumbers", "cfg_bank_account_number")
    CFG_LEGAL_BENEFICIARY = ("cfgLegalBeneficiaries", "cfg_legal_beneficiary")
    CFG_ORGANISM_CHART = ("cfgOrganismCharts", "cfg_organism_chart")
    REF_RELIGION = ("refReligions", "ref_religion")
    REF_EYE_COLOR = ("refEyeColors", "ref_eye_color")
    REF_INSTITUTION_TYPE = ("refInstitutionTypes", "ref_institution_type")
    
    # Credit & Accountant Management
    CFG_SECTION_CREDIT_MANAGER = ("cfgCreditManagers", "cfg_credit_manager")
    CFG_SECTION_CREDIT_SUB_MANAGER = ("cfgCreditSubManagers", "cfg_credit_sub_manager")
    CFG_ORG_PUBLIC_ACCOUNTANT = ("cfgPublicAccountants", "cfg_public_accountant")
    
    # Expense Operations
    OPS_EXPENSE_OPERATION = ("opsExpenseOperations", "ops_expense_operation")
    OPS_EXPENSE_TRANSACTION = ("opsExpenseTransactions", "ops_expense_transaction")
    OPS_EXPENSE_VERIFICATOR = ("opsExpenseVerificators", "ops_expense_verificator")
    OPS_EXPENSE_COMMENT = ("opsExpenseComments", "ops_expense_comment")
    CFG_USER_SIGNATURE = ("cfgUserSignatures", "cfg_user_signature")
    
    # Document Templates
    REF_DOCUMENT_TEMPLATE = ("refDocumentTemplates", "ref_document_template")
    REF_DOCUMENT_TEMPLATE_TYPE = ("refDocumentTemplateTypes", "ref_document_template_type")
    REF_DOCUMENT_TEMPLATE_PAGE = ("refDocumentTemplatePages", "ref_document_template_page")
    
    # Validation & Components
    OPS_VALIDATION_REQUEST = ("opsValidationRequests", "ops_validation_request")
    OPS_VALIDATION_REQUEST_USER = ("opsValidationRequestUsers", "ops_validation_request_user")
    SYS_CROSS_VALIDATION_ORGANIZATION = ("sysCrossValidationOrganizations", "sys_cross_validation_organization")
    RBAC_COMPONENT = ("rbacComponents", "rbac_component")
    RBAC_ACTION = ("rbacActions", "rbac_action")
    RBAC_SUDO_ACTION = ("rbacSudoActions", "rbac_sudo_action")
    RBAC_SUDO_ACTION_ORGANIZATION = ("rbacSudoActionOrganizations", "rbac_sudo_action_organization")
    RBAC_SUDO_ACTION_CONFIRMATION_TYPE = ("rbacSudoActionConfirmationTypes", "rbac_sudo_action_confirmation_type")
    RBAC_USER_VALIDATOR = ("rbacUserValidators", "rbac_user_validator")
    
    # Expense Types & Accounts
    REF_EXPENSE_TYPE = ("refExpenseTypes", "ref_expense_type")
    OPS_EXPENSE_ACCOUNT = ("opsExpenseAccounts", "ops_expense_account")
    RBAC_RESTRICTED_API_CONSUMER = ("rbacRestrictedApiConsumers", "rbac_restricted_api_consumer")
    REF_BANK_TYPE = ("refBankTypes", "ref_bank_type")
    RBAC_RESTRICTED_PROFIL = ("rbacRestrictedProfils", "rbac_restricted_profil")
    
    # Collections & Display
    REF_COLLECTION = ("refCollections", "ref_collection")
    REF_COLLECTION_CRUD_INFO = ("refCollectionCrudInfos", "ref_collection_crud_info")
    CFG_DATA_DISPLAY_TYPE = ("cfgDataDisplayTypes", "cfg_data_display_type")
    REF_DATA_DISPLAY_TYPE = ("refDataDisplayTypes", "ref_data_display_type")
    REF_CHILDREN_DISPLAY_TYPE = ("refChildrenDisplayTypes", "ref_children_display_type")
    CFG_CHILDREN_DISPLAY_TYPE = ("cfgChildrenDisplayTypes", "cfg_children_display_type")
    
    # Expense Account History & Security
    OPS_EXPENSE_ACCOUNT_HISTORY = ("opsExpenseAccountHistories", "ops_expense_account_history")
    CFG_EXPENSE_ACCOUNT_ACCOUNTANT = ("cfgExpenseAccountAccountants", "cfg_expense_account_accountant")
    OPS_EXPENSE_AMOUNT = ("opsExpenseAmounts", "ops_expense_amount")
    CFG_PHYSICAL_BENEFICIARY = ("cfgPhysicalBeneficiaries", "cfg_physical_beneficiary")
    
    # System & Locks
    DISTRIBUTED_LOCKS = ("archDistributedLocks", "arch_distributed_lock")
    CFG_ENTITY_AVAILABILITY = ("cfgEntityAvailabilities", "cfg_entity_availability")
    
    # Expense Chain Steps
    REF_BASIC_EXPENSE_STEPS = ("refBasicExpenseChainSteps", "ref_basic_expense_chain_step")
    CFG_BASIC_EXPENSE_STEPS = ("cfgBasicExpenseChainSteps", "cfg_basic_expense_chain_step")
    REF_BASIC_EXPENSE_STEP = ("refBasicExpenseSteps", "ref_basic_expense_step")
    CFG_BASIC_EXPENSE_STEP = ("cfgBasicExpenseSteps", "cfg_basic_expense_step")

    # Expense Chain Bank
    CFG_EXPCHAIN_BANK_AVAILABILITY = ("cfgExpchainBankAvailabilities", "cfg_expchain_bank_availability")
    CFG_EXPCHAIN_ORG_AS_BANK = ("cfgExpchainOrgAsBanks", "cfg_expchain_org_as_bank")
    CFG_EXPCHAIN_ORG_BANK_CONTRACT = ("cfgExpchainOrgBankContracts", "cfg_expchain_org_bank_contract")
    CFG_EXPCHAIN_ORG_BANK_LINK = ("cfgExpchainOrgBankLinks", "cfg_expchain_org_bank_link")

    # Payment & Activities
    OPS_EXPENSE_PAYMENT_PROGRESS = ("opsExpensePaymentProgress", "ops_expense_payment_progress")
    OPS_USER_LOGIN_DAILY_ACTIVITY = ("opsUserLoginDailyActivities", "ops_user_login_daily_activity")
    OPS_BASIC_EXPENSE_STEP_TEMPLATE = ("opsBasicExpenseStepTemplates", "ops_basic_expense_step_template")
    CFG_APPLICATION_GROUP_ACCESSIBILITY = ("cfgApplicationGroupAccessibilities", "cfg_application_group_accessibility")
    
    # Telephone Networks
    REF_TELEPHONE_NETWORK = ("refTelephoneNetworks", "ref_telephone_network")
    CFG_TELEPHONE_NETWORK_RELATED_COUNTRY = ("cfgTelephoneNetworkRelatedCountries", "cfg_telephone_network_related_country")
    CFG_COUNTRY_RELATED_APP_GROUP = ("cfgCountryRelatedApplicationGroups", "cfg_country_related_app_group")
    
    CFG_SYSTEM_COUNTRY = ("cfgSystemCountries", "cfg_system_country")
    CFG_FCM_CONFIG = ("cfgFcmConfigs", "cfg_fcm_config")
    # F10: per-org KMS + storage configuration. One row per
    # `sys_organization_id`. `kms_master_key_id` resolves the master key
    # used by `VoteCryptoService` to seal per-resolution DEKs.
    CFG_STORAGE = ("cfgStorages", "cfg_storage")
    CFG_COUNTRY_RELATED_PHONE_PREFIX = ("cfgCountryRelatedPhonePrefixes", "cfg_country_related_phone_prefix")
    CFG_COUNTRY_RELATED_COUNTRY_CODE = ("cfgCountryRelatedCountryCodes", "cfg_country_related_country_code")
    CFG_COUNTRY_RELATED_CURRENCY = ("cfgCountryRelatedCurrencies", "cfg_country_related_currency")
    CFG_COUNTRY_RELATED_EWALLET_PREFIX = ("cfgCountryRelatedEWalletPrefixes", "cfg_country_related_ewallet_prefix")
    CFG_BANK_RELATED_COUNTRY = ("cfgBankRelatedCountries", "cfg_bank_related_country")

    # Notifications
    CFG_NOTIFICATION_CONFIG = ("cfgNotificationConfigs", "cfg_notification_config")
    REF_NOTIFICATION_CHANNEL = ("refNotificationChannels", "ref_notification_channel")
    REF_NOTIFICATION_TUNNEL = ("refNotificationTunnels", "ref_notification_tunnel")
    CFG_RELATED_SYSTEM_PROFIL = ("cfgRelatedSystemProfils", "cfg_related_system_profil")

    # Default Currency
    CFG_DEFAULT_RELATED_CURRENCY = ("cfgDefaultRelatedCurrencies", "cfg_default_related_currency")
    OPS_DISTRIBUTED_LOCK = ("opsDistributedLocks", "ops_distributed_lock")

    # Security Reports & Account Management
    OPS_SUSPICIOUS_ACTIVITY_REPORT = ("opsSuspiciousActivityReports", "ops_suspicious_activity_report")
    CFG_TRUSTED_DEVICE = ("cfgTrustedDevices", "cfg_trusted_device")
    OPS_ACCOUNT_FREEZE = ("opsAccountFreezes", "ops_account_freeze")

    # Ops History (update & delete audit trail)
    OPS_UPDATE_HISTORY = ("opsUpdateHistories", "ops_update_history")
    OPS_DELETE_HISTORY = ("opsDeleteHistories", "ops_delete_history")

    # Organization CRUD Logs
    CFG_OPS_LOG_SETUP = ("cfgOpsLogSetups", "cfg_ops_log_setup")
    OPS_ORGANIZATION_LOG = ("opsOrganizationLogs", "ops_organization_log")



    def __new__(cls, collection_name: str, model_name: str):
        """Create a new CollectionKey member.
        
        Args:
            collection_name: The MongoDB collection name (camelCase).
            model_name: The Python model name (snake_case).
        
        Returns:
            A new CollectionKey instance that behaves as a string.
        """
        obj = str.__new__(cls, collection_name)
        obj._value_ = collection_name
        obj.model_name = model_name
        return obj

    
