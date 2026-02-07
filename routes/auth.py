from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import httpx
from database import get_db
from models import User
from auth_utils import create_access_token
from config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI
from error_handler import AppException
from schemas import GitHubCallbackRequest

router = APIRouter()

@router.get("/github")
async def github_login():
    return {
        "url": f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_REDIRECT_URI}&scope=user,repo"
    }

@router.post("/github/callback")
async def github_callback(request: GitHubCallbackRequest, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": request.code,
            },
            headers={"Accept": "application/json"}
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise AppException("Failed to get access token", 400)
        
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        github_user = user_response.json()
        
        user = db.query(User).filter(User.github_id == str(github_user["id"])).first()
        
        if not user:
            user = User(
                github_id=str(github_user["id"]),
                username=github_user["login"],
                email=github_user.get("email"),
                avatar_url=github_user.get("avatar_url"),
                access_token=access_token
            )
            db.add(user)
        else:
            user.access_token = access_token
            user.username = github_user["login"]
            user.email = github_user.get("email")
            user.avatar_url = github_user.get("avatar_url")
        
        db.commit()
        db.refresh(user)
        
        jwt_token = create_access_token(user.id)
        
        return {
            "access_token": jwt_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url
            }
        }
