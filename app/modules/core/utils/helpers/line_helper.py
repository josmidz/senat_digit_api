# app/modules/core/utils/helpers/line_helper.py

import inspect
import traceback
from typing import Optional, Dict, Any
from pathlib import Path


class LineHelper:
    """
    Efficient line helper utility for debugging and logging with accurate line numbers
    """
    
    @staticmethod
    def get_caller_info(depth: int = 1) -> Dict[str, Any]:
        """
        Get caller information at specified depth
        
        Args:
            depth: How many levels up the call stack to look
                  1 = immediate caller (default)
                  2 = caller's caller, etc.
        
        Returns:
            Dict with line_no, filename, function_name, full_path
        """
        try:
            frame = inspect.currentframe()
            # Go up the specified depth in the call stack
            for _ in range(depth + 1):  # +1 to skip this function itself
                frame = frame.f_back
                if frame is None:
                    break
            
            if frame is None:
                return {
                    'line_no': 0,
                    'filename': 'unknown',
                    'function_name': 'unknown',
                    'full_path': 'unknown'
                }
            
            full_path = frame.f_code.co_filename
            filename = Path(full_path).name
            function_name = frame.f_code.co_name
            line_no = frame.f_lineno
            
            return {
                'line_no': line_no,
                'filename': filename,
                'function_name': function_name,
                'full_path': full_path
            }
        except Exception:
            return {
                'line_no': 0,
                'filename': 'error',
                'function_name': 'error',
                'full_path': 'error'
            }
    
    @staticmethod
    def format_line_info(message: str, include_file: bool = True, include_function: bool = True, depth: int = 1) -> str:
        """
        Format message with line information
        
        Args:
            message: The message to format
            include_file: Whether to include filename
            include_function: Whether to include function name
            depth: Call stack depth (1 = immediate caller)
        
        Returns:
            Formatted message with line info
        """
        info = LineHelper.get_caller_info(depth)
        
        parts = []
        if include_file:
            parts.append(info['filename'])
        if include_function:
            parts.append(info['function_name'])
        parts.append(str(info['line_no']))
        
        location = ':'.join(parts)
        return f"[{location}] {message}"
    
    @staticmethod
    def debug_print(message: str, include_file: bool = True, include_function: bool = True) -> str:
        """
        Print debug message with line information
        
        Args:
            message: Debug message
            include_file: Include filename in output
            include_function: Include function name in output
        
        Returns:
            Formatted message (also prints it)
        """
        formatted = LineHelper.format_line_info(message, include_file, include_function, depth=1)
        print(formatted)
        return formatted
    
    @staticmethod
    def get_line_only() -> int:
        """
        Get just the line number of the caller
        
        Returns:
            Line number where this function was called
        """
        info = LineHelper.get_caller_info(depth=1)
        return info['line_no']
    
    @staticmethod
    def get_location_string(include_file: bool = True, include_function: bool = True) -> str:
        """
        Get location string of the caller
        
        Args:
            include_file: Include filename
            include_function: Include function name
        
        Returns:
            Location string like "file.py:function:123" or just "123"
        """
        info = LineHelper.get_caller_info(depth=1)
        
        parts = []
        if include_file:
            parts.append(info['filename'])
        if include_function:
            parts.append(info['function_name'])
        parts.append(str(info['line_no']))
        
        return ':'.join(parts)
    
    @staticmethod
    def trace_call_stack(max_depth: int = 5) -> str:
        """
        Get a formatted call stack trace
        
        Args:
            max_depth: Maximum depth to trace
        
        Returns:
            Formatted call stack string
        """
        stack_info = []
        
        for depth in range(1, max_depth + 1):
            info = LineHelper.get_caller_info(depth)
            if info['line_no'] == 0:  # No more frames
                break
            
            stack_info.append(f"  {depth}: {info['filename']}:{info['function_name']}:{info['line_no']}")
        
        return "Call Stack:\n" + "\n".join(stack_info)
    
    @staticmethod
    def error_with_line(message: str, exception: Optional[Exception] = None) -> str:
        """
        Format error message with line information and optional exception

        Args:
            message: Error message
            exception: Optional exception object

        Returns:
            Formatted error message
        """
        formatted = LineHelper.format_line_info(f"ERROR: {message}", depth=1)

        if exception:
            formatted += f" | Exception: {type(exception).__name__}: {str(exception)}"

        return formatted

    @staticmethod
    def get_exception_line_info(exception: Exception) -> Dict[str, Any]:
        """
        Get line information where an exception was raised

        Args:
            exception: Exception object

        Returns:
            Dict with exception line info
        """
        try:
            tb = exception.__traceback__
            if tb is None:
                return {
                    'line_no': 0,
                    'filename': 'unknown',
                    'function_name': 'unknown',
                    'full_path': 'unknown'
                }

            # Get the last frame in the traceback (where exception was raised)
            while tb.tb_next is not None:
                tb = tb.tb_next

            frame = tb.tb_frame
            full_path = frame.f_code.co_filename
            filename = Path(full_path).name
            function_name = frame.f_code.co_name
            line_no = tb.tb_lineno

            return {
                'line_no': line_no,
                'filename': filename,
                'function_name': function_name,
                'full_path': full_path
            }
        except Exception:
            return {
                'line_no': 0,
                'filename': 'error',
                'function_name': 'error',
                'full_path': 'error'
            }

    @staticmethod
    def format_exception_with_line(message: str, exception: Exception, include_traceback: bool = False) -> str:
        """
        Format exception message with line information where exception was raised

        Args:
            message: Custom message
            exception: Exception object
            include_traceback: Whether to include full traceback

        Returns:
            Formatted exception message with line info
        """
        # Get current caller info
        caller_info = LineHelper.get_caller_info(depth=1)

        # Get exception line info
        exc_info = LineHelper.get_exception_line_info(exception)

        # Format the message
        formatted = f"[{caller_info['filename']}:{caller_info['function_name']}:{caller_info['line_no']}] {message}"
        formatted += f" | Exception raised at [{exc_info['filename']}:{exc_info['function_name']}:{exc_info['line_no']}]"
        formatted += f" | {type(exception).__name__}: {str(exception)}"

        if include_traceback:
            formatted += f"\nTraceback: {traceback.format_exc()}"

        return formatted

    @staticmethod
    def get_full_traceback_info(exception: Exception) -> list:
        """
        Get full traceback information as a list of dictionaries

        Args:
            exception: Exception object

        Returns:
            List of traceback frame info
        """
        try:
            tb_info = []
            tb = exception.__traceback__

            while tb is not None:
                frame = tb.tb_frame
                full_path = frame.f_code.co_filename
                filename = Path(full_path).name
                function_name = frame.f_code.co_name
                line_no = tb.tb_lineno

                tb_info.append({
                    'line_no': line_no,
                    'filename': filename,
                    'function_name': function_name,
                    'full_path': full_path
                })

                tb = tb.tb_next

            return tb_info
        except Exception:
            return []


# Convenience functions for common use cases
def line_debug(message: str) -> str:
    """Quick debug with line info"""
    return LineHelper.debug_print(message)

def line_info(message: str) -> str:
    """Get formatted message with line info (doesn't print)"""
    return LineHelper.format_line_info(message, depth=1)

def line_number() -> int:
    """Get just the current line number"""
    return LineHelper.get_line_only()

def line_location() -> str:
    """Get current location string"""
    return LineHelper.get_location_string()

def line_error(message: str, exception: Optional[Exception] = None) -> str:
    """Format error with line info"""
    return LineHelper.error_with_line(message, exception)

def exception_line_info(exception: Exception) -> str:
    """Get formatted string with exception line info"""
    info = LineHelper.get_exception_line_info(exception)
    return f"{info['filename']}:{info['function_name']}:{info['line_no']}"

def format_exception(message: str, exception: Exception, include_traceback: bool = False) -> str:
    """Format exception with both caller and exception line info"""
    return LineHelper.format_exception_with_line(message, exception, include_traceback)
