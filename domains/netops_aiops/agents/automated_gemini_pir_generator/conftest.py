"""Ensures this logical agent's own package (e.g. `tools`) is importable from its
tests, regardless of the working directory pytest is invoked from.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
