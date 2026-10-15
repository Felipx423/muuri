import json
import os
import tempfile
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
def configuration_dir():
    override = os.environ.get("MUURI_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "darwin":
        from PyQt6.QtCore import QStandardPaths
        return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / "Muuri"
    return BASE_DIR


LIST_FILE = configuration_dir() / "pets_list.json"
CONFIG_FILE = configuration_dir() / "config.json"


def initialize_configs():
    documents = {}
    for path, filename in ((LIST_FILE, "pets_list.json"), (CONFIG_FILE, "config.json")):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            documents[path] = read_json(BASE_DIR / filename)
    if documents:
        write_configs(documents)


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_configs(documents):
    """Prepare all writes first; restore previous bytes if a replacement fails."""
    originals = {path: path.read_bytes() if path.exists() else None for path in documents}
    temporary = {}
    replaced = []
    try:
        for path, data in documents.items():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             suffix=".tmp", delete=False) as handle:
                temporary[path] = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=4)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        for path, tmp in temporary.items():
            os.replace(tmp, path)
            replaced.append(path)
    except Exception:
        for path in reversed(replaced):
            if originals[path] is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(originals[path])
        raise
    finally:
        for tmp in temporary.values():
            tmp.unlink(missing_ok=True)
