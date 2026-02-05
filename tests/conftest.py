import os
import sys
from unittest.mock import MagicMock

# Mock optional dependencies that may not be installed in test environment
sys.modules["maxminddb"] = MagicMock()

# Set required environment variables before any imports
os.environ.setdefault("API_URL", "http://localhost:8000")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASS", "postgres")
os.environ.setdefault("DB_NAME", "fediway_test")
