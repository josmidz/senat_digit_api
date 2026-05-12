
import enum
 
class MFaFlag(str, enum.Enum):
  EMAIL="email"
  PHONE_NUMBER = "phone_number"
  COMMON_2FA_APP = "common_2fa_app"
  SYCAMORE_2FA_APP = "sycamore_2fa_app"
  QUESTION_RESPONSE = "question_response"
  PASS_CODE = "pass_code"
  PIN = "pin"


class EMfaPurpose(str, enum.Enum):
  LOGIN_ONLY = "login_only"
  LOGIN_AND_RESET_PASSWORD = "login_and_reset_password"
  RESET_PASSWORD_ONLY = "reset_password_only"
  LOCKED_SCREEN_ONLY = "locked_screen_only"
  LOGIN_AND_LOCKED_SCREEN = "login_and_locked_screen"
  LOCKED_SCREEN_AND_RESET_PASSWORD = "locked_screen_and_reset_password"
  LOCKED_SCREEN_AND_LOGIN = "locked_screen_and_login"
  ALL = "all"
