# app/main.py

#FAST API
from app.lifespan.manager import lifespan
from fastapi import FastAPI,Request,status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
import os

# ROUTES
from app.modules.core.api.endpoints.route_entry_point import route_entry_point

# MIDDLEWARES
from app.modules.core.middleware.request_logging_middleware import RequestLoggingMiddleware
from app.modules.core.services.debug.debug_service import DebugService

# Import SMS Scheduler registration function
from app.modules.core.services.sms.sms_service import SmsService

#SECURITY
security = HTTPBearer()

app = FastAPI(
    title="Senat-Digit API",
    description="Senat-Digit — Digitalization platform for parliamentary sessions (main API)",

    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)

# Register SMS scheduler cron jobs
# register_sms_scheduler_cron_job(app)

# List of allowed origins
origins = [
    "http://0.0.0.0:9204",  # Angular app in py local server
    "http://localhost:7316",  # Angular app in py local server
    "http://localhost:7316",  # Angular app
    "http://127.0.0.1:7316",  # Localhost variant
    "http://209.74.64.154:7020",  # Remove trailing slash here
    "http://209.74.64.154:4308",  # Remove trailing slash here
    "https://dev.senat_digit.digipublic.app",
    "https://www.dev.senat_digit.digipublic.app",
    "*",  # Allow all origins for WebSocket connections
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # allow any origin
    allow_credentials=False,        # <— no credentials
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
) 
app.add_middleware(RequestLoggingMiddleware)
# Custom exception handler for RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract the preferred language from the request headers
    accept_language = request.headers.get("accept-language", "en").split(",")[0].strip()
    from app.modules.core.services.translation.translation_service import TranslationService
    # Extract error messages and format them into a single line
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
        msg_key = error["type"]  # Get the error type (e.g., "string_too_short")
        ctx = error.get("ctx", {})  # Get additional context (e.g., "min_length")

        # Translate the error message
        translated_msg = TranslationService.get_field_error_translated_message(accept_language, msg_key, **ctx)
        error_messages.append(f"{field}: {translated_msg}")

    # Join all error messages into a single line
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(error_messages)},
    ) 



#ROUTES
@app.options("/{path:path}")
async def preflight():
    return {"message": "Preflight OK"}

# Serve static files from a directory named "static"
app.mount("/static", StaticFiles(directory="static"), name="static")

# Route to serve the favicon.ico file
@app.get("/favicon.ico")
async def get_favicon():
    return FileResponse("static/favicon.ico")

# ROUTES ENTRY POINT 
app.mount("/api/v1", route_entry_point)

DebugService.app_debug_print(f"Running in {os.environ['ENV']} environment",True)
