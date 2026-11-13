"""memory package — re-export the jarvis_memory module so `import memory`
resolves to the SQLite memory module, not the memory/ directory of logs."""
import sys, os
_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
from jarvis_memory import (  # noqa: F401
    init_db,
    log_episode,
    search_keyword,
    add_memory,
    get_recent_episodes,
    DEFAULT_DB,
)
