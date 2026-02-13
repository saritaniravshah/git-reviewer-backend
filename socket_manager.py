import socketio
import logging
from typing import Dict, Any, Optional
from config import REDIS_URL

logger = logging.getLogger(__name__)

# Create Redis-based client manager for cross-process communication
mgr = socketio.AsyncRedisManager(REDIS_URL)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=mgr
)

socket_app = socketio.ASGIApp(sio)


# Event emission helpers for review progress
async def emit_progress(review_id: int, data: dict):
    """
    Emit review progress event to a specific review channel.
    Event name: review_progress_{review_id}
    """
    event_name = f"review_progress_{review_id}"
    try:
        await sio.emit(event_name, data)
    except Exception as e:
        logger.error(f"Failed to emit {event_name}: {str(e)}")


async def emit_review_started(review_id: int, data: Dict[str, Any]):
    """Emit when review process starts"""
    await emit_progress(review_id, {
        "status": "started",
        "review_id": review_id,
        **data
    })


async def emit_fetching_files(review_id: int, progress: int = 10):
    """Emit when starting to fetch repository files"""
    await emit_progress(review_id, {
        "status": "fetching_files",
        "progress": progress
    })


async def emit_analyzing_structure(review_id: int, progress: int, file_tree: str):
    """Emit when analyzing repository structure"""
    await emit_progress(review_id, {
        "status": "analyzing_structure",
        "progress": progress,
        "file_tree": file_tree
    })


async def emit_structure_complete(review_id: int, progress: int, structure_review: Dict[str, Any]):
    """Emit when structure analysis is complete"""
    await emit_progress(review_id, {
        "status": "structure_complete",
        "progress": progress,
        "structure_review": structure_review
    })


async def emit_reviewing_file(
    review_id: int,
    progress: int,
    current_file: str,
    completed: int,
    total: int
):
    """Emit when starting to review a file"""
    await emit_progress(review_id, {
        "status": "reviewing_file",
        "progress": progress,
        "current_file": current_file,
        "completed": completed,
        "total": total
    })


async def emit_file_complete(review_id: int, progress: int, file_review: Dict[str, Any]):
    """Emit when file review is complete"""
    await emit_progress(review_id, {
        "status": "file_complete",
        "progress": progress,
        "file_review": file_review
    })


async def emit_review_completed(review_id: int):
    """Emit when entire review process is complete"""
    logger.info(f"Review {review_id} completed successfully")
    await emit_progress(review_id, {
        "status": "completed",
        "progress": 100,
        "review_id": review_id
    })


async def emit_review_failed(review_id: int, error: str, progress: int = 0):
    """Emit when review process fails"""
    logger.error(f"Review {review_id} failed: {error}")
    await emit_progress(review_id, {
        "status": "failed",
        "error": error,
        "progress": progress
    })


# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def join_review(sid, data):
    """Allow client to join a specific review room"""
    review_id = data.get('review_id')
    if review_id:
        room = f"review_{review_id}"
        await sio.enter_room(sid, room)
        return {"status": "joined", "review_id": review_id}
    return {"status": "error", "message": "No review_id provided"}


@sio.event
async def leave_review(sid, data):
    """Allow client to leave a specific review room"""
    review_id = data.get('review_id')
    if review_id:
        room = f"review_{review_id}"
        await sio.leave_room(sid, room)
        return {"status": "left", "review_id": review_id}
    return {"status": "error", "message": "No review_id provided"}
