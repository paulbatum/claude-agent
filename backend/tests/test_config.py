"""Shared test configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Find .env file relative to this file's location
# This file is in backend/tests/test_config.py
# .env is in the root (../../.env from here)
test_dir = Path(__file__).parent
env_path = test_dir / "../../.env"

# Load environment variables
load_dotenv(dotenv_path=env_path)

# Default model from environment with fallback
DEFAULT_MODEL = os.getenv("MODEL_NAME", "claude-haiku-4-5-20251001")
