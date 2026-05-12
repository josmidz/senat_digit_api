#app/constants/keys.py

class RedisKeys:
    """
    A centralized place to define all static keys for Redis or other purposes.

    Example Usage:
    ---------------
    # Accessing static keys
    print(RedisKeys.ITEMS_LIST)  # Output: "items:list"

    # Formatting keys with dynamic parameters
    user_session_key = RedisKeys.format_key(RedisKeys.USER_SESSION, user_id=123)
    print(user_session_key)  # Output: "user:session:123"

    # Getting a key description
    description = RedisKeys.describe_key("USER_SESSION")
    print(description)
    """

    #: Key to store app languages data. No  parameter required.
    APP_LANGS = "app:languages"
    
    #: Key to store user session data. Requires `user_id` as a parameter.
    USER_SESSION = "user:session:{user_id}"
    
    #: Key to store user profile data. Requires `user_id` as a parameter.
    USER_PROFILE = "user:profile:{user_id}"
    
    #: Key to store item details. Requires `item_id` as a parameter.
    ITEM_DETAILS = "item:details:{item_id}"
    
    #: Key to store a list of all items. No dynamic parameters required.
    ITEMS_LIST = "items:list"
    
    #: Key to store transaction history. Requires `user_id` as a parameter.
    TRANSACTION_HISTORY = "transaction:history:{user_id}"
    
    #: Key to store currency exchange rates. No dynamic parameters required.
    CURRENCY_EXCHANGE_RATES = "currency:exchange_rates"
    
    #: Key to store global settings. No dynamic parameters required.
    GLOBAL_SETTINGS = "global:settings"

    # WebSocket Event Keys
    #: Key to store pending notifications for disconnected users. Requires `user_hash` and `event_id` as parameters.
    PENDING_NOTIFICATION = "event:notification:{user_hash}:{event_id}"

    #: Key to store pending instruction events for disconnected users. Requires `user_hash` and `instruction_id` as parameters.
    PENDING_INSTRUCTION = "event:instruction:{user_hash}:{instruction_id}"

    #: Key to store active instruction data. Requires `expected_action` and `instruction_id` as parameters.
    ACTIVE_INSTRUCTION = "instruction:{expected_action}:{instruction_id}"

    #: Key to store sudo action data. Requires `instruction_id` as parameter.
    SUDO_ACTION = "instruction:SUDO_ACTION:{instruction_id}"

    #: Key to store pending web lock status for a user. Requires `user_socket_hash` as parameter.
    PENDING_WEB_SCREEN_LOCK = "event:screen_lock:web:{user_socket_hash}"

    #: Key to track the server-side context of a multi-step grouped validation
    #: process. Requires `process_id` (UUID4) as parameter.
    #: Payload (JSON): {process_id, root_validation_request_id,
    #: current_validation_request_id, organization_id, sudo_action_type, created_at}
    #: TTL: 6 hours.
    VALIDATION_PROCESS = "instruction:VALIDATION_PROCESS:{process_id}"

    @staticmethod
    def format_key(key_template: str, **kwargs) -> str:
        """
        Formats a key template with dynamic values.

        Example:
            RedisKeys.format_key(RedisKeys.USER_SESSION, user_id=123)
            Output: "user:session:123"
        """
        return key_template.format(**kwargs)

    @classmethod
    def describe_key(cls, key_name: str) -> str:
        """
        Returns the description of the given key.

        Example:
            RedisKeys.describe_key("USER_SESSION")
            Output: "Key to store user session data. Requires user_id as a parameter."
        """
        descriptions = {
            "USER_SESSION": "Key to store user session data. Requires `user_id` as a parameter.",
            "USER_PROFILE": "Key to store user profile data. Requires `user_id` as a parameter.",
            "ITEM_DETAILS": "Key to store item details. Requires `item_id` as a parameter.",
            "ITEMS_LIST": "Key to store a list of all items. No dynamic parameters required.",
            "TRANSACTION_HISTORY": "Key to store transaction history. Requires `user_id` as a parameter.",
            "CURRENCY_EXCHANGE_RATES": "Key to store currency exchange rates. No dynamic parameters required.",
            "GLOBAL_SETTINGS": "Key to store global settings. No dynamic parameters required.",
            "PENDING_NOTIFICATION": "Key to store pending notifications for disconnected users. Requires `user_hash` and `event_id` as parameters.",
            "PENDING_INSTRUCTION": "Key to store pending instruction events for disconnected users. Requires `user_hash` and `instruction_id` as parameters.",
            "ACTIVE_INSTRUCTION": "Key to store active instruction data. Requires `expected_action` and `instruction_id` as parameters.",
            "SUDO_ACTION": "Key to store sudo action data. Requires `instruction_id` as parameter.",
            "PENDING_WEB_SCREEN_LOCK": "Key to store pending web lock status for a user. Requires `user_socket_hash` as parameter.",
            "VALIDATION_PROCESS": "Key to track multi-step grouped validation process context. Requires `process_id` (UUID4) as parameter. TTL: 6 h.",
        }
        return descriptions.get(key_name, "Description not available.")

