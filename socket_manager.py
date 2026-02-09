import socketio

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

socket_app = socketio.ASGIApp(sio)

async def emit_progress(review_id: int, data: dict):
    await sio.emit(f"review_progress_{review_id}", data)
