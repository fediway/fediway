import os

# Set required environment variables before any imports
os.environ.setdefault("API_URL", "http://localhost:8000")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASS", "postgres")
os.environ.setdefault("DB_NAME", "fediway_test")
