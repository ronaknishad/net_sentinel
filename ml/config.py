"""Shared constants for the NetSentinel ML pipeline."""
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_DIR.parent
DEFAULT_ARTIFACTS_DIR = ML_DIR / "artifacts"
DEFAULT_DATA_DIR = ML_DIR / "data"

BUNDLE_FILENAME = "model_bundle.joblib"
EVALUATION_FILENAME = "evaluation.json"

MAX_FILE_BYTES = 500 * 1024 * 1024      # reject files larger than 500 MB
MAX_ROWS = 2_000_000                    # reject files with more rows than this
MIN_MAPPED_FEATURES = 6                 # minimum schema features a dataset must provide
RANDOM_SEED = 42
DEFAULT_TEST_SIZE = 0.25
MIN_CLASS_SAMPLES = 10                  # classes rarer than this are excluded (and reported)

NORMAL_LABEL = "Normal"
SUSPICIOUS_LABEL = "Suspicious"
