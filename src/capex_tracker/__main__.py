"""Allow running the tool as ``python -m capex_tracker``."""

import sys

from capex_tracker.cli import main

if __name__ == "__main__":
    sys.exit(main())
