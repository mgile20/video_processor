import json
import subprocess

from typing import Tuple


def get_nested_value(data: dict, path: str, default=None):
    keys = path.split(".")
    val = data
    for key in keys:
        if isinstance(val, dict):
            val = val.get(key, default)
        else:
            return default
    return val


def categorize_file_type(format_name: str):
    format_name = format_name.strip().lower().lstrip(".")

    image_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg", "heic"}
    video_extensions = {"mp4", "mkv", "mov", "wmv", "flv", "avi", "avchd", "webm", "m4v"}

    if format_name in image_extensions:
        return "image"
    elif format_name in video_extensions:
        return "video"


def identify_file(file_path) -> Tuple[str, dict]:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        file_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(result.stderr)

    result_json = json.loads(result.stdout)

    if not isinstance(result_json, dict):
        raise Exception("ffprobe result not dict")

    format_name: str = get_nested_value(result_json, "format.format_name", "")
    first_format: str = format_name.split(",")[0]

    media_type = categorize_file_type(first_format)

    return media_type, result_json
