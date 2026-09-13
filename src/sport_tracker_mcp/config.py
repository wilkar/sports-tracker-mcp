import os
from pathlib import Path

from dotenv import load_dotenv

# Search for .env relative to project root, regardless of process working directory
project_root = Path(__file__).resolve().parents[2]
project_env = project_root / ".env"
if project_env.exists():
    load_dotenv(dotenv_path=project_env)
load_dotenv()

BASE_URL = os.getenv("STT_BASE_URL", "https://api.sports-tracker.com/apiserver/v1")
SESSION_KEY = os.getenv("STT_SESSION_KEY", "")
