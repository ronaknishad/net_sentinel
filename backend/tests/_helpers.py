import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.synthetic import generate_synthetic_flows  # noqa: E402


@contextmanager
def assert_raises(exc_type, contains=None):
    try:
        yield
    except exc_type as exc:
        if contains is not None:
            assert contains.lower() in str(exc).lower(), f"'{contains}' not in '{exc}'"
        return
    raise AssertionError(f"{exc_type.__name__} was not raised")


def small_dataset(n=1200, seed=11):
    """Deterministic synthetic dataset used by the tests (no download needed)."""
    return generate_synthetic_flows(n=n, seed=seed)


import io  # noqa: E402
import tempfile  # noqa: E402

from backend.app.database.db import connect, init_db  # noqa: E402


class Env:
    """Isolated data directory, database and artifacts directory for one test."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp())
        self.db_path = self.root / "test.db"
        self.uploads = self.root / "uploads"
        self.artifacts = self.root / "artifacts"
        init_db(self.db_path)

    def db(self):
        return connect(self.db_path)


def csv_bytes(df) -> io.BytesIO:
    return io.BytesIO(df.to_csv(index=False).encode("utf-8"))
