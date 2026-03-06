from pathlib import Path


def get_nested_value(data: dict, path: str, default=None):
    keys = path.split(".")
    val = data
    for key in keys:
        if isinstance(val, dict):
            val = val.get(key, default)
        else:
            return default
    return val


def get_project_root() -> Path:
    """Recursively find the project root by looking for a marker file."""
    current_path = Path(__file__).resolve()
    for parent in [current_path] + list(current_path.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return current_path.parent
