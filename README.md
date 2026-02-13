# AI Git Reviewer - Backend

FastAPI backend for AI-powered Git repository code reviews with real-time WebSocket updates.

## 🎯 Overview

This backend service provides:
- **GitHub OAuth Authentication**: Secure user authentication via GitHub
- **Repository Analysis**: AI-powered code review of Git repositories
- **Real-time Updates**: WebSocket communication for live review progress
- **Async Task Processing**: Celery for background review jobs
- **Redis Integration**: Cross-process communication and task queue

## 🏗️ Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Celery with Redis
- **Real-time**: Socket.IO with Redis manager
- **AI**: OpenRouter API for code analysis
- **Authentication**: GitHub OAuth + JWT

## 📁 Project Structure

```
backend/
├── routes/
│   ├── auth.py           # GitHub OAuth endpoints
│   ├── github.py         # Repository management
│   ├── user.py           # User profile endpoints
│   └── review.py         # Review history endpoints
├── models.py             # Database models
├── schemas.py            # Pydantic schemas
├── database.py           # Database configuration
├── config.py             # Environment configuration
├── tasks.py              # Celery background tasks
├── celery_config.py      # Celery configuration
├── socket_manager.py     # Socket.IO setup
├── ai_client.py          # AI service client
├── prompts.py            # AI prompts
├── auth_utils.py         # JWT utilities
├── error_handler.py      # Global error handlers
├── main.py               # Application entry point
└── requirements.txt      # Python dependencies
```

## 🚀 Quick Start

See [SETUP.md](./SETUP.md) for detailed setup instructions.

## 📚 API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 🔑 Key Features

### Authentication
- GitHub OAuth integration
- JWT token-based session management
- Secure token verification

### Code Review
- Fetch repository structure from GitHub API
- AI-powered structure analysis
- Individual file reviews with issue detection
- Progress tracking and incremental updates

### Real-time Communication
- WebSocket connections via Socket.IO
- Redis-based message broker for multi-process support
- Live progress updates during review

### Background Processing
- Celery workers for async review tasks
- Redis as message broker and result backend
- Automatic retry logic for failed operations

## 🛠️ Development

### Running Locally

```bash
# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (in another terminal)
celery -A celery_config worker --loglevel=info

# Start Redis (required for Socket.IO and Celery)
redis-server
```

## 📝 Environment Variables

See [SETUP.md](./SETUP.md) for complete environment configuration.

## 🔐 Security

- GitHub OAuth tokens stored securely
- JWT tokens for API authentication
- Input validation with Pydantic
- SQL injection protection via SQLAlchemy ORM
- CORS configuration for production

## 📄 License

[Add your license here]
