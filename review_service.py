import httpx
from sqlalchemy.orm import Session
from models import User, Review
from ai_client import get_ai_review
from error_handler import AppException

class ReviewService:
    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
    
    async def review_repository(self, repo_url: str):
        repo_parts = repo_url.rstrip("/").split("/")
        if len(repo_parts) < 2:
            raise AppException("Invalid repository URL", 400)
        
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]
        
        async with httpx.AsyncClient() as client:
            commits_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/commits",
                headers={"Authorization": f"Bearer {self.user.access_token}"},
                params={"per_page": 1}
            )
            
            if commits_response.status_code != 200:
                raise AppException("Failed to fetch repository commits", commits_response.status_code)
            
            commits = commits_response.json()
            if not commits:
                raise AppException("No commits found in repository", 404)
            
            latest_commit = commits[0]
            commit_sha = latest_commit["sha"]
            
            diff_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/commits/{commit_sha}",
                headers={"Authorization": f"Bearer {self.user.access_token}"}
            )
            
            if diff_response.status_code != 200:
                raise AppException("Failed to fetch commit diff", diff_response.status_code)
            
            commit_data = diff_response.json()
            files = commit_data.get("files", [])
            
            review_prompt = self._build_review_prompt(repo_name, commit_sha, files)
            ai_review = get_ai_review(review_prompt)
            
            review = Review(
                user_id=self.user.id,
                repo_url=repo_url,
                commit_hash=commit_sha,
                review_content=ai_review
            )
            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)
            
            return {
                "review_id": review.id,
                "repo_url": repo_url,
                "commit_hash": commit_sha,
                "review": ai_review
            }
    
    def _build_review_prompt(self, repo_name: str, commit_sha: str, files: list) -> str:
        prompt = f"Review the following code changes from repository '{repo_name}' (commit: {commit_sha}):\n\n"
        
        for file in files[:10]:
            prompt += f"File: {file['filename']}\n"
            prompt += f"Status: {file['status']}\n"
            if "patch" in file:
                prompt += f"Changes:\n{file['patch']}\n\n"
        
        prompt += "Provide a detailed code review covering:\n"
        prompt += "1. Code quality and best practices\n"
        prompt += "2. Potential bugs or issues\n"
        prompt += "3. Security concerns\n"
        prompt += "4. Performance improvements\n"
        prompt += "5. Suggestions for improvement"
        
        return prompt
