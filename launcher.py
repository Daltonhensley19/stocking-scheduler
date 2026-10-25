"""PyInstaller entry point (a plain script, since `scheduler` uses relative imports)."""

import sys

from scheduler.app import main

sys.exit(main())
