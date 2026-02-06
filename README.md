# AI Git Reviewer Backend

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at http://localhost:8000
API docs at http://localhost:8000/docs
