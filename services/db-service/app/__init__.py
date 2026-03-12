from pathlib import Path
import sys

_THIS_FILE = Path(__file__).resolve()

# Szukamy repo root dynamicznie - działa zarówno lokalnie jak i w kontenerze
def _find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "libs").exists():
            return parent
    return start

_REPO_ROOT = _find_repo_root(_THIS_FILE.parent)

repo_root_str = str(_REPO_ROOT)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)