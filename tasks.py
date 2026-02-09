from celery_config import celery_app
from database import SessionLocal
from models import User, Review
import httpx
import asyncio
from ai_client import get_ai_review, parse_ai_response
from prompts import FILE_STRUCTURE_PROMPT, FILE_REVIEW_PROMPT
from socket_manager import emit_progress
import json

@celery_app.task
def process_review_task(review_id: int, user_id: int, repo_url: str):
    asyncio.run(process_review(review_id, user_id, repo_url))

async def process_review(review_id: int, user_id: int, repo_url: str):
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        review = db.query(Review).filter(Review.id == review_id).first()
        
        if not user or not review:
            return
        
        repo_parts = repo_url.rstrip("/").split("/")
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]
        
        await emit_progress(review_id, {"status": "fetching_files", "progress": 10})
        
        async with httpx.AsyncClient() as client:
            tree_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/main?recursive=1",
                headers={"Authorization": f"Bearer {user.access_token}"}
            )
            
            if tree_response.status_code != 200:
                tree_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/master?recursive=1",
                    headers={"Authorization": f"Bearer {user.access_token}"}
                )
            
            tree_data = tree_response.json()
            files = [item for item in tree_data.get("tree", []) if item["type"] == "blob"]
            
            file_tree = "\n".join([f["path"] for f in files])
            
            await emit_progress(review_id, {
                "status": "analyzing_structure",
                "progress": 20,
                "file_tree": file_tree
            })
            
            structure_prompt = FILE_STRUCTURE_PROMPT.format(file_tree=file_tree)
            structure_review = get_ai_review(structure_prompt)
            structure_result = parse_ai_response(structure_review)
            
            await emit_progress(review_id, {
                "status": "structure_complete",
                "progress": 30,
                "structure_review": structure_result
            })
            
            code_files = [f for f in files if f["path"].endswith(('.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.cpp', '.c', '.rs'))]
            total_files = min(len(code_files), 20)
            file_reviews = []
            
            for idx, file in enumerate(code_files[:20]):
                progress = 30 + int((idx / total_files) * 60)
                
                await emit_progress(review_id, {
                    "status": "reviewing_file",
                    "progress": progress,
                    "current_file": file["path"],
                    "completed": idx,
                    "total": total_files
                })
                
                content_response = await client.get(
                    file["url"],
                    headers={"Authorization": f"Bearer {user.access_token}"}
                )
                
                if content_response.status_code == 200:
                    file_data = content_response.json()
                    if file_data.get("encoding") == "base64":
                        import base64
                        content = base64.b64decode(file_data["content"]).decode("utf-8", errors="ignore")
                        
                        file_prompt = FILE_REVIEW_PROMPT.format(
                            filename=file["path"],
                            content=content[:5000]
                        )
                        
                        file_review = get_ai_review(file_prompt)
                        file_result = parse_ai_response(file_review)
                        file_reviews.append(file_result)
                        
                        await emit_progress(review_id, {
                            "status": "file_complete",
                            "progress": progress,
                            "file_review": file_result
                        })
            
            final_result = {
                "structure_review": structure_result,
                "file_reviews": file_reviews,
                "total_files_reviewed": len(file_reviews)
            }
            
            review.review_content = json.dumps(final_result)
            review.status = "completed"
            db.commit()
            
            await emit_progress(review_id, {
                "status": "completed",
                "progress": 100,
                "review_id": review_id
            })
            
    except Exception as e:
        review.status = "failed"
        db.commit()
        await emit_progress(review_id, {
            "status": "failed",
            "error": str(e)
        })
    finally:
        db.close()
