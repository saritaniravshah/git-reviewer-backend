from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth_utils import verify_token
from error_handler import AppException

router = APIRouter()

async def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise AppException("Invalid authorization header", 401)
    
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    
    if not user_id:
        raise AppException("Invalid or expired token", 401)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException("User not found", 404)
    
    return user

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url
    }
