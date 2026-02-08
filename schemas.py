from pydantic import BaseModel

class GitHubCallbackRequest(BaseModel):
    code: str

class ReviewRequest(BaseModel):
    repo_url: str
