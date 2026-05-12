from enum import Enum
from typing import Dict
from app.modules.core.models.mapping_keys import CollectionKey

from app.modules.auth.enums.common import ModelMetadata
from app.modules.auth.models.ops_user_login_history.ops_user_login_history_model import OpsUserLoginHistoryModel
from app.modules.auth.models.cfg_user_config.cfg_user_config_model import CfgUserConfigModel
from app.modules.auth.models.cfg_user_device.cfg_user_device_model import CfgUserDeviceModel
from app.modules.auth.models.cfg_user_pin.cfg_user_pin_model import CfgUserPinModel
from app.modules.auth.models.cfg_user_mfa.cfg_user_mfa_model import CfgUserMfaModel
from app.modules.auth.models.ref_mfa.ref_mfa_model import RefMfaModel
from app.modules.core.models.cfg_bank.cfg_bank_model import CfgBankModel
from app.modules.core.models.cfg_children_display_type.cfg_children_display_type_model import CfgChildrenDisplayTypeModel
from app.modules.core.models.cfg_user_app_store.cfg_user_app_store_model import CfgUserAppStoreModel
from app.modules.core.models.cfg_country_currency.cfg_country_currency_model import CfgCountryCurrencyModel
from app.modules.core.models.cfg_currency_exchange.cfg_currency_exchange_model import CfgCurrencyExchangeModel
from app.modules.core.models.cfg_data_display_type.cfg_data_display_type_model import CfgDataDisplayTypeModel
from app.modules.core.models.cfg_due_document.cfg_due_document_model import CfgDueDocumentModel
from app.modules.core.models.cfg_fiscal_year.cfg_fiscal_year_model import CfgFiscalYearModel
from app.modules.core.models.cfg_function.cfg_function_model import CfgFunctionModel
from app.modules.core.models.cfg_grade.cfg_grade_model import CfgGradeModel
from app.modules.core.models.cfg_icon_api_consumer.cfg_icon_api_consumer_model import CfgIconApiConsumerModel
from app.modules.core.models.cfg_organism_chart.cfg_organism_chart_model import CfgOrganismChartModel
from app.modules.core.models.cfg_required_document.cfg_required_document_model import CfgRequiredDocumentModel
from app.modules.core.models.cfg_user_profil_role.cfg_user_profil_role_model import CfgUserProfilRoleModel
from app.modules.core.models.ntf_notification.ntf_notification_model import NtfNotificationModel
from app.modules.core.models.ops_contact_us.ops_contact_us_model import OpsContactUsModel
from app.modules.core.models.ops_distributed_lock.ops_distributed_lock_model import OpsDistributedLockModel
from app.modules.core.models.rbac_action.rbac_action_model import RbacActionModel
from app.modules.core.models.rbac_component.rbac_component_model import RbacComponentModel
from app.modules.core.models.rbac_endpoint.rbac_endpoint_model import RbacEndpointModel
from app.modules.core.models.rbac_path_guard.rbac_path_guard_model import RbacPathGuardModel
from app.modules.core.models.rbac_permission.rbac_permission_model import RbacPermissionModel
from app.modules.core.models.rbac_permission_role.rbac_permission_role_model import RbacPermissionRoleModel
from app.modules.core.models.rbac_permission_target.rbac_permission_target_model import RbacPermissionTargetModel
from app.modules.core.models.rbac_privilege.rbac_privilege_model import RbacPrivilegeModel
from app.modules.core.models.rbac_restricted_api_consumer.rbac_restricted_api_consumer_model import RbacRestrictedApiConsumerModel
from app.modules.core.models.rbac_restricted_profil.rbac_restricted_profil_model import RbacRestrictedProfilModel
from app.modules.core.models.rbac_role.rbac_role_model import RbacRoleModel
from app.modules.core.models.rbac_title.rbac_title_model import RbacTitleModel

from app.modules.core.models.ref_api_consumer.ref_api_consumer_model import RefApiConsumerModel
from app.modules.core.models.ref_application_group.ref_application_group_model import RefApplicationGroupModel
from app.modules.core.models.ref_bank.ref_bank_model import RefBankModel
from app.modules.core.models.ref_bank_type.ref_bank_type_model import RefBankTypeModel
from app.modules.core.models.ref_beneficiary.ref_beneficiary_model import RefBeneficiaryModel
from app.modules.core.models.ref_blood_type.ref_blood_type_model import RefBloodTypeModel
from app.modules.core.models.ref_budget_year.ref_budget_year_model import RefBudgetYearModel
from app.modules.core.models.ref_children_display_type.ref_children_display_type_model import RefChildrenDisplayTypeModel
from app.modules.core.models.ref_collection.ref_collection_model import RefCollectionModel
from app.modules.core.models.ref_collection_crud_info.ref_collection_crud_info_model import RefCollectionCrudInfoModel
from app.modules.core.models.ref_color.ref_color_model import RefColorModel
from app.modules.core.models.ref_country.ref_country_model import RefCountryModel
from app.modules.core.models.ref_currency.ref_currency_model import RefCurrencyModel
from app.modules.core.models.ref_data_display_type.ref_data_display_type_model import RefDataDisplayTypeModel
from app.modules.core.models.ref_data_to_collect.ref_data_to_collect_model import RefDataToCollectTypesModel
from app.modules.core.models.ref_document.ref_document_model import RefDocumentModel
from app.modules.core.models.ref_document_template.ref_document_template_model import RefDocumentTemplateModel
from app.modules.core.models.ref_document_template_page.ref_document_template_page_model import RefDocumentTemplatePageModel
from app.modules.core.models.ref_document_template_type.ref_document_template_type_model import RefDocumentTemplateTypeModel
from app.modules.core.models.ref_entity.ref_entity_model import RefEntityModel
from app.modules.core.models.ref_eye_color.ref_eye_color_model import RefEyeColorModel
from app.modules.core.models.ref_field_of_study.ref_field_of_study_model import RefFieldOfStudyModel
from app.modules.core.models.ref_icon.ref_icon_model import RefIconModel
from app.modules.core.models.ref_language.ref_language_model import RefLanguageModel
from app.modules.core.models.ref_marital_status.ref_marital_status_model import RefMaritalStatusModel
from app.modules.core.models.ref_named_entity.ref_named_entity_model import RefNamedEntityModel
from app.modules.core.models.ref_religion.ref_religion_model import RefReligionModel
from app.modules.core.models.ref_school_level.ref_school_level_model import RefSchoolLevelModel
from app.modules.core.models.ref_theme.ref_theme_model import RefThemeModel
from app.modules.core.models.ref_telephone_network.ref_telephone_network_model import RefTelephoneNetworkModel
from app.modules.core.models.saas_version.saas_version_model import SaasVersionModel
from app.modules.core.models.sys_application.sys_application_model import SysApplicationModel
from app.modules.core.models.sys_menu.sys_menu_model import SysMenuModel
from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
from app.modules.core.models.sys_organization_agent.sys_organization_agent_model import SysOrganizationAgentModel
from app.modules.core.models.sys_person.sys_person_model import SysPersonModel
from app.modules.core.models.sys_person_type.sys_person_type_model import RefPersonTypeModel
from app.modules.core.models.rbac_profile.rbac_profile_model import RbacProfileModel
from app.modules.core.models.sys_user.sys_user_model import SysUserModel
from app.modules.edocs.models.arch_file.arch_file_model import ArchFileModel
from app.modules.edocs.models.arch_folder.arch_folder_model import ArchFolderModel

from app.modules.core.models.cfg_saas_config.cfg_saas_config_model import CfgSaasConfigModel
from app.modules.core.models.cfg_entity_availability.cfg_entity_availability_model import CfgEntityAvailabilityModel

from app.modules.auth.models.ops_user_login_daily_activity.ops_user_login_daily_activity_model import OpsUserLoginDailyActivityModel
from app.modules.core.models.cfg_country_related_country_code.cfg_country_related_country_code_model import CfgCountryRelatedCountryCodeModel
from app.modules.core.models.cfg_country_related_phone_prefix.cfg_country_related_phone_prefix_model import CfgCountryRelatedPhonePrefixModel
from app.modules.core.models.cfg_country_related_wallet_prefix.cfg_country_related_wallet_prefix_model import CfgCountryRelatedWalletPrefixModel

from app.modules.core.models.cfg_country_related_currency.cfg_country_related_currency_model import CfgCountryRelatedCurrencyModel

from app.modules.core.models.cfg_bank_related_country.cfg_bank_related_country_model import CfgBankRelatedCountryModel 
from app.modules.core.models.cfg_application_group_accessibility.cfg_application_group_accessibility_model import CfgApplicationGroupAccessibilityModel 
from app.modules.core.models.cfg_telephone_network_related_country.cfg_telephone_network_related_country_model import CfgTelephoneNetworkRelatedCountryModel
from app.modules.core.models.cfg_country_related_application_group.cfg_country_related_application_group_model import CfgCountryRelatedApplicationGroupModel 
from app.modules.core.models.cfg_notification_config.cfg_notification_config_model import CfgNotificationConfigModel
from app.modules.core.models.ref_notification_channel.ref_notification_channel_model import RefNotificationChannelModel
from app.modules.core.models.ref_notification_tunnel.ref_notification_tunnel_model import RefNotificationTunnelModel
from app.modules.core.models.cfg_related_system_profil.cfg_related_system_profil_model import CfgRelatedSystemProfilModel

from app.modules.core.models.cfg_default_related_currency.cfg_default_related_currency_model import CfgDefaultRelatedCurrencyModel
from app.modules.core.models.ops_update_history.ops_update_history_model import OpsUpdateHistoryModel
from app.modules.core.models.ops_delete_history.ops_delete_history_model import OpsDeleteHistoryModel
from app.modules.core.models.cfg_system_country.cfg_system_country_model import CfgSystemCountryModel
from app.modules.auth.models.cfg_user_question_response.cfg_user_question_response_model import CfgUserQuestionResponseModel
from app.modules.auth.models.ref_auth_question.ref_auth_question_model import RefAuthQuestionModel
from app.modules.auth.models.ref_auth_question_category.ref_auth_question_category_model import RefAuthQuestionCategoryModel
from app.modules.auth.models.cfg_user_auth_setup.cfg_user_config_model import CfgUserAuthSetupModel
from app.modules.core.models.cfg_bank_account_number.cfg_bank_account_number_model import CfgBankAccountNumberModel
from app.modules.core.models.cfg_fcm_config.cfg_fcm_config_model import CfgFcmConfigModel 
from app.modules.core.models.cfg_system_organization.cfg_system_organization_model import CfgSystemOrganizationModel
from app.modules.security.models.cfg_organization_sudo_action.cfg_organization_sudo_action_model import CfgOrganizationSudoActionModel
# from app.modules.security.models.cfg_rls_global_access.cfg_rls_global_access_model import CfgRlsGlobalAccessModel
# from app.modules.security.models.cfg_rls_row_access.cfg_rls_row_access_model import CfgRowAccessModel
from app.modules.security.models.cfg_user_signature.cfg_user_signature_model import CfgUserSignatureModel
from app.modules.security.models.cfg_user_totp.cfg_user_totp_model import CfgUserTotpModel
from app.modules.security.models.ops_validation_request.ops_validation_request_model import OpsValidationRequestModel
from app.modules.security.models.ops_validation_request_user.ops_validation_request_user_model import OpsValidationRequestUserModel
from app.modules.security.models.sys_cross_validation_organization.sys_cross_validation_organization_model import SysCrossValidationOrganizationModel
from app.modules.security.models.rbac_sudo_action.rbac_sudo_action_model import RbacSudoActionModel
from app.modules.security.models.rbac_sudo_action_confirmation_type.rbac_sudo_action_confirmation_type_model import RbacSudoActionConfirmationTypeModel
from app.modules.security.models.rbac_sudo_action_organization.rbac_sudo_action_organization_model import RbacSudoActionOrganizationModel
from app.modules.security.models.rbac_user_validator.rbac_user_validator_model import RbacUserValidatorModel
from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel
from app.modules.security.models.ref_sudo_rls_security_group_user.ref_sudo_rls_security_group_user_model import RefSudoRlsSecurityGroupUserModel
# from app.modules.security.models.cfg_rls_global_access.cfg_rls_global_access_model import CfgRlsGlobalAccessModel
from app.modules.security.models.cfg_organization_rls.cfg_organization_rls_model import CfgOrganizationRlsModel
from app.modules.security.models.cfg_rls_setup.cfg_rls_setup_model import CfgRlsSetupModel
from app.modules.security.models.cfg_sudo_action_setup.cfg_sudo_action_setup_model import CfgSudoActionSetupModel
from app.modules.security.models.cfg_sudo_action_access.cfg_sudo_action_access_model import CfgSudoActionAccessModel
from app.modules.security.models.cfg_ops_log_setup.cfg_ops_log_setup_model import CfgOpsLogSetupModel
from app.modules.security.models.ops_organization_log.ops_organization_log_model import OpsOrganizationLogModel
from app.modules.security.models.cfg_rls_access.cfg_rls_access_model import CfgRlsAccessModel
from app.modules.security.models.cfg_storage.cfg_storage_model import CfgStorageModel
from app.modules.core.models.cfg_system_town_entity.cfg_system_town_entity_model import CfgSystemTownEntityModel

# --- Senat-Digit feature modules (§3.5) ---
from app.modules.session_meeting.models.session_meeting.session_meeting_model import SessionMeetingModel
from app.modules.session_meeting.models.session_participant.session_participant_model import SessionParticipantModel
from app.modules.agenda.models.agenda_item.agenda_item_model import AgendaItemModel
from app.modules.document.models.document_meta.document_meta_model import DocumentMetaModel
from app.modules.document.models.document_version.document_version_model import DocumentVersionModel
from app.modules.document.models.document_amendment.document_amendment_model import DocumentAmendmentModel
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.models.vote_ballot.vote_ballot_model import VoteBallotModel
from app.modules.vote.models.vote_proxy.vote_proxy_model import VoteProxyModel
from app.modules.vote.models.vote_result.vote_result_model import VoteResultModel
from app.modules.presence.models.presence_signature.presence_signature_model import PresenceSignatureModel
from app.modules.parole.models.parole_request.parole_request_model import ParoleRequestModel
from app.modules.audit_security.models.audit_event.audit_event_model import AuditEventModel
from app.modules.core.models.cfg_current_entity.cfg_current_entity_model import CfgCurrentEntityModel
 

# Schema modules for array_of_object_model lookup
SCHEMA_MODULES = [
    "app.modules.core.schemas.core_schema",
    "app.modules.auth.schemas.auth_schema",
    # Add more schema modules as needed
]

COLLECTIONS = [
    # Tuple format: (CollectionKey, collection_name, Model, is_exposed, verbose, can_watch_update_history, can_watch_delete_history)
    (CollectionKey.REF_MFAS, RefMfaModel.Settings.name, RefMfaModel, True, "Authentification multi-facteurs", False, False),
    (CollectionKey.CFG_USER_MFA, CfgUserMfaModel.Settings.name, CfgUserMfaModel, True, "Configuration MFA des utilisateurs", False, False),
    (CollectionKey.CFG_USER_DEVICE, CfgUserDeviceModel.Settings.name, CfgUserDeviceModel, True, "Appareils des utilisateurs", False, False),
    (CollectionKey.CFG_USER_PIN, CfgUserPinModel.Settings.name, CfgUserPinModel, False, "PIN utilisateur", False, False),
    (CollectionKey.CFG_USER_APP_STORE, CfgUserAppStoreModel.Settings.name, CfgUserAppStoreModel, False, "Cache des applications par utilisateur", False, False),
    (CollectionKey.OPS_USER_LOGIN_HISTORY, OpsUserLoginHistoryModel.Settings.name, OpsUserLoginHistoryModel, True, "Historique de connexion des utilisateurs", False, False),
    (CollectionKey.CFG_ENTITY_CURRENCY, CfgCountryCurrencyModel.Settings.name, CfgCountryCurrencyModel, True, "Devises des entités", False, False),
    (CollectionKey.CFG_CURRENT_ENTITY, CfgCurrentEntityModel.Settings.name, CfgCurrentEntityModel, True, "Entités actuelles"),
    (CollectionKey.REF_NAMED_ENTITY, RefNamedEntityModel.Settings.name, RefNamedEntityModel, True, "Entités nommées", False, False),
    (CollectionKey.REF_ENTITY, RefEntityModel.Settings.name, RefEntityModel, True, "Entités", True, True),
    (CollectionKey.REF_APPLICATION_GROUP, RefApplicationGroupModel.Settings.name, RefApplicationGroupModel, True, "Groupes d'applications", False, False),
    (CollectionKey.REF_CURRENCY, RefCurrencyModel.Settings.name, RefCurrencyModel, True, "Devises", False, False),
    (CollectionKey.CFG_CURRENCY_EXCHANGE, CfgCurrencyExchangeModel.Settings.name, CfgCurrencyExchangeModel, True, "Taux de change", False, False),
    (CollectionKey.SAAS_VERSION, SaasVersionModel.Settings.name, SaasVersionModel, True, "Versions SaaS", False, False),
    (CollectionKey.CFG_SYSTEM_ORGANIZATION, CfgSystemOrganizationModel.Settings.name, CfgSystemOrganizationModel, True, "Organisations", False, False),
   
    (CollectionKey.ARCH_FOLDER, ArchFolderModel.Settings.name, ArchFolderModel, True, "Dossiers d'archives", False, False),
    (CollectionKey.ARCH_FILE, ArchFileModel.Settings.name, ArchFileModel, True, "Fichiers d'archives", False, False),
    (CollectionKey.RBAC_PROFILE, RbacProfileModel.Settings.name, RbacProfileModel, True, "Profils système", False, False),
    (CollectionKey.RBAC_ROLE, RbacRoleModel.Settings.name, RbacRoleModel, True, "Rôles RBAC", False, False),
    (CollectionKey.SYS_ORGANIZATION, SysOrganizationModel.Settings.name, SysOrganizationModel, True, "Organisations", False, False),
    (CollectionKey.SYS_ORGANIZATION_AGENT, SysOrganizationAgentModel.Settings.name, SysOrganizationAgentModel, True, "Agents d'organisation", False, False),
    (CollectionKey.SYS_USER, SysUserModel.Settings.name, SysUserModel, True, "Utilisateurs", True, True),
    (CollectionKey.SYS_MENU, SysMenuModel.Settings.name, SysMenuModel, True, "Menus", False, False),
    (CollectionKey.SYS_APPLICATION, SysApplicationModel.Settings.name, SysApplicationModel, True, "Applications", False, False),
    (CollectionKey.CFG_USER_PROFILE_ROLE, CfgUserProfilRoleModel.Settings.name, CfgUserProfilRoleModel, True, "Rôles des profils utilisateurs", False, False),
    (CollectionKey.CFG_USER_CONFIG, CfgUserConfigModel.Settings.name, CfgUserConfigModel, True, "Configuration des utilisateurs", False, False),

    (CollectionKey.CFG_USER_QUESTION_RESPONSE, CfgUserQuestionResponseModel.Settings.name, CfgUserQuestionResponseModel, True, "Réponses aux questions des utilisateurs", False, False),
    (CollectionKey.REF_AUTH_QUESTION_CATEGORY, RefAuthQuestionCategoryModel.Settings.name, RefAuthQuestionCategoryModel, True, "Catégories de questions d'authentification", False, False),
    (CollectionKey.REF_AUTH_QUESTION, RefAuthQuestionModel.Settings.name, RefAuthQuestionModel, True, "Questions d'authentification", False, False),
    # CFG_USER_AUTH_SETUP
    (CollectionKey.CFG_USER_AUTH_SETUP, CfgUserAuthSetupModel.Settings.name, CfgUserAuthSetupModel, True, "Configuration d'authentification des utilisateurs", False, False),
    

    (CollectionKey.REF_LANGUAGE, RefLanguageModel.Settings.name, RefLanguageModel, True, "Langues", False, False),
    (CollectionKey.CFG_ICON_API_CONSUMER, CfgIconApiConsumerModel.Settings.name, CfgIconApiConsumerModel, True, "Consommateurs d'API d'icônes", False, False),
    (CollectionKey.REF_THEME, RefThemeModel.Settings.name, RefThemeModel, True, "Thèmes", False, False),
    (CollectionKey.REF_PERSON_TYPE, RefPersonTypeModel.Settings.name, RefPersonTypeModel, True, "Types de personnes", False, False),
    (CollectionKey.SYS_PERSON, SysPersonModel.Settings.name, SysPersonModel, True, "Personnes", False, False),
    (CollectionKey.REF_DATA_TO_COLLECT_TYPE, RefDataToCollectTypesModel.Settings.name, RefDataToCollectTypesModel, True, "Types de données à collecter", False, False),
    (CollectionKey.RBAC_ENDPOINT, RbacEndpointModel.Settings.name, RbacEndpointModel, True, "Points de terminaison RBAC", False, False),
    (CollectionKey.RBAC_PRIVILEGE, RbacPrivilegeModel.Settings.name, RbacPrivilegeModel, True, "Privilèges RBAC", False, False),
    (CollectionKey.RBAC_PERMISSION_ROLE, RbacPermissionRoleModel.Settings.name, RbacPermissionRoleModel, True, "Rôles de permission RBAC", False, False),
    (CollectionKey.RBAC_PERMISSION, RbacPermissionModel.Settings.name, RbacPermissionModel, True, "Permissions RBAC", False, False),
    (CollectionKey.CFG_DUE_DOCUMENT, CfgDueDocumentModel.Settings.name, CfgDueDocumentModel, True, "Documents dus", False, False),
    (CollectionKey.REF_DOCUMENT, RefDocumentModel.Settings.name, RefDocumentModel, True, "Documents", False, False),
    (CollectionKey.CFG_REQUIRED_DOCUMENT, CfgRequiredDocumentModel.Settings.name, CfgRequiredDocumentModel, True, "Documents requis", False, False),
    (CollectionKey.REF_API_CONSUMER, RefApiConsumerModel.Settings.name, RefApiConsumerModel, True, "Consommateurs d'API", False, False),
    (CollectionKey.OPS_CONTACT_US, OpsContactUsModel.Settings.name, OpsContactUsModel, True, "Nous contacter", False, False),
    (CollectionKey.REF_FIELD_OF_STUDY, RefFieldOfStudyModel.Settings.name, RefFieldOfStudyModel, True, "Domaines d'étude", False, False),
    (CollectionKey.REF_SCHOOL_LEVEL, RefSchoolLevelModel.Settings.name, RefSchoolLevelModel, True, "Domaines d'étude", False, False),
    (CollectionKey.REF_MARITAL_STATUS, RefMaritalStatusModel.Settings.name, RefMaritalStatusModel, True, "États matrimoniaux", False, False),
    (CollectionKey.REF_COLOR, RefColorModel.Settings.name, RefColorModel, True, "Couleurs", False, False),
    (CollectionKey.REF_BLOOD_TYPE, RefBloodTypeModel.Settings.name, RefBloodTypeModel, True, "Groupes sanguins", False, False),
    (CollectionKey.REF_ICON, RefIconModel.Settings.name, RefIconModel, True, "Icônes", False, False),
    (CollectionKey.NTF_NOTIFICATION, NtfNotificationModel.Settings.name, NtfNotificationModel, True, "Notifications", False, False),

    # Senat-Digit feature modules (§3.5)
    (CollectionKey.SESSION_MEETING, SessionMeetingModel.Settings.name, SessionMeetingModel, True, "Séances", False, False),
    (CollectionKey.SESSION_PARTICIPANT, SessionParticipantModel.Settings.name, SessionParticipantModel, True, "Participants à une séance", False, False),
    (CollectionKey.AGENDA_ITEM, AgendaItemModel.Settings.name, AgendaItemModel, True, "Points d'ordre du jour", False, False),
    (CollectionKey.DOCUMENT_META, DocumentMetaModel.Settings.name, DocumentMetaModel, True, "Documents (méta)", False, False),
    (CollectionKey.DOCUMENT_VERSION, DocumentVersionModel.Settings.name, DocumentVersionModel, True, "Versions de documents", False, False),
    (CollectionKey.DOCUMENT_AMENDMENT, DocumentAmendmentModel.Settings.name, DocumentAmendmentModel, True, "Amendements", False, False),
    (CollectionKey.VOTE_CONFIG, VoteConfigModel.Settings.name, VoteConfigModel, True, "Scrutins (configurations)", False, False),
    (CollectionKey.VOTE_BALLOT, VoteBallotModel.Settings.name, VoteBallotModel, True, "Bulletins de vote", False, False),
    (CollectionKey.VOTE_PROXY, VoteProxyModel.Settings.name, VoteProxyModel, True, "Pouvoirs / procurations", False, False),
    (CollectionKey.VOTE_RESULT, VoteResultModel.Settings.name, VoteResultModel, True, "Résultats de scrutin", False, False),
    (CollectionKey.PRESENCE_SIGNATURE, PresenceSignatureModel.Settings.name, PresenceSignatureModel, True, "Signatures de présence", False, False),
    (CollectionKey.PAROLE_REQUEST, ParoleRequestModel.Settings.name, ParoleRequestModel, True, "Demandes de parole", False, False),
    (CollectionKey.AUDIT_EVENT, AuditEventModel.Settings.name, AuditEventModel, True, "Événements d'audit (chaîne)", False, False),
    (CollectionKey.CFG_FISCAL_YEAR, CfgFiscalYearModel.Settings.name, CfgFiscalYearModel, True, "Années fiscales", False, False),
    (CollectionKey.RBAC_ACTION, RbacActionModel.Settings.name, RbacActionModel, True, "Actions RBAC", False, False),
    (CollectionKey.REF_BUDGET_YEAR, RefBudgetYearModel.Settings.name, RefBudgetYearModel, True, "Années budgétaires", False, False),

    (CollectionKey.RBAC_TITLE, RbacTitleModel.Settings.name, RbacTitleModel, True, "Titres RBAC", False, False),
    (CollectionKey.RBAC_PATH_GUARD, RbacPathGuardModel.Settings.name, RbacPathGuardModel, True, "Gardes de chemin RBAC", False, False),
    (CollectionKey.RBAC_PERMISSION_TARGET, RbacPermissionTargetModel.Settings.name, RbacPermissionTargetModel, True, "Cibles de permission RBAC", False, False),
    (CollectionKey.REF_COUNTRY, RefCountryModel.Settings.name, RefCountryModel, True, "Pays", False, False),

    (CollectionKey.CFG_GRADE, CfgGradeModel.Settings.name, CfgGradeModel, True, "Grades", False, False),
    (CollectionKey.CFG_FUNCTION, CfgFunctionModel.Settings.name, CfgFunctionModel, True, "Fonctions", False, False),
    (CollectionKey.REF_BANK, RefBankModel.Settings.name, RefBankModel, True, "Banques", False, False),
    (CollectionKey.REF_BENEFICIARY, RefBeneficiaryModel.Settings.name, RefBeneficiaryModel, True, "Bénéficiaires", False, False),
    (CollectionKey.CFG_BANK, CfgBankModel.Settings.name, CfgBankModel, True, "Configuration des banques", False, False),
    (CollectionKey.CFG_BANK_ACCOUNT_NUMBER, CfgBankAccountNumberModel.Settings.name, CfgBankAccountNumberModel, True, "Numéros de compte bancaire", False, False),

    (CollectionKey.CFG_ORGANISM_CHART, CfgOrganismChartModel.Settings.name, CfgOrganismChartModel, True, "Organigrammes", False, False),
    (CollectionKey.REF_RELIGION, RefReligionModel.Settings.name, RefReligionModel, True, "Religions", False, False),
    (CollectionKey.REF_EYE_COLOR, RefEyeColorModel.Settings.name, RefEyeColorModel, True, "Couleurs des yeux", False, False),

    (CollectionKey.RBAC_RESTRICTED_API_CONSUMER, RbacRestrictedApiConsumerModel.Settings.name, RbacRestrictedApiConsumerModel, True, "Consommateurs d'API restreints", False, False),
    (CollectionKey.REF_BANK_TYPE, RefBankTypeModel.Settings.name, RefBankTypeModel, True, "Types de banques", False, False),
    (CollectionKey.RBAC_RESTRICTED_PROFIL, RbacRestrictedProfilModel.Settings.name, RbacRestrictedProfilModel, True, "Profils restreints", False, False),
    (CollectionKey.REF_COLLECTION, RefCollectionModel.Settings.name, RefCollectionModel, True, "Collections", False, False),
    (CollectionKey.REF_COLLECTION_CRUD_INFO, RefCollectionCrudInfoModel.Settings.name, RefCollectionCrudInfoModel, True, "Informations CRUD des collections", False, False),
    
    (CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE, RefDocumentTemplateTypeModel.Settings.name, RefDocumentTemplateTypeModel, True, "Types de modèles de documents", False, False),
    
    (CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE, RefDocumentTemplatePageModel.Settings.name, RefDocumentTemplatePageModel, True, "Pages de modèles de documents", False, False),
    (CollectionKey.REF_DOCUMENT_TEMPLATE, RefDocumentTemplateModel.Settings.name, RefDocumentTemplateModel, True, "Modèles de documents", False, False),
    (CollectionKey.RBAC_COMPONENT, RbacComponentModel.Settings.name, RbacComponentModel, True, "Composants RBAC", False, False),
    

    (CollectionKey.CFG_DATA_DISPLAY_TYPE, CfgDataDisplayTypeModel.Settings.name, CfgDataDisplayTypeModel, True, "Types d'affichage des données", False, False),
    (CollectionKey.CFG_CHILDREN_DISPLAY_TYPE, CfgChildrenDisplayTypeModel.Settings.name, CfgChildrenDisplayTypeModel, True, "Types d'affichage des données", False, False),
    (CollectionKey.REF_CHILDREN_DISPLAY_TYPE, RefChildrenDisplayTypeModel.Settings.name, RefChildrenDisplayTypeModel, True, "Types d'affichage des données", False, False),
    (CollectionKey.REF_DATA_DISPLAY_TYPE, RefDataDisplayTypeModel.Settings.name, RefDataDisplayTypeModel, True, "Types d'affichage des données", False, False),

    # SECURITY
    (CollectionKey.CFG_SUDO_ACTION_ACCESS, CfgSudoActionAccessModel.Settings.name, CfgSudoActionAccessModel, True, "Accès aux actions sudo", False, False),
    (CollectionKey.CFG_RLS_ACCESS, CfgRlsAccessModel.Settings.name, CfgRlsAccessModel, True, "Accès aux actions sudo", False, False),
    # (CollectionKey.CFG_RLS_GLOBAL_ACCESS, CfgRlsGlobalAccessModel.Settings.name, CfgRlsGlobalAccessModel, True, "Sécurité au niveau des lignes", False, False),
    # (CollectionKey.CFG_RLS_ROW_ACCESS, CfgRowAccessModel.Settings.name, CfgRowAccessModel, True, "Sécurité au niveau des lignes", False, False),
    (CollectionKey.REF_SUDO_RLS_SECURITY_GROUP, RefSudoRlsSecurityGroupModel.Settings.name, RefSudoRlsSecurityGroupModel, True, "Groupes de sécurité", False, False),
    (CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER, RefSudoRlsSecurityGroupUserModel.Settings.name, RefSudoRlsSecurityGroupUserModel, True, "Utilisateurs de groupes de sécurité", False, False),
    (CollectionKey.CFG_USER_TOTP, CfgUserTotpModel.Settings.name, CfgUserTotpModel, True, "Configuration TOTP des utilisateurs", False, False),
    (CollectionKey.CFG_SUDO_ACTION_SETUP, CfgSudoActionSetupModel.Settings.name, CfgSudoActionSetupModel, True, "Configuration des actions sudo", False, False),
    (CollectionKey.CFG_RLS_SETUP, CfgRlsSetupModel.Settings.name, CfgRlsSetupModel, True, "Configuration de la sécurité au niveau des lignes", False, False),
    (CollectionKey.CFG_ORGANIZATION_RLS, CfgOrganizationRlsModel.Settings.name, CfgOrganizationRlsModel, True, "Sécurité au niveau des lignes par organisation", False, False),
    (CollectionKey.CFG_ORGANIZATION_SUDO_ACTION, CfgOrganizationSudoActionModel.Settings.name, CfgOrganizationSudoActionModel, True, "Organisations", False, False),
    (CollectionKey.CFG_USER_SIGNATURE, CfgUserSignatureModel.Settings.name, CfgUserSignatureModel, True, "Signatures des utilisateurs", False, False),
    (CollectionKey.OPS_VALIDATION_REQUEST, OpsValidationRequestModel.Settings.name, OpsValidationRequestModel, True, "Demandes de validation", False, False),
    (CollectionKey.OPS_VALIDATION_REQUEST_USER, OpsValidationRequestUserModel.Settings.name, OpsValidationRequestUserModel, True, "Utilisateurs validateurs des demandes", False, False),
    (CollectionKey.SYS_CROSS_VALIDATION_ORGANIZATION, SysCrossValidationOrganizationModel.Settings.name, SysCrossValidationOrganizationModel, True, "Organisations", False, False),
    (CollectionKey.RBAC_SUDO_ACTION, RbacSudoActionModel.Settings.name, RbacSudoActionModel, True, "Actions sudo RBAC", False, False),
    (CollectionKey.RBAC_SUDO_ACTION_ORGANIZATION, RbacSudoActionOrganizationModel.Settings.name, RbacSudoActionOrganizationModel, True, "Actions sudo RBAC par organisation", False, False),
    (CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE, RbacSudoActionConfirmationTypeModel.Settings.name, RbacSudoActionConfirmationTypeModel, True, "Types de confirmation d'actions sudo RBAC", False, False),
    (CollectionKey.RBAC_USER_VALIDATOR, RbacUserValidatorModel.Settings.name, RbacUserValidatorModel, True, "Validateurs d'utilisateurs RBAC", False, False),

    (CollectionKey.DISTRIBUTED_LOCKS, OpsDistributedLockModel.Settings.name, OpsDistributedLockModel, True, "Bénéficiaire interne", False, False),
    (CollectionKey.CFG_SAAS_CONFIG, CfgSaasConfigModel.Settings.name, CfgSaasConfigModel, True, "Configuration SaaS", False, False),
    (CollectionKey.CFG_ENTITY_AVAILABILITY, CfgEntityAvailabilityModel.Settings.name, CfgEntityAvailabilityModel, True, "Configuration des disponibilités par entités", False, False),

    (CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY, OpsUserLoginDailyActivityModel.Settings.name, OpsUserLoginDailyActivityModel, True, "Les activités journalières d'un utilisateur", False, False),

    # CfgApplicationGroupAccessibilityModel
    (CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY, CfgApplicationGroupAccessibilityModel.Settings.name, CfgApplicationGroupAccessibilityModel, True, "Accessibilité des groupes d'applications", False, False),
    (CollectionKey.REF_TELEPHONE_NETWORK, RefTelephoneNetworkModel.Settings.name, RefTelephoneNetworkModel, True, "Réseaux téléphoniques", False, False),
    (CollectionKey.CFG_TELEPHONE_NETWORK_RELATED_COUNTRY, CfgTelephoneNetworkRelatedCountryModel.Settings.name, CfgTelephoneNetworkRelatedCountryModel, True, "Réseaux téléphoniques par pays", False, False),
    (CollectionKey.CFG_COUNTRY_RELATED_APP_GROUP, CfgCountryRelatedApplicationGroupModel.Settings.name, CfgCountryRelatedApplicationGroupModel, True, "Groupes d'applications par pays", False, False),
 
    (CollectionKey.CFG_SYSTEM_COUNTRY, CfgSystemCountryModel.Settings.name, CfgSystemCountryModel, True, "Pays du système", False, False),
    (CollectionKey.CFG_SYSTEM_TOWN_ENTITY, CfgSystemTownEntityModel.Settings.name, CfgSystemTownEntityModel, True, "Villes des entités"),
    (CollectionKey.CFG_FCM_CONFIG, CfgFcmConfigModel.Settings.name, CfgFcmConfigModel, True, "FCM Configuration", False, False),

    (CollectionKey.CFG_COUNTRY_RELATED_CURRENCY, CfgCountryRelatedCurrencyModel.Settings.name, CfgCountryRelatedCurrencyModel, True, "Devises liées aux pays", False, False),
    (CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX, CfgCountryRelatedPhonePrefixModel.Settings.name, CfgCountryRelatedPhonePrefixModel, True, "Prefixes téléphoniques liés aux pays", False, False),
    (CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX, CfgCountryRelatedWalletPrefixModel.Settings.name, CfgCountryRelatedWalletPrefixModel, True, "Prefixes de portefeuille liés aux pays", False, False),

    (CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE, CfgCountryRelatedCountryCodeModel.Settings.name, CfgCountryRelatedCountryCodeModel, True, "Codes pays liés aux pays", False, False),
     
    (CollectionKey.CFG_BANK_RELATED_COUNTRY, CfgBankRelatedCountryModel.Settings.name, CfgBankRelatedCountryModel, True, "Banques liées aux pays", False, False),
    
    (CollectionKey.REF_NOTIFICATION_CHANNEL, RefNotificationChannelModel.Settings.name, RefNotificationChannelModel, True, "Canaux de notification", False, False),
    (CollectionKey.REF_NOTIFICATION_TUNNEL, RefNotificationTunnelModel.Settings.name, RefNotificationTunnelModel, True, "Tunnels de notification", False, False),
    (CollectionKey.CFG_NOTIFICATION_CONFIG, CfgNotificationConfigModel.Settings.name, CfgNotificationConfigModel, True, "Configuration des notifications", False, False),
    (CollectionKey.CFG_RELATED_SYSTEM_PROFIL, CfgRelatedSystemProfilModel.Settings.name, CfgRelatedSystemProfilModel, True, "Profils système liés", False, False),
    (CollectionKey.CFG_DEFAULT_RELATED_CURRENCY, CfgDefaultRelatedCurrencyModel.Settings.name, CfgDefaultRelatedCurrencyModel, True, "Devises par défaut liées aux entités", False, False),

    # Organization CRUD Logs
    (CollectionKey.CFG_OPS_LOG_SETUP, CfgOpsLogSetupModel.Settings.name, CfgOpsLogSetupModel, True, "Configuration des logs d'organisation", False, False),
    (CollectionKey.OPS_ORGANIZATION_LOG, OpsOrganizationLogModel.Settings.name, OpsOrganizationLogModel, True, "Logs d'organisation CRUD", False, False),

    # F10: per-organization KMS + storage configuration. Resolves the master
    # key VoteCryptoService uses to seal per-resolution DEKs.
    (CollectionKey.CFG_STORAGE, CfgStorageModel.Settings.name, CfgStorageModel, True, "Configuration KMS / stockage par organisation", False, False),

    # Ops History (audit trail) — these collections should NOT record their own history
    (CollectionKey.OPS_UPDATE_HISTORY, OpsUpdateHistoryModel.Settings.name, OpsUpdateHistoryModel, True, "Historique des mises à jour", False, False),
    (CollectionKey.OPS_DELETE_HISTORY, OpsDeleteHistoryModel.Settings.name, OpsDeleteHistoryModel, True, "Historique des suppressions", False, False),

]


### **`COLLECTION_MODEL_MAPPING` Construction:**

def _is_tenant_scoped(model_class) -> bool:
    """
    A collection is tenant-scoped for RLS purposes if its model declares a
    `sys_organization_id` field. Global ref/system tables (countries, currencies,
    RBAC roles, etc.) do not declare this field and are exempt from RLS scoping.
    """
    try:
        return "sys_organization_id" in getattr(model_class, "model_fields", {})
    except Exception:
        return False


COLLECTION_MODEL_MAPPING: Dict[CollectionKey, ModelMetadata] = {
    key: ModelMetadata(
        key=key,
        collection_name=collection_name,
        model_class=model,
        is_exposed=exposed,
        verbose=rest[0] if rest else f"Collection {collection_name}",
        can_watch_update_history=rest[1] if len(rest) > 1 else False,
        can_watch_delete_history=rest[2] if len(rest) > 2 else False,
        is_tenant_scoped=_is_tenant_scoped(model),
    )
    for key, collection_name, model, exposed, *rest in COLLECTIONS
}
