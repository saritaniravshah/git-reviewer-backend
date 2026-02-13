from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from database import engine, Base
from routes.auth import router as auth_router
from routes.github import router as github_router
from routes.user import router as user_router
from routes.review import router as review_router
from socket_manager import socket_app
from error_handler import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Git Reviewer")

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(github_router, prefix="/api/github", tags=["github"])
app.include_router(user_router, prefix="/api/user", tags=["user"])
app.include_router(review_router, prefix="/api/review", tags=["review"])

app.mount("/socket.io", socket_app)

@app.get("/")
def root():
    return {"message": "AI Git Reviewer API"}

@app.get("/health")
def health():
    return {"status": "healthy"}
