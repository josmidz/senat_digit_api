import multiprocessing
import os
from pathlib import Path
from dotenv import load_dotenv

# Environment detection
ENV = os.getenv("ENV", "development").lower()
BASE_DIR = Path(__file__).parent.parent  # Points to project root

# Load environment-specific .env file
env_file = BASE_DIR / f".env.{ENV}"
if env_file.exists():
    load_dotenv(env_file, override=True)

# Server configuration
bind = f"0.0.0.0:{os.getenv('APP_PORT', '5516' if ENV == 'development' else '9000')}"

# Worker configuration
workers = int(os.getenv(
    "GUNICORN_WORKERS",
    multiprocessing.cpu_count() * (2 if ENV == "development" else 2)
))
# AsyncioUvicornWorker forces asyncio loop to avoid uvloop/anyio BaseHTTPMiddleware crash
worker_class = "worker.AsyncioUvicornWorker"
threads = int(os.getenv("GUNICORN_THREADS", "1"))

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120" if ENV == "development" else "30"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Requests
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Logging
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "debug" if ENV == "development" else "info")
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")

# Security
proxy_allow_ips = os.getenv("GUNICORN_PROXY_ALLOW_IPS", "*")
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")

# Environment-specific
reload = ENV == "development"
preload_app = ENV == "production" or ENV == "development"
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", "/tmp")
# worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", "/dev/shm")