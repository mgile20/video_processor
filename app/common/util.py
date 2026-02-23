import asyncio
import fractions
import json
import os
import tempfile

from pathlib import Path

from PIL import Image


def get_media_type(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext in ("jpg", "jpeg", "png", "gif", "webp"):
        return "image"
    if ext in ("mp4", "mov", "webm", "mkv", "avi"):
        return "video"
    return "other"


async def get_image_metadata(src_path: Path):
    try:
        img = Image.open(str(src_path))
        return {"width": img.width, "height": img.height}
    except Exception:
        return {}


async def process_video(video_data: bytes):
    in_temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    in_temp.write(video_data)
    in_temp.flush()
    in_path = in_temp.name

    out_temp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    out_path = out_temp.name

    gif_temp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
    gif_path = gif_temp.name

    try:
        await generate_video_thumbnail(in_path, out_path)
        metadata = await get_video_metadata(in_path)

        interval = 5 * 30
        duration = metadata.get("duration")
        fps = metadata.get("fps", 10)
        if duration and fps:
            total_frames = int(duration * fps)
            interval = max(1, total_frames // 10)

            # Safety check: if interval >= total_frames,
            # you'll only ever get the first frame.
            if interval >= total_frames and total_frames > 1:
                interval = total_frames // 2

        await generate_video_timelapse_gif(in_path, gif_path, 5, interval)

        with open(out_path, "rb") as f:
            thumbnail_bytes = f.read()

        with open(gif_path, "rb") as f:
            gif_bytes = f.read()

        return metadata, thumbnail_bytes, gif_bytes

    finally:
        for path in [in_path, out_path, gif_path]:
            if os.path.exists(path):
                os.remove(path)


async def get_video_metadata(src_path: str):
    # Try ffprobe to get duration and resolution
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration,avg_frame_rate",
            "-of",
            "json",
            str(src_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()

        data: dict = json.loads(out.decode() or "{}")
        stream = (data.get("streams") or [{}])[0]
        meta = {}
        if "width" in stream and "height" in stream:
            meta["width"] = int(stream["width"])
            meta["height"] = int(stream["height"])
        if "duration" in stream:
            try:
                meta["duration"] = float(stream["duration"])
            except Exception:
                pass
        if "avg_frame_rate" in stream:
            meta["fps"] = float(fractions.Fraction(stream["avg_frame_rate"]))
        return meta
    except Exception:
        return {}


async def generate_image_thumbnail(src_path: Path, dest_path: Path, size=(320, 240)):
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(str(src_path))
        img.thumbnail(size)
        img.convert("RGB").save(str(dest_path), "JPEG")
        return True
    except Exception:
        return False


async def generate_video_thumbnail(src_path: Path, dest_path: Path, timecode="00:00:02"):
    # Use ffmpeg to grab a frame; requires ffmpeg installed on system
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(src_path),
            "-ss",
            timecode,
            "-vframes",
            "1",
            str(dest_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
    except Exception as ex:
        print(ex)


async def generate_video_timelapse_gif(src_path: Path, dest_path: Path, fps=10, interval=5):
    # 1. select: grab every Nth frame
    # 2. setpts: recalculate timing so frames are back-to-back at the target fps
    # 3. fps: enforce the final playback speed
    filters = (
        f"select='not(mod(n,{interval}))',"
        f"setpts=N/({fps}*TB),"
        f"fps={fps},"
        f"scale=320:-1:flags=lanczos"  # lanczos improves scaling quality
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            str(src_path),
            "-vf",
            filters,
            "-loop",
            "0",
            "-y",
            str(dest_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
    except Exception as ex:
        print(f"Error generating GIF: {ex}")
