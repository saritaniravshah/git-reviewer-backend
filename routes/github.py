from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
import httpx
from database import get_db
from models import User
from auth_utils import verify_token
from error_handler import AppException
from schemas import ReviewRequest
from review_service import ReviewService

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

@router.get("/repos")
async def list_repos(current_user: User = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {current_user.access_token}"},
            params={"per_page": 100, "sort": "updated"}
        )
        
        if response.status_code != 200:
            raise AppException("Failed to fetch repositories", response.status_code)
        
        repos = response.json()
        # socket
        return {
            "repos": [
                {
                    "id": repo["id"],
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "url": repo["html_url"],
                    "private": repo["private"],
                    "description": repo.get("description"),
                    "updated_at": repo["updated_at"]
                }
                for repo in repos
            ]
        }

@router.post("/review")
async def create_review(
    request: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    review_service = ReviewService(current_user, db)
    result = await review_service.start_review(request.repo_url)
    return result
