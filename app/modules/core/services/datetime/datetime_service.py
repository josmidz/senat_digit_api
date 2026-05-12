

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Union
from num2words import num2words
import locale
import time

from app.modules.core.models.field_translation_keys import (
    DAY_NAMES, 
    DEFAULT_LANGUAGE, 
    FIELD_ERROR_TRANSLATED, 
    MONTH_NAMES, 
    TERMS_ABR,
    DATE_FORMATS, 
    LANGUAGE_MAPPING, 
    LOCALE_MAPPING
)


class DatetimeService:
    """
    Service for date and time operations.
    Provides methods for formatting dates, parsing datetime strings,
    and supporting various locale-specific formats.
    """
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        
    def format_date(self, date_obj: Union[date, datetime], format_str: Optional[str] = None) -> str:
        """
        Format a date object according to the specified format string or locale-specific default.
        
        Args:
            date_obj: The date or datetime object to format
            format_str: Optional format string (if None, uses locale-specific default)
            
        Returns:
            Formatted date string
        """
        if format_str is None:
            # Default formats based on language
            formats = {
                "en": "%m/%d/%Y",  # US format: MM/DD/YYYY
                "fr": "%d/%m/%Y",  # French/European format: DD/MM/YYYY
                "ru": "%d.%m.%Y",  # Russian format: DD.MM.YYYY
            }
            format_str = formats.get(self.accept_language, "%Y-%m-%d")  # ISO format as fallback
        
        # Convert datetime to date if needed
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
            
        return date_obj.strftime(format_str)
    
    def format_datetime(self, dt: datetime, include_time: bool = True, include_seconds: bool = False) -> str:
        """
        Format a datetime object according to locale-specific format.
        
        Args:
            dt: The datetime object to format
            include_time: Whether to include time in the output
            include_seconds: Whether to include seconds in the time
            
        Returns:
            Formatted datetime string
        """
        date_formats = {
            "en": "%m/%d/%Y",  # US format
            "fr": "%d/%m/%Y",  # French/European format
            "ru": "%d.%m.%Y",  # Russian format
        }
        
        time_formats = {
            "with_seconds": " %H:%M:%S",
            "without_seconds": " %H:%M"
        }
        
        date_format = date_formats.get(self.accept_language, "%Y-%m-%d")
        
        if include_time:
            time_format = time_formats["with_seconds" if include_seconds else "without_seconds"]
            return dt.strftime(f"{date_format}{time_format}")
        else:
            return dt.strftime(date_format)
    
    def parse_date(self, date_str: str) -> date:
        """
        Parse a date string into a date object, supporting multiple formats.
        
        Args:
            date_str: The date string to parse
            
        Returns:
            A date object
            
        Raises:
            ValueError: If the date string cannot be parsed
        """
        # Define supported date formats based on locale
        supported_formats = [
            "%Y-%m-%d",              # ISO 8601 date part
            "%d/%m/%Y",              # European format
            "%m/%d/%Y",              # US format
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with time and timezone (milliseconds)
            "%Y-%m-%dT%H:%M:%SZ",     # ISO 8601 with time and timezone (no milliseconds)
            "%Y-%m-%d %H:%M:%S",      # Custom format with time
            "%d-%m-%Y",              # European format with hyphens
            "%m-%d-%Y",              # US format with hyphens
            "%d.%m.%Y",              # Russian format
        ]
        
        # Try each format
        parsed_date = None
        for fmt in supported_formats:
            try:
                # Handle the 'Z' timezone explicitly
                if fmt.endswith("Z") and date_str.endswith("Z"):
                    # Remove the 'Z' and parse the datetime
                    date_str_without_z = date_str[:-1]
                    parsed_date = datetime.strptime(date_str_without_z, fmt[:-1]).date()
                else:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        
        # Try ISO format as a fallback
        if parsed_date is None:
            try:
                # Handle ISO 8601 format with timezone (Z) and milliseconds
                if "T" in date_str and "Z" in date_str:
                    # Replace 'Z' with '+00:00' to make it compatible with fromisoformat
                    date_str_iso = date_str.replace("Z", "+00:00")
                    parsed_date = datetime.fromisoformat(date_str_iso).date()
                else:
                    parsed_date = datetime.fromisoformat(date_str).date()
            except ValueError:
                error_key = "invalid_date_format"
                error_msg = FIELD_ERROR_TRANSLATED.get(self.accept_language, {}).get(
                    error_key, "Invalid date format. Expected format: YYYY-MM-DD"
                )
                raise ValueError(error_msg)
        
        return parsed_date
    
    def parse_datetime(self, datetime_str: str) -> datetime:
        """
        Parse a datetime string into a datetime object, supporting multiple formats.
        
        Args:
            datetime_str: The datetime string to parse
            
        Returns:
            A datetime object
            
        Raises:
            ValueError: If the datetime string cannot be parsed
        """
        # Define supported datetime formats
        supported_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with milliseconds
            "%Y-%m-%dT%H:%M:%SZ",     # ISO 8601 without milliseconds
            "%Y-%m-%d %H:%M:%S",      # Custom format
            "%Y-%m-%d %H:%M",         # Custom format without seconds
            "%d/%m/%Y %H:%M:%S",     # European format with time
            "%m/%d/%Y %H:%M:%S",     # US format with time
        ]
        
        # Try each format
        parsed_dt = None
        for fmt in supported_formats:
            try:
                # Handle the 'Z' timezone explicitly
                if fmt.endswith("Z") and datetime_str.endswith("Z"):
                    # Remove the 'Z' and parse the datetime
                    datetime_str_without_z = datetime_str[:-1]
                    parsed_dt = datetime.strptime(datetime_str_without_z, fmt[:-1])
                else:
                    parsed_dt = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue
        
        # Try ISO format as a fallback
        if parsed_dt is None:
            try:
                # Handle ISO 8601 format with timezone
                if "T" in datetime_str and "Z" in datetime_str:
                    # Replace 'Z' with '+00:00' to make it compatible with fromisoformat
                    datetime_str_iso = datetime_str.replace("Z", "+00:00")
                    parsed_dt = datetime.fromisoformat(datetime_str_iso)
                else:
                    parsed_dt = datetime.fromisoformat(datetime_str)
            except ValueError:
                error_key = "invalid_datetime_format"
                error_msg = FIELD_ERROR_TRANSLATED.get(self.accept_language, {}).get(
                    error_key, "Invalid datetime format"
                )
                raise ValueError(error_msg)
        
        return parsed_dt
    
    def get_date_components(self, date_obj: Union[date, datetime]) -> Dict[str, int]:
        """
        Extract components (year, month, day) from a date object.
        
        Args:
            date_obj: The date or datetime object
            
        Returns:
            Dictionary with year, month, and day components
        """
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
            
        return {
            "year": date_obj.year,
            "month": date_obj.month,
            "day": date_obj.day
        }
    
    def get_datetime_components(self, dt: datetime) -> Dict[str, int]:
        """
        Extract all components from a datetime object.
        
        Args:
            dt: The datetime object
            
        Returns:
            Dictionary with all datetime components
        """
        return {
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute,
            "second": dt.second,
            "microsecond": dt.microsecond
        }
    
    def calculate_age(self, birth_date: Union[date, datetime, str]) -> int:
        """
        Calculate age based on birth date.
        
        Args:
            birth_date: Birth date as date, datetime, or string
            
        Returns:
            Age in years
        """
        if isinstance(birth_date, str):
            birth_date = self.parse_date(birth_date)
        elif isinstance(birth_date, datetime):
            birth_date = birth_date.date()
            
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    def is_major(self, birth_date: Union[date, datetime, str], major_age: int = 18) -> bool:
        """
        Check if a person is of major age based on birth date.
        
        Args:
            birth_date: Birth date as date, datetime, or string
            major_age: Age threshold for majority (default: 18)
            
        Returns:
            True if the person is of major age, False otherwise
        """
        age = self.calculate_age(birth_date)
        return age >= major_age
    
    def get_date_difference(self, date1: Union[date, datetime, str], date2: Union[date, datetime, str]) -> Dict[str, int]:
        """
        Calculate the difference between two dates.
        
        Args:
            date1: First date (earlier)
            date2: Second date (later)
            
        Returns:
            Dictionary with difference in years, months, and days
        """
        # Parse strings if needed
        if isinstance(date1, str):
            date1 = self.parse_date(date1)
        if isinstance(date2, str):
            date2 = self.parse_date(date2)
            
        # Convert datetime to date if needed
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()
            
        # Ensure date2 is later than date1
        if date1 > date2:
            date1, date2 = date2, date1
            
        # Calculate difference
        delta = date2 - date1
        
        # Calculate years and months difference
        years = date2.year - date1.year
        months = date2.month - date1.month
        
        if date2.day < date1.day:
            months -= 1
            
        if months < 0:
            years -= 1
            months += 12
            
        return {
            "years": years,
            "months": months,
            "days": delta.days
        }
    
    def get_localized_month_name(self, month: Union[int, date, datetime]) -> str:
        """
        Get the localized month name based on the month number or date.
        
        Args:
            month: Month number (1-12) or date/datetime object
            
        Returns:
            Localized month name
        """
        # Extract month number if date or datetime is provided
        if isinstance(month, (date, datetime)):
            month = month.month
            
        # Validate month number
        if not 1 <= month <= 12:
            raise ValueError("Month must be between 1 and 12")
            
        # Month names by language 
        
        # Get month names for the current language or fallback to English
        names = MONTH_NAMES.get(self.accept_language, MONTH_NAMES[DEFAULT_LANGUAGE])
        return names[month - 1]  # Adjust for 0-based index
    
    def get_localized_day_name(self, day_of_week: Union[int, date, datetime]) -> str:
        """
        Get the localized day name based on the day of week number or date.
        
        Args:
            day_of_week: Day of week (0-6, where 0 is Monday) or date/datetime object
            
        Returns:
            Localized day name
        """
        # Extract day of week if date or datetime is provided
        if isinstance(day_of_week, (date, datetime)):
            # Convert to day of week where Monday is 0 and Sunday is 6
            day_of_week = day_of_week.weekday()
            
        # Validate day of week
        if not 0 <= day_of_week <= 6:
            raise ValueError("Day of week must be between 0 and 6")
            
        # Day names by language 
        
        # Get day names for the current language or fallback to English
        names = DAY_NAMES.get(self.accept_language, DAY_NAMES[DEFAULT_LANGUAGE])
        return names[day_of_week]  # Already 0-based index
    
    def format_relative_date(self, dt: Union[date, datetime]) -> str:
        """
        Format a date relative to today (e.g., "Today", "Yesterday", "Tomorrow").
        
        Args:
            dt: The date or datetime to format
            
        Returns:
            Localized relative date string or formatted date
        """
        # Convert datetime to date if needed
        if isinstance(dt, datetime):
            dt = dt.date()
            
        today = date.today()
        delta = (dt - today).days
        
        # Relative date terms by language 
        # Get terms for the current language or fallback to English
        lang_terms = TERMS_ABR.get(self.accept_language, TERMS_ABR[DEFAULT_LANGUAGE])
        
        if delta == 0:
            return lang_terms["today"]
        elif delta == -1:
            return lang_terms["yesterday"]
        elif delta == 1:
            return lang_terms["tomorrow"]
        else:
            return self.format_date(dt)
    
    def get_first_day_of_month(self, year: int, month: int) -> date:
        """
        Get the first day of a specific month.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Date object representing the first day of the month
        """
        return date(year, month, 1)
    
    def get_last_day_of_month(self, year: int, month: int) -> date:
        """
        Get the last day of a specific month.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Date object representing the last day of the month
        """
        # If month is December, the next month is January of the next year
        if month == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month + 1
            
        # The last day of the month is one day before the first day of the next month
        return date(next_month_year, next_month, 1) - timedelta(days=1)
    
    def add_time_to_date(self, dt: Union[date, datetime], 
                        years: int = 0, months: int = 0, days: int = 0,
                        hours: int = 0, minutes: int = 0, seconds: int = 0) -> Union[date, datetime]:
        """
        Add time units to a date or datetime.
        
        Args:
            dt: The date or datetime to modify
            years: Number of years to add
            months: Number of months to add
            days: Number of days to add
            hours: Number of hours to add (only for datetime)
            minutes: Number of minutes to add (only for datetime)
            seconds: Number of seconds to add (only for datetime)
            
        Returns:
            Modified date or datetime object
        """
        is_date_only = isinstance(dt, date) and not isinstance(dt, datetime)
        
        # Convert date to datetime if time units are provided
        if is_date_only and (hours != 0 or minutes != 0 or seconds != 0):
            dt = datetime.combine(dt, datetime.min.time())
            is_date_only = False
            
        # Add years and months (these require special handling)
        if years != 0 or months != 0:
            # Calculate target year and month
            year = dt.year + years
            month = dt.month + months
            
            # Adjust if month is out of range
            while month > 12:
                year += 1
                month -= 12
            while month < 1:
                year -= 1
                month += 12
                
            # Get the last day of the target month
            last_day = self.get_last_day_of_month(year, month).day
            
            # Ensure day is valid for the target month
            day = min(dt.day, last_day)
            
            # Create new date/datetime
            if isinstance(dt, datetime):
                dt = dt.replace(year=year, month=month, day=day)
            else:
                dt = date(year, month, day)
        
        # Add days, hours, minutes, seconds
        if days != 0 or hours != 0 or minutes != 0 or seconds != 0:
            delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            dt = dt + delta
            
        # Convert back to date if the input was a date
        if is_date_only and isinstance(dt, datetime):
            dt = dt.date()
            
        return dt
    
    
    @staticmethod
    def format_date_with_locale(locale_code=DEFAULT_LANGUAGE, date=None, add_time=False):
        """
        Format a date based on the provided locale.

        :param locale_code: Language code (e.g., "en", "fr", "ru"). Defaults to "fr".
        :param date: A datetime object to format. If None, uses the current date and time.
        :param add_time: If True, includes the time in the formatted output.
        :return: Formatted date or datetime as a string.
        """
        # Fallback to French if no locale is provided
        if locale_code is None:
            locale_code = DEFAULT_LANGUAGE

        # Get the full locale code from the mapping
        full_locale_code = LOCALE_MAPPING.get(locale_code, LOCALE_MAPPING[DEFAULT_LANGUAGE])  # Default to French

        try:
            # Set the locale
            locale.setlocale(locale.LC_TIME, full_locale_code)
        except locale.Error as e:
            return f"Locale '{full_locale_code}' is not supported: {e}"

        # Use the provided date or the current date and time
        if date is None:
            date = datetime.now()

        # Get the format based on the locale and add_time flag
        format_key = "datetime" if add_time else "date"
        date_format = DATE_FORMATS.get(locale_code, DATE_FORMATS[DEFAULT_LANGUAGE])[format_key]

        # Format the date or datetime
        formatted_output = date.strftime(date_format)

        return formatted_output

    def get_today_timestamp_int():
        timestamp = int(time.time())
        return timestamp

    def day_count_from_now(self,target_date, accept_language="en"):
        """
        Calculate the day count from now and return a human-readable string.

        Args:
            target_date (str or datetime): The target date in "YYYY-MM-DD" format or as a datetime object.
            accept_language (str): Language code (e.g., "en", "fr", "ru"). Defaults to "en".

        Returns:
            str: A human-readable string like "3 days", "one week and 2 days", "1 month, 2 weeks and 5 days".
        """

        # Fallback to English if the language is not supported
        if accept_language not in LANGUAGE_MAPPING:
            accept_language = "en"

        # Get the num2words language code
        language = LANGUAGE_MAPPING[accept_language]

        # Parse the target date if it's a string
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError:
                return "Invalid date format. Use 'YYYY-MM-DD'."

        # Get the current date and time
        now = datetime.now()

        # Calculate the difference between the target date and now
        delta = target_date - now

        # Handle past dates
        if delta.days < 0:
            return "The target date is in the past."

        # Calculate years, months, weeks, and days
        years = delta.days // 365
        remaining_days = delta.days % 365
        months = remaining_days // 30
        remaining_days %= 30
        weeks = remaining_days // 7
        days = remaining_days % 7

        # Build the human-readable string
        parts = []
        if years > 0:
            years_word = num2words(years, lang=language)
            parts.append(f"{years_word} year{'s' if years > 1 else ''}")
        if months > 0:
            months_word = num2words(months, lang=language)
            parts.append(f"{months_word} month{'s' if months > 1 else ''}")
        if weeks > 0:
            weeks_word = num2words(weeks, lang=language)
            parts.append(f"{weeks_word} week{'s' if weeks > 1 else ''}")
        if days > 0:
            days_word = num2words(days, lang=language)
            parts.append(f"{days_word} day{'s' if days > 1 else ''}")

        # Join the parts with commas and "and"
        if len(parts) == 0:
            return "0 days"
        elif len(parts) == 1:
            return parts[0]
        else:
            return ", ".join(parts[:-1]) + " and " + parts[-1]