
from dataclasses import  dataclass
from enum import Enum
from typing import Any, Dict, Optional,Type

class MessageCategory(Enum):
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"
    REGISTRATION = "registration"
    COMMON = "common"
    MULTI_VALIDATION = "multi_validation"
    EXCEPTIONS = "inner_exceptions"
    EXIST_EXCEPTIONS = "exist_exceptions"
    NOT_FOUND = "exceptions"
    ERRORS = "errors"
    MISSING = "missing"
    EMAIL_TEMPLATE = "email_template"
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"



class EIconFlag(Enum):
    STANDARD_SVG = "standard_svg"
    REACT_SVG = "react_svg"
    IMAGE = "image"
    REACT_MATERIAL_ICON = "react_material_icon"
    ANGULAR_MATERIAL_ICON = "react_material_icon"


class ERbacActionFlag(Enum):
    TABLE_ACTION_ADD = "table_action_add"
    TABLE_ACTION_ADD_CHILD = "table_action_add_child"
    TABLE_ACTION_UPDATE = "table_action_update"
    TABLE_ACTION_DELETE = "table_action_delete"
    TABLE_ACTION_VIEW = "table_action_view"
    STANDALONE_ACTION = "standalone_action"
    COMMON_LOCK_ACTION = "common_action_lock_flag"
    COMMON_UNLOCK_ACTION = "common_action_unlock_flag"
    COMMON_DOWNLOAD_ACTION = "common_action_download_flag"
    COMMON_UPLOAD_ACTION_FILE = "common_action_upload_file_flag"

class ERbacActionHardCodeFlag(Enum):
    CREATION_ACTION = "creation_action_flag"
    DELETION_ACTION = "table_action_delete_flag"
    UPDATE_ACTION = "table_action_update_flag"
    VIEW_ACTION = "view_action_flag"
    LOCK_ACTION = "lock_action_flag"
    UNLOCK_ACTION = "unlock_action_flag"
    DOWNLOAD_ACTION = "download_action_flag"
    UPLOAD_ACTION = "upload_action_flag"

class ERbacComponentFlag(Enum):
    DATA_LIST_COMPONENT = "data_list_component"
    OWN_INFO_COMPONENT = "own_info_component"
    STANDARD_COMPONENT = "standard_component"
    CUSTOM_COMPONENT = "custom_component"


# class ERbacHardCodeActionFlag(Enum):
#     HARD_CODED_ACTION_ADD = "hard_coded_creation_action_flag"
#     HARD_CODED_ACTION_ADD_CHILD = "hard_coded_action_add_child_flag"
#     HARD_CODED_ACTION_UPDATE = "hard_coded_action_update_flag"
#     HARD_CODED_ACTION_DELETE = "hard_coded_action_delete_flag"
#     HARD_CODED_ACTION_VIEW = "hard_coded_action_view_flag"
#     HARD_CODED_STANDALONE_ACTION = "hard_coded_action_standalone_flag"



class EMenuAppDisplayFlag(Enum):
    HARD_CODED = "hard_coded"
    AUTO_GENERATED = "auto_generated"


class EDistributedLockStatusFlag(Enum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


@dataclass
class ModelMetadata:
    collection_name: str
    model_class: Type
    is_exposed: bool
    key: Optional[str]
    verbose: Optional[str] = None
    can_watch_update_history: bool = False
    can_watch_delete_history: bool = False
    # RLS: True when the model carries a `sys_organization_id` field (i.e. its rows
    # are tenant-scoped). Auto-derived at mapping construction time — do not set manually.
    is_tenant_scoped: bool = False

class FieldTranslation:
    def __init__(self,
                 property_name: str,
                 data_type: Any,
                 property_value: Optional[Any] = None,
                 extra_metas: Dict[str, bool] = {},
                 may_have_translation: bool = False,
                 to_be_translated_in_front: bool = False):

        self.may_have_translation = may_have_translation
        self.property_name = property_name
        self.property_value = property_value
        self.data_type = data_type
        self.extra_metas = extra_metas
        self.to_be_translated_in_front = to_be_translated_in_front

