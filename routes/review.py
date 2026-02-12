from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Review
from routes.github import get_current_user
from error_handler import AppException
from typing import Optional
import json

router = APIRouter()

@router.get("/{review_id}")
async def get_review(review_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    review = db.query(Review).filter(Review.id == review_id, Review.user_id == current_user.id).first()
    
    if not review:
        raise AppException("Review not found", 404)
    
    review_data = json.loads(review.review_content) if review.review_content else {}
    
    # Calculate statistics
    stats = calculate_review_stats(review_data)
    
    return {
        "id": review.id,
        "repo_url": review.repo_url,
        "status": review.status,
        "progress": review.progress,
        "created_at": review.created_at,
        "review_content": review_data,
        "stats": stats
    }

@router.get("/")
async def get_review_history(repo_url: Optional[str] = Query(None), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    query = db.query(Review).filter(Review.user_id == current_user.id)
    
    if repo_url:
        query = query.filter(Review.repo_url == repo_url)
    
    reviews = query.order_by(Review.created_at.desc()).all()
    
    history = []
    for review in reviews:
        review_data = json.loads(review.review_content) if review.review_content else {}
        stats = calculate_review_stats(review_data)
        
        history.append({
            "id": review.id,
            "repo_url": review.repo_url,
            "status": review.status,
            "progress": review.progress,
            "created_at": review.created_at,
            "stats": stats
        })
    
    return {"reviews": history}

def calculate_review_stats(review_data: dict) -> dict:
    stats = {
        "total_issues": 0,
        "critical": 0,
        "warnings": 0,
        "info": 0,
        "files_reviewed": 0
    }
    
    if not review_data:
        return stats
    
    file_reviews = review_data.get("file_reviews", [])
    stats["files_reviewed"] = len(file_reviews)
    
    for file_review in file_reviews:
        summary = file_review.get("summary", {})
        stats["total_issues"] += summary.get("total_issues", 0)
        stats["critical"] += summary.get("critical", 0)
        stats["warnings"] += summary.get("warnings", 0)
        stats["info"] += summary.get("info", 0)
    
    structure_review = review_data.get("structure_review", {})
    structure_issues = structure_review.get("issues", [])
    for issue in structure_issues:
        severity = issue.get("severity", "info")
        if severity == "critical":
            stats["critical"] += 1
        elif severity == "warning":
            stats["warnings"] += 1
        else:
            stats["info"] += 1
        stats["total_issues"] += 1
    
    return stats
