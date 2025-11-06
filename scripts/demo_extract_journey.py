"""Demo CLI for journey info extraction.

Usage:
    python scripts/demo_extract_journey.py "<text to analyze>"

If no text is provided, uses a small built-in sample.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so top-level packages (tools) can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.journey_tools import extract_journey_info


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = (
            "JourneyId: 98765\nScore: -4.2\nReason: Excessive delay at origin due to operational issue.\n"
            "Solution: Replan connection and alert customer service."
        )

    out = extract_journey_info(text)
    print(out)


if __name__ == "__main__":
    main()
