# app/modules/core/utils/helpers/line_helper_examples.py

"""
Examples of how to use the LineHelper utility
"""

from app.modules.core.utils.helpers.line_helper import (
    LineHelper,
    line_debug,
    line_info,
    line_number,
    line_location,
    line_error,
    exception_line_info,
    format_exception
)


def example_basic_usage():
    """Basic usage examples"""
    
    # Method 1: Using the class directly
    message = LineHelper.format_line_info("This is a debug message")
    print(message)  # Output: [line_helper_examples.py:example_basic_usage:18] This is a debug message
    
    # Method 2: Using convenience functions
    line_debug("Quick debug message")  # Prints: [line_helper_examples.py:example_basic_usage:21] Quick debug message
    
    # Method 3: Get just the line number
    current_line = line_number()
    print(f"Current line: {current_line}")  # Output: Current line: 24
    
    # Method 4: Get location string
    location = line_location()
    print(f"Location: {location}")  # Output: Location: line_helper_examples.py:example_basic_usage:27


def example_error_handling():
    """Error handling examples"""

    try:
        # Some code that might fail
        result = 10 / 0
    except Exception as e:
        # Log error with line information
        error_msg = line_error("Division by zero occurred", e)
        print(error_msg)
        # Output: [line_helper_examples.py:example_error_handling:36] ERROR: Division by zero occurred | Exception: ZeroDivisionError: division by zero


def example_exception_line_tracking():
    """Examples of tracking where exceptions are thrown"""

    def problematic_function():
        """Function that will throw an exception"""
        x = 10
        y = 0
        return x / y  # This line will throw ZeroDivisionError

    def another_problematic_function():
        """Another function that throws an exception"""
        data = {"key": "value"}
        return data["missing_key"]  # This line will throw KeyError

    # Example 1: Basic exception line info
    try:
        problematic_function()
    except Exception as e:
        exc_location = exception_line_info(e)
        print(f"Exception occurred at: {exc_location}")
        # Output: Exception occurred at: line_helper_examples.py:problematic_function:52

    # Example 2: Detailed exception formatting
    try:
        another_problematic_function()
    except Exception as e:
        detailed_msg = format_exception("Key access failed", e)
        print(detailed_msg)
        # Output: [line_helper_examples.py:example_exception_line_tracking:62] Key access failed | Exception raised at [line_helper_examples.py:another_problematic_function:56] | KeyError: 'missing_key'

    # Example 3: Exception with full traceback
    try:
        problematic_function()
    except Exception as e:
        detailed_with_trace = format_exception("Critical error", e, include_traceback=True)
        print(detailed_with_trace)

    # Example 4: Get full traceback info as structured data
    try:
        problematic_function()
    except Exception as e:
        traceback_info = LineHelper.get_full_traceback_info(e)
        print("Full traceback info:")
        for i, frame in enumerate(traceback_info):
            print(f"  Frame {i}: {frame['filename']}:{frame['function_name']}:{frame['line_no']}")


def example_nested_exception_tracking():
    """Example with nested function calls to show full traceback"""

    def level_1():
        return level_2()

    def level_2():
        return level_3()

    def level_3():
        # This will throw an exception
        return int("not_a_number")

    try:
        level_1()
    except Exception as e:
        # Show where exception was caught vs where it was thrown
        print("=== Nested Exception Example ===")
        print(f"Caught at: {line_location()}")
        print(f"Exception thrown at: {exception_line_info(e)}")

        # Show full call stack
        traceback_info = LineHelper.get_full_traceback_info(e)
        print("Full call stack:")
        for i, frame in enumerate(traceback_info):
            print(f"  {i+1}. {frame['filename']}:{frame['function_name']}:{frame['line_no']}")


def example_real_world_usage():
    """Real-world usage examples for your codebase"""

    def simulate_database_error():
        """Simulate a database connection error"""
        raise ConnectionError("Database connection failed")

    def simulate_validation_error():
        """Simulate a validation error"""
        raise ValueError("Invalid input data")

    # Example 1: HTTP Exception with line info (like in your country_controller.py)
    try:
        simulate_database_error()
    except Exception as e:
        # Instead of just: message = f"line {current_line} : {message}"
        # Use this for much better info:
        error_msg = format_exception("Database operation failed", e)
        print(f"HTTPException detail: {error_msg}")
        # This gives you both where you're handling the error AND where it was thrown

    # Example 2: Logging with exception context
    try:
        simulate_validation_error()
    except Exception as e:
        # Get structured info for logging
        exc_info = LineHelper.get_exception_line_info(e)
        log_message = f"Validation failed at {exc_info['filename']}:{exc_info['line_no']} in {exc_info['function_name']}() - {str(e)}"
        print(f"Log entry: {log_message}")

    # Example 3: Debug service integration
    try:
        simulate_database_error()
    except Exception as e:
        # Enhanced debug print with exception context
        debug_msg = format_exception("Service error occurred", e)
        # DebugService.app_debug_print(debug_msg, True)  # Your existing debug service
        print(f"Debug: {debug_msg}")


def example_custom_formatting():
    """Custom formatting examples"""
    
    # Include only filename and line (no function name)
    msg1 = LineHelper.format_line_info("Message 1", include_function=False)
    print(msg1)  # Output: [line_helper_examples.py:44] Message 1
    
    # Include only line number
    msg2 = LineHelper.format_line_info("Message 2", include_file=False, include_function=False)
    print(msg2)  # Output: [47] Message 2
    
    # Get just line number
    line_num = LineHelper.get_line_only()
    custom_message = f"Custom format - Line {line_num}: Important info"
    print(custom_message)  # Output: Custom format - Line 51: Important info


def example_call_stack():
    """Call stack tracing example"""
    
    def level_3():
        # Show call stack from here
        stack = LineHelper.trace_call_stack(max_depth=5)
        print(stack)
    
    def level_2():
        level_3()
    
    def level_1():
        level_2()
    
    level_1()
    # Output:
    # Call Stack:
    #   1: line_helper_examples.py:level_3:58
    #   2: line_helper_examples.py:level_2:61
    #   3: line_helper_examples.py:level_1:64
    #   4: line_helper_examples.py:example_call_stack:66


def example_integration_with_debug_service():
    """Example of integrating with existing DebugService"""
    
    # Replace your current approach:
    # current_line = inspect.currentframe().f_lineno
    # message = f"line {current_line} : {message}"
    
    # With this:
    original_message = "Processing user data"
    enhanced_message = line_info(original_message)
    print(enhanced_message)
    
    # Or for DebugService integration:
    def enhanced_debug_print(message: str, show_details: bool = True):
        if show_details:
            # This will show the line where enhanced_debug_print was called
            formatted_message = LineHelper.format_line_info(message, depth=1)
        else:
            formatted_message = message
        
        # Your existing DebugService logic here
        print(f"DEBUG: {formatted_message}")
    
    # Usage:
    enhanced_debug_print("User authentication successful")
    # Output: DEBUG: [line_helper_examples.py:example_integration_with_debug_service:89] User authentication successful


if __name__ == "__main__":
    print("=== LineHelper Examples ===\n")

    print("1. Basic Usage:")
    example_basic_usage()

    print("\n2. Error Handling:")
    example_error_handling()

    print("\n3. Exception Line Tracking:")
    example_exception_line_tracking()

    print("\n4. Nested Exception Tracking:")
    example_nested_exception_tracking()

    print("\n5. Real-World Usage:")
    example_real_world_usage()

    print("\n6. Custom Formatting:")
    example_custom_formatting()

    print("\n7. Call Stack:")
    example_call_stack()

    print("\n8. Integration Example:")
    example_integration_with_debug_service()
