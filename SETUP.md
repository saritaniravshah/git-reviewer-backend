# Backend Setup Guide

Complete setup instructions for the AI Git Reviewer backend.

## Prerequisites

- Python 3.10 or higher
- PostgreSQL 14 or higher
- Redis 6 or higher
- Git

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd backend
```

## Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Setup PostgreSQL Database

### Option A: Local PostgreSQL

1. Install PostgreSQL:
   - **macOS**: `brew install postgresql`
   - **Ubuntu**: `sudo apt-get install postgresql`
   - **Windows**: Download from [postgresql.org](https://www.postgresql.org/download/)

2. Start PostgreSQL service:
   - **macOS**: `brew services start postgresql`
   - **Ubuntu**: `sudo systemctl start postgresql`
   - **Windows**: Service starts automatically

3. Create database:
   ```bash
   psql -U postgres
   CREATE DATABASE git_reviewer;
   CREATE USER reviewer_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE git_reviewer TO reviewer_user;
   \q
   ```

### Option B: Using Docker

```bash
docker run -d \
  --name postgres-git-reviewer \
  -e POSTGRES_DB=git_reviewer \
  -e POSTGRES_USER=reviewer_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:14
```

## Step 5: Setup Redis

### Option A: Local Redis

1. Install Redis:
   - **macOS**: `brew install redis`
   - **Ubuntu**: `sudo apt-get install redis-server`
   - **Windows**: Use WSL or download from [redis.io](https://redis.io/download)

2. Start Redis:
   - **macOS**: `brew services start redis`
   - **Ubuntu**: `sudo systemctl start redis`
   - **WSL/Manual**: `redis-server`

### Option B: Using Docker

```bash
docker run -d \
  --name redis-git-reviewer \
  -p 6379:6379 \
  redis:6
```

## Step 6: Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://reviewer_user:your_password@localhost:5432/git_reviewer

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth
# Create GitHub OAuth App at: https://github.com/settings/developers
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:3000/auth/callback

# JWT Secret (generate a random string)
JWT_SECRET=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OpenRouter API (for AI code review)
# Get API key from: https://openrouter.ai/
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Getting GitHub OAuth Credentials

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: Git Reviewer (or your choice)
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:3000/auth/callback`
4. Click "Register application"
5. Copy **Client ID** and **Client Secret** to your `.env` file

### Getting OpenRouter API Key

1. Visit [openrouter.ai](https://openrouter.ai/)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

### Generate JWT Secret

```bash
# Generate a secure random string
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 7: Initialize Database

The database tables will be created automatically when you first run the application. Alternatively, you can create them manually:

```bash
python -c "from database import engine, Base; from models import *; Base.metadata.create_all(bind=engine)"
```

## Step 8: Run the Application

### Start the FastAPI Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- Main API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Start the Celery Worker

In a separate terminal (with virtual environment activated):

```bash
celery -A celery_config worker --loglevel=info
```

## Step 9: Verify Installation

Test the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

## 🎯 Production Deployment

For production deployment:

1. **Use production database**: Set up PostgreSQL on a managed service (AWS RDS, Google Cloud SQL, etc.)
2. **Use production Redis**: Set up Redis on a managed service (AWS ElastiCache, Redis Cloud, etc.)
3. **Update environment variables**: Use production URLs and secrets
4. **Enable HTTPS**: Configure SSL certificates
5. **Update CORS**: Restrict `allow_origins` in `main.py`
6. **Use Gunicorn**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
7. **Setup process manager**: Use systemd, supervisor, or PM2 for Celery workers
8. **Monitor logs**: Setup logging and monitoring tools

## 🐛 Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution**: Ensure PostgreSQL is running and credentials in `.env` are correct.

### Redis Connection Error

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution**: Ensure Redis is running on the specified port.

### Import Errors

```
ModuleNotFoundError: No module named 'X'
```

**Solution**: Ensure virtual environment is activated and dependencies are installed:
```bash
pip install -r requirements.txt
```

### GitHub OAuth Error

```
Invalid client_id or client_secret
```

**Solution**: Verify GitHub OAuth credentials in `.env` match your GitHub OAuth App.

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Socket.IO Documentation](https://socket.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
