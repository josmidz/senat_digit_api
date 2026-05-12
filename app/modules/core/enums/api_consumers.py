from enum import Enum


class EApiConsumerFlag(str, Enum):
    """API consumer flags for Senat-Digit.

    Three first-party consumers:
      - SENAT_DIGIT_MOBILE     : Flutter app for sénateurs
      - SENAT_DIGIT_ADMIN_WEB  : Angular admin (greffier / admin IT / archiviste)
      - SENAT_DIGIT_FS         : Server-to-server (senat_digit_fs_api → senat_digit_api)

    Plus utility consumers (Postman, MFA-validation app).
    """
    SENAT_DIGIT_MOBILE = "senat_digit_mobile",
    SENAT_DIGIT_ADMIN_WEB = "senat_digit_admin_web",
    SENAT_DIGIT_FS = "senat_digit_fs",
    CLIENT_POSTMAN = "client_postman",
    FLUTTER_VALIDATION_AND_TOTP_MFA_APPS = "flutter_validation_and_totp_mfa_apps",



