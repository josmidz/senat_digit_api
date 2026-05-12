from enum import Enum
import enum

class ValidatorDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EConfigSudoActionTypeFlag(str,enum.Enum):
    IS_SUDO_ACTION = "is_sudo_action"
    IS_SUDO_DELEGATED_ACTION = "is_sudo_delegated_action"

    IS_SUDO_GROUP_ACTION = "is_sudo_group_action"
    IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION = "is_sudo_group_cross_organization_validation_action"

    IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION = "is_sudo_group_inter_connected_organization_validation_action"

    NONE = "none"

class ESudoActionAccessTargetedTypeFlag(str,enum.Enum):
    USER = "user"
    SUDO_RLS_SECURITY_GROUP = "sudo_rls_security_group"
    CROSS_ORGANIZATION = "cross_organization"
    INTER_CONNECTED_ORGANIZATION = "inter_connected_organization"

class ESudoActionAccessTypeFlag(str,enum.Enum):
    GLOBAL_ACCESS = "global_access"
    GROUPED_ACCESS = "grouped_access"
    DELEGATED_ACCESS = "delegated_access"
    GROUPED_CROSS_VALIDATION_ACCESS = "grouped_cross_validation_access"
    GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS = "grouped_inter_connected_organization_validation_access"
    NONE = "none"


class ERlsAccessTypeFlag(str,enum.Enum):
    GLOBAL_ACCESS = "global_access"
    REVOKED_ACCESS = "revoked_access"
    CUSTOM_ACCESS = "custom_access"
    NONE = "none"

