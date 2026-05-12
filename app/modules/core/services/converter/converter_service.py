from datetime import datetime
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from num2words import num2words
from bson import ObjectId
from pydantic import BaseModel

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE, LANGUAGE_MAPPING
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.enums.type_enum import OutputFormat


class ConverterService:
    """
    Service for converting data between different formats.
    """
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
    
    
    @staticmethod
    def amount_to_letters(amount, accept_language=DEFAULT_LANGUAGE):
        """
        Convert an amount to words based on the provided language.

        :param amount: The amount to convert (float or int).
        :param accept_language: Language code (e.g., "en", "fr", "ru"). Defaults to "fr".
        :return: The amount in words as a string.
        """
    
        # Fallback to French if the language is not supported
        if accept_language not in LANGUAGE_MAPPING:
            accept_language = DEFAULT_LANGUAGE

        # Get the num2words language code
        language = LANGUAGE_MAPPING[accept_language]

        try:
            # Convert the amount to words
            amount_in_words = num2words(amount, lang=language)
            return amount_in_words
        except NotImplementedError:
            return f"Language '{accept_language}' is not supported by num2words."
        
    @staticmethod
    def convert_enums_to_values(data: Any) -> Any:
        """Convert enum values to their underlying values."""
        if isinstance(data, dict):
            return {k: ConverterService.convert_enums_to_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ConverterService.convert_enums_to_values(item) for item in data]
        elif isinstance(data, Enum):
            return data.value
        return data

    @staticmethod
    def convert_to_objectid(value: Any) -> Any:
        """Convert a value to ObjectId if possible."""
        from bson import ObjectId
        # Si la valeur est déjà un ObjectId, la retourner telle quelle
        if isinstance(value, ObjectId):
            return value
        # Si c'est une chaîne de caractères, essayer de la convertir
        if isinstance(value, str):
            try:
                return ObjectId(value)
            except:
                return value
        return value

    @staticmethod
    def track_saving_data_to_objectid(data: Any) -> Any:
        """
        Convert recursively all fields ending with '_id' to ObjectId.
        Works with nested dictionaries, lists, and other data structures.
        
        Args:
            data: The data to convert (dict, list, or any other type)
            
        Returns:
            The converted data with all '_id' fields as ObjectId
        """
        from bson import ObjectId
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key.endswith('_id'):
                    # Vérifier si la valeur est déjà un ObjectId
                    if isinstance(value, ObjectId):
                        result[key] = value
                    else:
                        result[key] = ConverterService.convert_to_objectid(value)
                else:
                    result[key] = ConverterService.track_saving_data_to_objectid(value)
            return result
        elif isinstance(data, list):
            return [ConverterService.track_saving_data_to_objectid(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(ConverterService.track_saving_data_to_objectid(item) for item in data)
        elif isinstance(data, set):
            return {ConverterService.track_saving_data_to_objectid(item) for item in data}
        return data

    @staticmethod
    def convert_query_params(query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert query parameters to appropriate types."""
        result = {}
        for key, value in query_params.items():
            if key.endswith('_id'):
                result[key] = ConverterService.convert_to_objectid(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def process_sort(sort):
        """
        Process the `sort` parameter to ensure it is a valid dictionary.
        If parsing fails, return a default sort dictionary.
        """
        if isinstance(sort, str):
            try:
                # Convert JSON string to dictionary
                sort = json.loads(sort)
                # Convert values to integers
                sort = {key: int(value) for key, value in sort.items()}
            except (json.JSONDecodeError, ValueError) as e:
                DebugService.app_debug_print(f"\n\n\n error sort 1 > : {e}\n\n\n", True)
                # Fallback to default if parsing fails
                sort = {'created_at': -1}
        elif isinstance(sort, dict) and sort:
            # If `sort` is already a non-empty dictionary, use it as-is
            # Convert values to integers to ensure consistency
            try:
                sort = {key: int(value) for key, value in sort.items()}
            except (ValueError, TypeError) as e:
                DebugService.app_debug_print(f"\n\n\n error sort 2 > : {e}\n\n\n", True)
                sort = {'created_at': -1}
        else:
            # If `sort` is not a string or valid dict, use the default
            sort = {'created_at': -1}
        
        return sort
    
    @staticmethod
    def normalize_sort(sort_input: Union[set, dict, List[Tuple[str, int]]]) -> List[Tuple[str, int]]:
        """
        Converts various sort formats into a list of tuples compatible with MongoDB sorting.
        
        - If input is a dictionary, convert it to a list of (key, direction) tuples.
        - If input is a set, attempt to extract key-value pairs correctly.
        - If input is already a list of tuples, return it unchanged.

        Args:
            sort_input: Input sort structure (set, dict, or list of tuples)

        Returns:
            A properly formatted list of (key, direction) tuples.

        Raises:
            ValueError: If the input set does not have a valid key-value pairing.
        """
        
        if isinstance(sort_input, list):
            # Already in correct format, return as is
            return sort_input
        
        if isinstance(sort_input, dict):
            # Convert dictionary to list of tuples
            return list(sort_input.items())

        if isinstance(sort_input, set):
            # Convert set to a sorted list (to maintain order)
            sort_list = sorted(sort_input, key=lambda x: str(x))  # Sort to ensure stability
            
            if len(sort_list) % 2 != 0:
                raise ValueError("Invalid sort set: Expected key-value pairs but got an odd number of elements")

            # Convert sorted list to tuple pairs
            return [(str(sort_list[i]), int(sort_list[i + 1])) for i in range(0, len(sort_list), 2)]

        raise TypeError("Invalid type for sort_input. Expected dict, set, or list of tuples.")

    @staticmethod
    def convert_sort_to_mongo_format(sort_input, output_format=OutputFormat.DEFAULT):
        """
        Converts a dynamic sort input into a valid MongoDB sort format.

        Args:
            sort_input (set, dict, or tuple): A set, dictionary, or tuple containing field-direction pairs.
                                            Example: {'created_at', -1, 'order_by': 1}
            output_format (OutputFormat): The desired output format (default: OutputFormat.DEFAULT).

        Returns:
            list or dict: A list of tuples or a dictionary, depending on the output_format.
                        Example: [("created_at", -1), ("order_by", 1)] or {"created_at": -1, "order_by": 1}

        Raises:
            ValueError: If the sort_input is invalid or unsupported.
        """
        sort_list = []

        # Handle tuples (if output_format is DEFAULT, return as-is)
        if isinstance(sort_input, tuple):
            if output_format == OutputFormat.DEFAULT:
                return sort_input
            elif output_format == OutputFormat.DICT:
                return dict([sort_input])
            else:
                raise ValueError("Invalid output_format for tuple input.")

        # Handle sets
        if isinstance(sort_input, set):
            # Convert the set to a list and process it
            sort_input = list(sort_input)
            for i in range(0, len(sort_input), 2):
                field = sort_input[i]
                direction = sort_input[i + 1]
                sort_list.append((field, direction))
        # Handle dictionaries
        elif isinstance(sort_input, dict):
            for field, direction in sort_input.items():
                sort_list.append((field, direction))
        else:
            raise ValueError("Invalid sort input. Must be a set, dictionary, or tuple.")

        # Convert to the desired output format
        if output_format == OutputFormat.DEFAULT:
            return sort_list
        elif output_format == OutputFormat.DICT:
            return dict(sort_list)
        else:
            raise ValueError("Invalid output_format. Must be OutputFormat.DEFAULT or OutputFormat.DICT.")
        
    @staticmethod
    def convert_enum_to_value(query):
        """
        Enhanced converter that handles enums and data type conversions for MongoDB operators.
        Supports proper type conversion for comparison operators like $lt, $gt, $gte, $lte.
        """
        if isinstance(query, dict):
            converted = {}
            for k, v in query.items():
                # Handle MongoDB comparison operators with proper type conversion
                if isinstance(v, dict) and any(op in v for op in ['$lt', '$lte', '$gt', '$gte', '$in', '$ne']):
                    converted[k] = ConverterService._convert_comparison_operators(v)
                else:
                    converted[k] = ConverterService.convert_enum_to_value(v)
            return converted
        elif isinstance(query, list):
            return [ConverterService.convert_enum_to_value(v) for v in query]
        elif isinstance(query, Enum):
            return query.value  # Convert Enum to its string value
        return query

    @staticmethod
    def _convert_comparison_operators(operator_dict):
        """
        Convert values within MongoDB comparison operators to appropriate types.
        Handles dates, numbers, ObjectIds, and other data types.
        """
        from datetime import datetime
        from bson import ObjectId
        import re

        converted = {}
        for operator, value in operator_dict.items():
            if operator in ['$lt', '$lte', '$gt', '$gte']:
                # Handle comparison operators with type conversion
                converted[operator] = ConverterService._convert_value_by_type(value)
            elif operator == '$in':
                # Handle $in operator with array of values
                if isinstance(value, list):
                    converted[operator] = [ConverterService._convert_value_by_type(v) for v in value]
                else:
                    converted[operator] = ConverterService._convert_value_by_type(value)
            else:
                # Handle other operators
                converted[operator] = ConverterService._convert_value_by_type(value)

        return converted

    @staticmethod
    def _convert_value_by_type(value):
        """
        Convert a value to the most appropriate type based on its content.
        Handles dates, numbers, ObjectIds, booleans, and strings.
        """
        from datetime import datetime
        from bson import ObjectId
        import re

        # If already converted or None, return as-is
        if value is None or isinstance(value, (ObjectId, datetime, bool)):
            return value

        # Convert enum values
        if hasattr(value, 'value'):  # Enum check
            value = value.value

        # If not a string, try basic type conversions
        if not isinstance(value, str):
            return value

        # Trim whitespace
        value = value.strip()

        # 1. Try to convert to ObjectId (MongoDB _id fields)
        if len(value) == 24 and re.match(r'^[a-fA-F0-9]{24}$', value):
            try:
                return ObjectId(value)
            except:
                pass

        # 2. Try to convert to datetime (ISO format)
        datetime_patterns = [
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$',  # ISO format
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$',  # ISO with timezone
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',  # Standard datetime
            r'^\d{4}-\d{2}-\d{2}$',  # Date only
        ]

        for pattern in datetime_patterns:
            if re.match(pattern, value):
                try:
                    # Handle different datetime formats
                    if 'T' in value:
                        # ISO format
                        if value.endswith('Z'):
                            value = value[:-1] + '+00:00'
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    elif ' ' in value:
                        # Standard datetime format
                        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    else:
                        # Date only
                        return datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    pass

        # 3. Try to convert to boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # 4. Try to convert to integer
        if re.match(r'^-?\d+$', value):
            try:
                return int(value)
            except ValueError:
                pass

        # 5. Try to convert to float
        if re.match(r'^-?\d*\.\d+$', value):
            try:
                return float(value)
            except ValueError:
                pass

        # 6. Return as string if no conversion possible
        return value
       
    @staticmethod 
    def recursive_convert(value: Any) -> Any:
        """
        Recursively convert special types in the value.
        
        - Converts ObjectId to string.
        - Converts datetime to ISO formatted string.
        - If the value is a list, recurses for each item.
        - If the value is a dict, recurses for each key/value.
        - If the value has a `dict()` method (e.g. a Pydantic model), convert it to a dict first.
        - Otherwise, returns the value unchanged.
        """
        # If the value is a Pydantic model or any object with a .dict() method:
        if hasattr(value, "dict") and callable(value.dict):
            # Convert the model instance to a dict and then recurse.
            value = value.dict()
        
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, list):
            return [ConverterService.recursive_convert(item) for item in value]
        elif isinstance(value, dict):
            return {k: ConverterService.recursive_convert(v) for k, v in value.items()}
        return value
