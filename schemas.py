from pydantic import BaseModel

class GitHubCallbackRequest(BaseModel):
    code: str
