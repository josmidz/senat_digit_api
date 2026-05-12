from starlette.types import Message, Receive, Scope


_CACHED_BODY_KEY = "_cached_http_body"
_CACHED_DISCONNECT_KEY = "_cached_http_disconnect"


def has_cached_body(scope: Scope) -> bool:
    return _CACHED_BODY_KEY in scope


async def get_cached_body(scope: Scope, receive: Receive) -> bytes:
    cached_body = scope.get(_CACHED_BODY_KEY)
    if isinstance(cached_body, bytes):
        return cached_body

    body_chunks: list[bytes] = []
    disconnect_message: Message | None = None

    while True:
        message = await receive()
        message_type = message.get("type")

        if message_type == "http.disconnect":
            disconnect_message = message
            break

        if message_type != "http.request":
            continue

        body_chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break

    body = b"".join(body_chunks)
    scope[_CACHED_BODY_KEY] = body

    if disconnect_message is not None:
        scope[_CACHED_DISCONNECT_KEY] = disconnect_message

    return body


def build_receive_with_cached_body(scope: Scope) -> Receive:
    cached_body = scope.get(_CACHED_BODY_KEY, b"")
    disconnect_message = scope.get(_CACHED_DISCONNECT_KEY)
    body_sent = False
    disconnect_sent = False

    async def receive() -> Message:
        nonlocal body_sent, disconnect_sent

        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": cached_body, "more_body": False}

        if disconnect_message is not None and not disconnect_sent:
            disconnect_sent = True
            return disconnect_message

        return {"type": "http.request", "body": b"", "more_body": False}

    return receive
