"""Root pytest configuration: registers the shared quality fixtures."""

from __future__ import annotations

import sys
import os
from pathlib import Path

# mock-geban/ is a sibling of backend/, not part of the backend package; expose it on
# sys.path so e2e tests can `import scenario_runner` directly, the same way
# mock-geban/scenario_runner.py itself bootstraps backend/ onto sys.path.
MOCK_GEBAN_DIR = Path(__file__).resolve().parents[2] / "mock-geban"
if str(MOCK_GEBAN_DIR) not in sys.path:
    sys.path.insert(0, str(MOCK_GEBAN_DIR))

pytest_plugins = ["tests.support.quality_fixtures"]

# Existing contract fixtures intentionally exercise the historical demo catalog.
os.environ.setdefault("GEMODO_KEEP_DEMO_MODELS", "1")
