import os

# Import-time environment resolution.
BASE_URL = os.getenv("STT_BASE_URL", "https://api.sports-tracker.com/apiserver/v1")
SESSION_KEY = os.getenv("STT_SESSION_KEY", "")
