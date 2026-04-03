"""Pytest configuration for repository-local imports."""

from pathlib import Path
import sys

# Ensure tests can import top-level modules (e.g., bibtex_refiner.py)
# regardless of pytest import mode or CI runner path behavior.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
