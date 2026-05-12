
import enum

class EAccessFlag(str, enum.Enum):
    READ = "read"
    WHITE = "whrite"
    UPDATE = "update"
    DELETE = "delete" 
    DOWNLOAD = "download"
    ADDED = "added"
    REMOVED = "removed"


class EUserInfoValidationFlag(str, enum.Enum):
    EMAIL="email"
    PHONE_NUMBER = "phone_number"