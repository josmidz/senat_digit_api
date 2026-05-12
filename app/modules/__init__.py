from typing import Dict
from fastapi import WebSocket

# Store active connections per organization
active_connections: Dict[str, Dict[str, WebSocket]] = {}

