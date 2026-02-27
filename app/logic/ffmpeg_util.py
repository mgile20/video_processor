import json
import subprocess

from typing import Tuple

from app.common import util


def categorize_file_type(format_name: str):
    format_name = format_name.strip().lower().lstrip(".")

    image_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg", "heic"}
    video_extensions = {"mp4", "mkv", "mov", "wmv", "flv", "avi", "avchd", "webm", "m4v"}

    if any(key in format_name for key in image_extensions):
        return "image"
    elif any(key in format_name for key in video_extensions):
        return "video"


def identify_file(file_path) -> Tuple[str, dict]:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration,avg_frame_rate",
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

    format_name: str = util.get_nested_value(result_json, "format.format_name", "")

    media_type = categorize_file_type(format_name)

    return media_type, result_json
