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


def is_heif(file_path):
    try:
        with open(file_path, "rb") as f:
            # Read the first 12 bytes
            header = f.read(12)

            # ISOBMFF files (HEIF/MP4) start with 'ftyp' at offset 4
            if len(header) < 12 or header[4:8] != b"ftyp":
                return False

            # Common HEIF brands
            heif_brands = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}

            # The major brand is at offset 8
            major_brand = header[8:12]
            return major_brand in heif_brands
    except IOError:
        return False


def identify_file(file_path) -> Tuple[str, dict]:
    if is_heif(file_path):
        return "image", {"format": {"format_name": "heic"}}

    cmd = [
        "ffprobe",
        # "-v",
        # "quiet",
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
