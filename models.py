from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, index=True)
    commit_hash = Column(String)
    review_content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
