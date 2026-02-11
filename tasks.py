from celery_config import celery_app
from database import SessionLocal
from models import User, Review
import httpx
import asyncio
from ai_client import get_ai_review, parse_ai_response
from prompts import FILE_STRUCTURE_PROMPT, FILE_REVIEW_PROMPT
from socket_manager import (
    emit_fetching_files,
    emit_analyzing_structure,
    emit_structure_complete,
    emit_reviewing_file,
    emit_file_complete,
    emit_review_completed,
    emit_review_failed
)
import json
import logging
from typing import Optional, Dict, List, Any
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
MAX_FILES_TO_REVIEW = 20
MAX_CONTENT_LENGTH = 5000
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# File extensions to review
REVIEWABLE_EXTENSIONS = (
    '.py', '.js', '.ts', '.tsx', '.jsx',
    '.java', '.go', '.rb', '.php',
    '.cpp', '.c', '.rs', '.cs',
    '.swift', '.kt', '.scala'
)

# Common branch names to try
DEFAULT_BRANCHES = ['main', 'master', 'develop', 'dev']


class ReviewError(Exception):
    """Custom exception for review-related errors"""
    pass


@celery_app.task
def process_review_task(review_id: int, user_id: int, repo_url: str):
    """Celery task wrapper for processing reviews"""
    try:
        asyncio.run(process_review(review_id, user_id, repo_url))
    except Exception as e:
        logger.error(f"Review task failed for review_id={review_id}: {str(e)}", exc_info=True)
        # Ensure the error is propagated to the database
        db = SessionLocal()
        try:
            review = db.query(Review).filter(Review.id == review_id).first()
            if review:
                review.status = "failed"
                db.commit()
        finally:
            db.close()


async def process_review(review_id: int, user_id: int, repo_url: str):
    """Main review processing function"""
    db = SessionLocal()
    
    try:
        # Validate user and review existence
        user = db.query(User).filter(User.id == user_id).first()
        review = db.query(Review).filter(Review.id == review_id).first()
        
        if not user:
            logger.error(f"User not found: user_id={user_id}")
            raise ReviewError(f"User not found: {user_id}")
        
        if not review:
            logger.error(f"Review not found: review_id={review_id}")
            raise ReviewError(f"Review not found: {review_id}")
        
        # Update review status to processing
        review.status = "processing"
        review.progress = 0
        db.commit()
        
        logger.info(f"Starting review for review_id={review_id}, repo={repo_url}")
        
        # Parse repository information
        repo_parts = repo_url.rstrip("/").split("/")
        if len(repo_parts) < 2:
            raise ReviewError(f"Invalid repository URL: {repo_url}")
        
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]
        
        # Step 1: Fetch repository files
        await emit_fetching_files(review_id, progress=10)
        review.progress = 10
        db.commit()
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Get repository file tree
            tree_data = await fetch_repository_tree(
                client=client,
                owner=owner,
                repo_name=repo_name,
                access_token=user.access_token
            )
            
            files = [item for item in tree_data.get("tree", []) if item["type"] == "blob"]
            
            # Create file tree string
            file_tree = "\n".join([f["path"] for f in files])
            
            # Step 2: Analyze repository structure
            await emit_analyzing_structure(review_id, progress=20, file_tree=file_tree)
            review.progress = 20
            db.commit()
            
            structure_review = await analyze_structure(file_tree, review_id)
            
            await emit_structure_complete(
                review_id,
                progress=30,
                structure_review=structure_review
            )
            review.progress = 30
            db.commit()
            
            # Update review in database with structure analysis
            review.review_content = json.dumps({
                "file_tree": file_tree,
                "structure_review": structure_review,
                "file_reviews": []
            })
            db.commit()
            
            # Step 3: Review individual files
            code_files = filter_reviewable_files(files)
            total_files = min(len(code_files), MAX_FILES_TO_REVIEW)
            
            file_reviews_dict = {}
            
            for idx, file in enumerate(code_files[:MAX_FILES_TO_REVIEW]):
                progress = 30 + int((idx / total_files) * 60)
                
                await emit_reviewing_file(
                    review_id,
                    progress=progress,
                    current_file=file["path"],
                    completed=idx,
                    total=total_files
                )
                
                try:
                    file_review = await review_file(
                        client=client,
                        file=file,
                        access_token=user.access_token,
                        review_id=review_id
                    )
                    
                    if file_review:
                        file_reviews_dict[file["path"]] = file_review
                        
                        await emit_file_complete(
                            review_id,
                            progress=progress + 1,
                            file_review=file_review
                        )
                        
                        # Update database incrementally
                        review.review_content = json.dumps({
                            "file_tree": file_tree,
                            "structure_review": structure_review,
                            "file_reviews": list(file_reviews_dict.values()),
                            "total_files_reviewed": len(file_reviews_dict)
                        })
                        review.progress = progress + 1
                        db.commit()
                        
                except Exception as e:
                    logger.warning(f"Failed to review file {file['path']}: {str(e)}")
                    # Continue with other files even if one fails
                    continue
            
            # Step 4: Complete review
            final_result = {
                "file_tree": file_tree,
                "structure_review": structure_review,
                "file_reviews": list(file_reviews_dict.values()),
                "total_files_reviewed": len(file_reviews_dict)
            }
            
            review.review_content = json.dumps(final_result)
            review.status = "completed"
            review.progress = 100
            db.commit()
            
            await emit_review_completed(review_id)
            
    except ReviewError as e:
        logger.error(f"Review error for review_id={review_id}: {str(e)}")
        review.status = "failed"
        db.commit()
        await emit_review_failed(review_id, error=str(e))
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error for review_id={review_id}: {str(e)}")
        review.status = "failed"
        db.commit()
        await emit_review_failed(
            review_id,
            error=f"Failed to fetch repository data: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error for review_id={review_id}: {str(e)}", exc_info=True)
        review.status = "failed"
        db.commit()
        await emit_review_failed(
            review_id,
            error=f"An unexpected error occurred: {str(e)}"
        )
        
    finally:
        db.close()


async def fetch_repository_tree(
    client: httpx.AsyncClient,
    owner: str,
    repo_name: str,
    access_token: str
) -> Dict[str, Any]:
    """Fetch repository file tree from GitHub API"""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try different branch names
    for branch in DEFAULT_BRANCHES:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                continue  # Try next branch
            else:
                response.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue
            raise
    
    # If all branches fail, raise error
    raise ReviewError(f"Could not find repository tree. Tried branches: {', '.join(DEFAULT_BRANCHES)}")


def filter_reviewable_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter files to only include reviewable code files"""
    reviewable_files = []
    
    for file in files:
        path = file["path"]
        
        # Skip files in common directories to ignore
        if any(skip in path for skip in ['node_modules/', 'venv/', '.git/', 'dist/', 'build/', '__pycache__/']):
            continue
        
        # Check if file has a reviewable extension
        if path.endswith(REVIEWABLE_EXTENSIONS):
            reviewable_files.append(file)
    
    return reviewable_files


async def analyze_structure(file_tree: str, review_id: int) -> Dict[str, Any]:
    """Analyze repository structure using AI"""
    try:
        structure_prompt = FILE_STRUCTURE_PROMPT.format(file_tree=file_tree)
        
        # Get AI review with retry logic
        for attempt in range(MAX_RETRIES):
            try:
                structure_review = get_ai_review(structure_prompt)
                structure_result = parse_ai_response(structure_review)
                
                # Validate response has required fields
                if "overall_rating" in structure_result and "issues" in structure_result:
                    return structure_result
                else:
                    logger.warning(f"Invalid structure review response (attempt {attempt + 1})")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    
            except Exception as e:
                logger.warning(f"Structure analysis attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise
        
        # Return default structure if all retries fail
        return {
            "overall_rating": "needs_improvement",
            "issues": [],
            "strengths": [],
            "recommendations": ["Unable to complete full analysis"]
        }
        
    except Exception as e:
        logger.error(f"Structure analysis failed for review_id={review_id}: {str(e)}")
        return {
            "overall_rating": "needs_improvement",
            "issues": [{
                "type": "structure",
                "severity": "warning",
                "message": f"Analysis failed: {str(e)}",
                "suggestion": "Please try again"
            }],
            "strengths": [],
            "recommendations": []
        }


async def review_file(
    client: httpx.AsyncClient,
    file: Dict[str, Any],
    access_token: str,
    review_id: int
) -> Optional[Dict[str, Any]]:
    """Review a single file using AI"""
    file_path = file["path"]
    
    try:
        
        # Fetch file content
        content_response = await client.get(
            file["url"],
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if content_response.status_code != 200:
            logger.warning(f"Failed to fetch content for {file_path}: {content_response.status_code}")
            return None
        
        file_data = content_response.json()
        
        # Decode content
        if file_data.get("encoding") == "base64":
            try:
                content = base64.b64decode(file_data["content"]).decode("utf-8", errors="ignore")
            except Exception as e:
                logger.warning(f"Failed to decode {file_path}: {str(e)}")
                return None
        else:
            content = file_data.get("content", "")
        
        # Truncate content if too long
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        
        # Get AI review with retry logic
        for attempt in range(MAX_RETRIES):
            try:
                file_prompt = FILE_REVIEW_PROMPT.format(
                    filename=file_path,
                    content=content
                )
                
                file_review = get_ai_review(file_prompt)
                file_result = parse_ai_response(file_review)
                
                # Validate response has required fields
                if "filename" in file_result and "issues" in file_result:
                    return file_result
                else:
                    logger.warning(f"Invalid file review response for {file_path} (attempt {attempt + 1})")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                        
            except Exception as e:
                logger.warning(f"File review attempt {attempt + 1} failed for {file_path}: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise
        
        # Return minimal review if all retries fail
        return {
            "filename": file_path,
            "issues": [],
            "summary": {
                "total_issues": 0,
                "critical": 0,
                "warnings": 0,
                "info": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to review file {file_path}: {str(e)}")
        return {
            "filename": file_path,
            "issues": [{
                "type": "bug",
                "severity": "warning",
                "message": f"Review failed: {str(e)}",
                "suggestion": "Manual review recommended"
            }],
            "summary": {
                "total_issues": 1,
                "critical": 0,
                "warnings": 1,
                "info": 0
            }
        }
