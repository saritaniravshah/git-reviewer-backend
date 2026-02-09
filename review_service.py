import httpx
from sqlalchemy.orm import Session
from models import User, Review
from error_handler import AppException
from tasks import process_review_task

class ReviewService:
    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
    
    async def start_review(self, repo_url: str):
        repo_parts = repo_url.rstrip("/").split("/")
        if len(repo_parts) < 2:
            raise AppException("Invalid repository URL", 400)
        
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]
        
        async with httpx.AsyncClient() as client:
            repo_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}",
                headers={"Authorization": f"Bearer {self.user.access_token}"}
            )
            if repo_response.status_code != 200:
                raise AppException("Repository not found or access denied", repo_response.status_code)
        
        review = Review(
            user_id=self.user.id,
            repo_url=repo_url,
            status="pending"
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        
        process_review_task.apply_async(args=[review.id, self.user.id, repo_url])
        
        return {
            "review_id": review.id,
            "status": "started",
            "message": "Review process started. Connect to WebSocket for progress updates."
        }
