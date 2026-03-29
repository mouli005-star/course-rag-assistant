import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
DOTENV_PATH = PROJECT_ROOT / ".env"
RECOMMENDED_PYTHON = "3.11 or 3.12"


def load_project_env():
	load_dotenv(DOTENV_PATH)


def warn_python_compatibility():
	if sys.version_info >= (3, 14):
		warnings.warn(
			"Python 3.14+ may be incompatible with parts of the current "
			"LangChain stack (Pydantic v1 path). Use Python 3.11 or 3.12 "
			"for best stability.",
			RuntimeWarning,
			stacklevel=2,
		)


def get_openai_api_key(required=True):
	load_project_env()
	api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
	if required and not api_key:
		raise RuntimeError(
			"OPENAI_API_KEY not found. Add it to .env or set it in your environment."
		)
	return api_key
