import json
import subprocess

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dateutil import parser

from app.models.video_processor_result_model import VideoProcessorResultModel


class VideoProcessor:
    @classmethod
    def _get_captured_dt(cls, file_path) -> datetime | None:
        cmd = [
            "exiftool",
            "-json",
            "-api",
            "QuickTimeUTC",  # Normalizes UTC tags
            "-CreationDate",  # Apple's local time tag
            "-DateTimeOriginal",  # Common photo/video tag
            "-CreateDate",  # Backup standard tag
            file_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            metadata = json.loads(result.stdout)[0]
            dt_str: str | None = None

            if "CreationDate" in metadata:
                dt_str = metadata["CreationDate"]
            elif "DateTimeOriginal" in metadata:
                dt_str = metadata["DateTimeOriginal"]
            elif "CreateDate" in metadata:
                dt_str = metadata["CreateDate"]

            if not dt_str:
                return dt_str

            normalized_date = dt_str.replace(":", "-", 2)
            dt_aware = parser.parse(normalized_date)

            return dt_aware

        except Exception as ex:
            print(ex)

        return None

    @classmethod
    def _generate_thumbnail(cls, path: Path, timecode="00:00:02") -> bytes | None:
        dest_path = path.parent.joinpath(f"{uuid4().hex}.jpg")

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            timecode,
            "-i",
            str(path),
            "-vframes",
            "1",
            "-f",
            "image2",
            str(dest_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return dest_path.read_bytes()

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr}")
        except Exception as ex:
            print(f"General Error: {ex}")
        finally:
            if dest_path.exists():
                dest_path.unlink()

        return None

    @classmethod
    def _generate_time_lapse_gif(cls, path: Path, fps=10, interval=5) -> bytes | None:
        dest_path = path.parent.joinpath(f"{uuid4().hex}.gif")

        filters = f"select='not(mod(n,{interval}))'," f"setpts=N/({fps}*TB)," f"fps={fps}," f"scale=320:-1:flags=lanczos"

        cmd = [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            filters,
            "-loop",
            "0",
            "-y",
            str(dest_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return dest_path.read_bytes()

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr}")
        except Exception as ex:
            print(f"General Error: {ex}")
        finally:
            if dest_path.exists():
                dest_path.unlink()

        return None

    @classmethod
    def run(cls, path: Path):
        return VideoProcessorResultModel(
            thumbnail_bytes=cls._generate_thumbnail(path),
            gif_bytes=cls._generate_time_lapse_gif(path),
            captured_at=cls._get_captured_dt(path),
        )
