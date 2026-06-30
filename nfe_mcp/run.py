import sys
from pathlib import Path

_parent = Path(__file__).resolve().parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

import asyncio
from nfe_mcp.server import run


if __name__ == "__main__":
    asyncio.run(run())
