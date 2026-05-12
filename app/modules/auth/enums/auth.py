
import enum

class ELoginStatus(str, enum.Enum):
    NONE  = "none"
    LOGGED_IN  = "logged_in"
    LOGGED_OUT = "logged_out"
    INIT_LOGIN = "init_login"
    INIT_PASSWORD_PROCESS = "init_password_process"
    RESET_PASSWORD_PROCESS_VALIDATED = "reset_password_process_validated"
    RESET_PASSWORD_PROCESS_COMPLETED = "reset_password_process_completed"
    
