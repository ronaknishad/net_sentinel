"""Runtime settings. Paths can be overridden with environment variables (used by tests)."""
import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "NetSentinel"
APP_VERSION = "0.3.0"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

MAX_UPLOAD_BYTES = 200 * 1024 * 1024      # per uploaded CSV
MAX_ANALYSIS_ROWS = 100_000               # flows stored per analysis
MAX_SYNTHETIC_ROWS = 5_000
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    artifacts_dir: Path

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "netsentinel.db"


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("NETSENTINEL_DATA_DIR", PROJECT_ROOT / "backend" / "data"))
    artifacts = Path(os.environ.get("NETSENTINEL_ARTIFACTS_DIR", PROJECT_ROOT / "ml" / "artifacts"))
    return Settings(data_dir=data_dir, artifacts_dir=artifacts)
