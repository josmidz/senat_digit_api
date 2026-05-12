"""
Error Logger Helper

A comprehensive error logging utility that saves formatted errors to log files
with proper structure, rotation, and different log levels.
"""

import os
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Union
from enum import Enum
import logging
from logging.handlers import RotatingFileHandler

from app.modules.core.utils.helpers.line_helper import LineHelper


class LogLevel(Enum):
    """Log levels for error categorization"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorLogger:
    """
    Enhanced error logger that saves errors to structured log files
    with rotation, formatting, and different output formats.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the error logger
        
        Args:
            base_dir: Base directory for logs. Defaults to cwd()/ERRORS
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / "ERRORS"
        self.base_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        (self.base_dir / "application").mkdir(exist_ok=True)
        (self.base_dir / "validation").mkdir(exist_ok=True)
        (self.base_dir / "system").mkdir(exist_ok=True)
        (self.base_dir / "api").mkdir(exist_ok=True)
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Setup rotating file handlers for different log categories"""
        self.loggers = {}
        
        categories = ["application", "validation", "system", "api"]
        
        for category in categories:
            logger = logging.getLogger(f"senat_digit_{category}")
            logger.setLevel(logging.DEBUG)
            
            # Clear existing handlers
            logger.handlers.clear()
            
            # Create rotating file handler (10MB max, keep 5 backups)
            log_file = self.base_dir / category / f"{category}.log"
            handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
            logger.propagate = False  # Prevent duplicate logs
            
            self.loggers[category] = logger
    
    def log_error(
        self,
        message: str,
        exception: Optional[Exception] = None,
        level: LogLevel = LogLevel.ERROR,
        category: str = "application",
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        save_json: bool = True
    ) -> str:
        """
        Log an error with comprehensive information
        
        Args:
            message: Error message
            exception: Exception object (if any)
            level: Log level
            category: Log category (application, validation, system, api)
            context: Additional context data
            user_id: User ID associated with the error
            request_id: Request ID for tracing
            save_json: Whether to also save as JSON format
            
        Returns:
            Path to the log file created
        """
        timestamp = datetime.now(timezone.utc)
        
        # Get caller information
        caller_info = LineHelper.get_caller_info(depth=1)
        
        # Build error data structure
        error_data = {
            "timestamp": timestamp.isoformat(),
            "level": level.value,
            "category": category,
            "message": message,
            "caller": {
                "file": caller_info["filename"],
                "function": caller_info["function_name"],
                "line": caller_info["line_no"],
                "full_path": caller_info["full_path"]
            },
            "user_id": user_id,
            "request_id": request_id,
            "context": context or {}
        }
        
        # Add exception information if provided
        if exception:
            exc_info = LineHelper.get_exception_line_info(exception)
            error_data["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "location": {
                    "file": exc_info["filename"],
                    "function": exc_info["function_name"],
                    "line": exc_info["line_no"],
                    "full_path": exc_info["full_path"]
                },
                "traceback": traceback.format_exc() if exception.__traceback__ else None
            }
        
        # Format message for standard logging
        log_message = self._format_log_message(error_data)
        
        # Log to appropriate logger
        logger = self.loggers.get(category, self.loggers["application"])
        log_method = getattr(logger, level.value.lower(), logger.error)
        log_method(log_message)
        
        # Save as JSON if requested
        if save_json:
            self._save_json_log(error_data, category)
        
        return str(self.base_dir / category / f"{category}.log")
    
    def _format_log_message(self, error_data: Dict[str, Any]) -> str:
        """Format error data for standard log output"""
        parts = []
        
        # Basic info
        parts.append(f"[{error_data['caller']['file']}:{error_data['caller']['function']}:{error_data['caller']['line']}]")
        parts.append(error_data["message"])
        
        # User and request info
        if error_data.get("user_id"):
            parts.append(f"User: {error_data['user_id']}")
        
        if error_data.get("request_id"):
            parts.append(f"Request: {error_data['request_id']}")
        
        # Exception info
        if error_data.get("exception"):
            exc = error_data["exception"]
            parts.append(f"Exception: {exc['type']}: {exc['message']}")
            parts.append(f"at [{exc['location']['file']}:{exc['location']['function']}:{exc['location']['line']}]")
        
        # Context
        if error_data.get("context"):
            context_str = json.dumps(error_data["context"], default=str)
            parts.append(f"Context: {context_str}")
        
        return " | ".join(parts)
    
    def _save_json_log(self, error_data: Dict[str, Any], category: str):
        """Save error data as JSON for structured analysis"""
        json_dir = self.base_dir / category / "json"
        json_dir.mkdir(exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        json_file = json_dir / f"error_{timestamp}.json"
        
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            # Fallback logging if JSON save fails
            print(f"Failed to save JSON log: {e}")
    
    def log_validation_error(
        self,
        field_name: str,
        field_value: Any,
        error_message: str,
        model_name: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Log validation errors with specific context
        
        Args:
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            error_message: Validation error message
            model_name: Name of the Pydantic model
            user_id: User ID
            request_id: Request ID
            
        Returns:
            Path to the log file
        """
        context = {
            "field_name": field_name,
            "field_value": str(field_value)[:500],  # Limit value length
            "model_name": model_name
        }
        
        message = f"Validation failed for field '{field_name}': {error_message}"
        
        return self.log_error(
            message=message,
            level=LogLevel.WARNING,
            category="validation",
            context=context,
            user_id=user_id,
            request_id=request_id
        )
    
    def log_api_error(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        error_message: str,
        exception: Optional[Exception] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log API-specific errors
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            error_message: Error message
            exception: Exception object
            user_id: User ID
            request_id: Request ID
            request_data: Request data (will be truncated if too large)
            
        Returns:
            Path to the log file
        """
        context = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "request_data": str(request_data)[:1000] if request_data else None  # Limit size
        }
        
        message = f"API Error [{method} {endpoint}] {status_code}: {error_message}"
        
        level = LogLevel.ERROR if status_code >= 500 else LogLevel.WARNING
        
        return self.log_error(
            message=message,
            exception=exception,
            level=level,
            category="api",
            context=context,
            user_id=user_id,
            request_id=request_id
        )


# Global instance for easy access
error_logger = ErrorLogger()


# Convenience functions
def log_error(message: str, exception: Optional[Exception] = None, **kwargs) -> str:
    """Convenience function to log errors"""
    return error_logger.log_error(message, exception, **kwargs)


def log_validation_error(field_name: str, field_value: Any, error_message: str, **kwargs) -> str:
    """Convenience function to log validation errors"""
    return error_logger.log_validation_error(field_name, field_value, error_message, **kwargs)


def log_api_error(endpoint: str, method: str, status_code: int, error_message: str, **kwargs) -> str:
    """Convenience function to log API errors"""
    return error_logger.log_api_error(endpoint, method, status_code, error_message, **kwargs)
