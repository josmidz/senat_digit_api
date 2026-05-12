# app/core/config.py
from pydantic_settings import BaseSettings
import os

# Normalize ENV value so we pick the right .env file even when shorthand is used
ENV_ALIAS_MAP = {
    "dev": "development",
    "development": "development",
    "prod": "production",
    "production": "production",
    "local": "local",
    "stage": "staging",
    "staging": "staging",
    "test": "test",
    "testing": "test",
}
ENV_VALUE = os.getenv("ENV", "development")
NORMALIZED_ENV = ENV_ALIAS_MAP.get(ENV_VALUE, ENV_VALUE)

class Settings(BaseSettings):
    # Configuration de base
    ENV: str = "development"
    APP_PORT: int = 8088
    EXPOSE: str = ""  # Added EXPOSE field
    NGINX: str = ""  # Added EXPOSE field
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    LOG_LEVEL: str = ""
    REDIS_DB: int = 0

    TOTP_ISSUER: str = "MinFinance"

    # ── HMAC consumer validation ─────────────────────────────────────────
    # When True, ConsumerValidationMiddleware rejects every request that
    # doesn't carry a valid X-Api-Signature (HMAC over the request).
    # Default False so local dev + CI can still use the bare-flag path.
    # MUST be True in dev/stage/prod — wire via .env.<env>.
    STRICT_CONSUMER_VALIDATION: bool = False

    # Maximum clock skew tolerated between client and server, in seconds.
    # Anti-replay: requests older than this are rejected. 300s (5 min)
    # matches AWS SigV4 — generous enough to absorb device NTP drift +
    # network latency, tight enough that captured-and-replayed requests
    # die quickly. Phase 2 nonce dedup tightens further; tighten this
    # window to 60s once mobile NTP is reliably <±10s.
    CONSUMER_SIGNATURE_MAX_SKEW_SECONDS: int = 300


    # Configuration Gunicorn
    GUNICORN_PORT: int = 9382
    GUNICORN_WORKERS: int = 4
    GUNICORN_TIMEOUT: int = 120
    GUNICORN_KEEPALIVE: int = 5
    GUNICORN_MAX_REQUESTS: int = 1000
    GUNICORN_MAX_REQUESTS_JITTER: int = 50

    # Configuration MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = ""

    # Configuration Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "redis"
    REDIS_URL_ALT:str = ""

    # Configuration de sécurité
    SECRET_KEY: str = "a3f4b0e36a8c5982cb702861386a49db86f5bec5b1c5fde69a7700d1c445f523"
    RECAPTCHA_SECRET: str = "I3290SD3923"
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str = "f6db43ccc7171c3fecdc7ee382179115a4a3a35f3f2b83b74835d7ff34597d4a"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 60 * 24 * 7
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = "http://localhost:4000"
    RATE_LIMIT: str = "100/minute"
    RATE_LIMIT_STORAGE_URL: str = "redis://localhost:6379/2"

    # Configuration du chiffrement
    ENCRYPTION_KEY: str = ''
    ENCRYPTION_SECRET_KEY: str = ''
    ENCRYPTION_DB_SECRET_KEY: str = ''  # Dedicated key for database encryption
    CURRENT_KEY_VERSION: str = 'v1'
    GATEWAY_ENCRYPTION_SECRET_KEY: str = 'CWX22q4kLtru43o3_brxja21_fW22pM6nALmkmsd7Rc'
    # python3 -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip('='))"
    AUTH_APP_PAIRING_SECRET_KEY: str = ''  # AES-256-CBC key for mobile app pairing (base64-encoded 32 bytes)

    # Configuration de la base de données
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Configuration du cache
    CACHE_TYPE: str = "redis"
    CACHE_REDIS_URL: str = "redis://localhost:6379/1"
    CACHE_DEFAULT_TIMEOUT: int = 1800

    # Configuration du fuseau horaire (Timezone)
    # Par défaut: Europe/Paris (UTC+1 en hiver, UTC+2 en été)
    DEFAULT_TIMEZONE: str = "Africa/Kinshasa"

    # Configuration des logs
    LOG_LEVEL: str = "info"
    LOG_FILE: str = "/var/log/senat_digit_api.log"
    ERROR_LOG_FILE: str = "/var/log/senat_digit_api.error.log"
    ACCESS_LOG_FILE: str = "/var/log/senat_digit_api.access.log"

    # Configuration SSL/TLS
    SSL_CERT_PATH: str = "/path/to/cert.pem"
    SSL_KEY_PATH: str = "/path/to/key.pem"

    # Configuration du monitoring
    SENTRY_DSN: str = ""
    PROMETHEUS_METRICS_PORT: int = 9090

    # Redis L1 TTL for the /data/get-applications cache. Was 1800s (30min)
    # back when L1 was the only invalidation mechanism. Now that the L2
    # user_app_store layer + the explicit cache-sweep hooks (RBAC permission
    # changes, SysUser save events) all flush L1 keys directly, the TTL is
    # mostly a defensive ceiling rather than the primary correctness lever.
    # Shortened to 5 minutes so any rare missed-invalidation never lasts long.
    CACHE_DEFAULT_APPLICATION_TIMEOUT: int = 300

    # URLs des services
    FRONT_END_ANGULAR_BASE_URL: str = ""
    SENAT_DIGIT_APPS_FILE_SYSTEM_URL: str = ""
    SENAT_DIGIT_APPS_FILE_BEARER_TOKEN: str = ""

    # Audit chain verification cron (F7). Cadence at which the background
    # job walks every org's audit chain + writes a snapshot to
    # OpsOrganizationLogModel. Default 15 minutes; clamped to [60, 86400].
    AUDIT_CHAIN_VERIFY_INTERVAL_SECONDS: int = 900
    SENAT_DIGIT_APPS_FILE_ORGANIZATION_LOGO_BASE_DIR: str = ""
    SENAT_DIGIT_APPS_FILE_ORGANIZATION_USER_SIGNATURE_BASE_DIR: str = ""
    SENAT_DIGIT_APPS_FILE_ADVERTISEMENT_BASE_DIR: str = "advertisements"
    SENAT_DIGIT_APPS_ICONS_SYSTEM_BASE_DIR: str = "senat_digit_apps_icons"
    MAIN_APP_BASE_URL: str = ""

    

    # Configuration SMTP
    SMTP_PORT: int = 587
    SMTP_SECURE: bool = False
    SMTP_HOST: str = ""
    SMTP_AUTH_USER: str = ""
    SMTP_AUTH_PASS: str = ""
    SMTP_FROM_NAME: str = "SenatDigit Support"
    SMTP_FROM_EMAIL: str = ""

    # Configuration SMS
    SMS_SENDER_ID: str = ""
    SMS_POST_URL: str = ""
    SMS_TOKEN: str = ""
    SMS_API_KEY: str = ""
    SMS_API_SECRET: str = ""
    SMS_FROM_NUMBER: str = ""
    ONE_MESSAGE_COUNT_CHARACTERS: int = 160

    # HTTP Basic Auth (webhook callbacks)
    BASIC_USERNAME: str = "webhook"
    BASIC_PASSWORD: str = ""

    # Configuration des administrateurs 
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_PHONE_NUMBER: str = ""
    ADMIN_LAST_NAME: str = ""
    ADMIN_GENDER: str = ""
    ADMIN_FRIST_NAME: str = ""

    TESTER_ADMIN_USERNAME: str = ""
    TESTER_ADMIN_PASSWORD: str = ""
    TESTER_ADMIN_EMAIL: str = ""
    TESTER_ADMIN_PHONE_NUMBER: str = ""
    TESTER_ADMIN_LAST_NAME: str = ""
    TESTER_ADMIN_GENDER: str = ""
    TESTER_ADMIN_FIRST_NAME: str = ""
    ADMIN_FIRST_NAME: str = ""


    LISOLOO_API_KEY: str = ""
    LISOLOO_API_URL : str = ""

    # Configuration Emess SMS (emess.cd)
    EMESS_APP_ID: str = ""
    EMESS_SECRET_KEY: str = ""
    EMESS_API_URL: str = "https://emess.cd"

    SENAT_DIGIT_SMS_SENDER_ID: str = "SenatDigit"

    # Easypay mobile money collections
    EASYPAY_API_KEY: str = ""
    EASYPAY_BASE_URL: str = "https://www.easypay-gateway.com/payments/api/v1"
    EASYPAY_TIMEOUT_SECONDS: float = 30.0
    EASYPAY_TOKEN_CACHE_SECONDS: int = 3300
    EASYPAY_USE_REDIS_TOKEN_CACHE: bool = True
    EASYPAY_MAX_RETRIES: int = 1
  
    # DEFAULT : app menus are fetched and submenus are fetched in a second request.
    # COMPACT : app menus are fetched and submenus are fetched in one request.
    APP_MENU_FETCH_PARADIGM: str = "default" # default | compact

    class Config:
        # Dynamiquement déterminer le fichier .env à utiliser
        env_file = f".env.{NORMALIZED_ENV}"  # Par défaut .env.development
        extra = "ignore"  # Ignore extra fields not defined in the model

settings = Settings()
