import os
import sys
from pathlib import Path

os.environ.setdefault("GREENHOUSE_API_KEY", "test-api-key")
os.environ.setdefault("GREENHOUSE_BASE_URL", "https://harvest.greenhouse.io/v1")
# Intentionally do NOT default GREENHOUSE_USER_ID — tests that exercise
# write paths set it explicitly so we test the missing-env behavior too.
os.environ.pop("GREENHOUSE_USER_ID", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
