"""Run unit tests for the project without requiring pytest.

This script imports the test module and runs each test function, reporting failures.
"""
import importlib
import sys
from pathlib import Path

# Ensure repository root is on sys.path so tests and tools import correctly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    mod = importlib.import_module("tests.test_journey_tools")
    test_funcs = [
        getattr(mod, name)
        for name in dir(mod)
        if name.startswith("test_") and callable(getattr(mod, name))
    ]

    failures = 0
    for f in test_funcs:
        try:
            f()
            print(f"OK: {f.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {f.__name__} -> {e}")
        except Exception as e:
            failures += 1
            print(f"ERROR: {f.__name__} -> {e}")

    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    else:
        print("\nAll tests passed")


if __name__ == "__main__":
    run_tests()
