def get_nested_value(data: dict, path: str, default=None):
    keys = path.split(".")
    val = data
    for key in keys:
        if isinstance(val, dict):
            val = val.get(key, default)
        else:
            return default
    return val
