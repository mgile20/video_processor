import os
import shutil
import tempfile

from multiprocessing import Pool
from multiprocessing import cpu_count

import ffmpeg


def process_clip(args):
    """
    Stage 1: Normalize every clip to identical specs (1080p, 30fps, Stereo 44.1kHz).
    This prevents the concat demuxer from glitching due to mismatched streams.
    """
    i, item, temp_dir, image_duration = args
    path = item["path"]
    media_type = item["type"]
    temp_output = os.path.join(temp_dir, f"clip_{i:03d}.mp4")

    # 1. Setup Input
    if media_type == "video":
        probe = ffmpeg.probe(path)
        duration = float(probe["format"]["duration"])
        input_stream = ffmpeg.input(path)
    else:
        duration = image_duration
        input_stream = ffmpeg.input(path, loop=1, t=image_duration)

    # 2. Video Processing (Standardize Resolution & Frame Rate)
    v = (
        input_stream.video.filter("scale", 1920, 1080, force_original_aspect_ratio="decrease")
        .filter("pad", 1920, 1080, "(ow-iw)/2", "(oh-ih)/2")
        .filter("fps", 30)
        .filter("format", "yuv420p")
    )

    # 3. Audio Processing (Strictly Standardize Sample Rate & Layout)
    if media_type == "image":
        a = ffmpeg.input("anullsrc=cl=stereo:r=44100", f="lavfi", t=duration).audio
    else:
        try:
            # We force 2-channel stereo and 44.1k to ensure amix doesn't fail later
            a = (
                input_stream.audio.filter("aresample", 44100)
                .filter("aformat", sample_fmts="fltp", channel_layouts="stereo")
                .filter("atrim", duration=duration)  # Ensure audio isn't longer than video
            )
        except Exception:
            a = ffmpeg.input("anullsrc=cl=stereo:r=44100", f="lavfi", t=duration).audio

    # 4. Output Normalized Clip
    (
        ffmpeg.output(
            v,
            a,
            temp_output,
            vcodec="libx264",
            acodec="aac",
            preset="ultrafast",
            # Ensure the container has valid timestamps
            video_track_timescale=30000,
        )
        .global_args("-threads", "1")
        .run(overwrite_output=True, quiet=True)
    )

    return (i, media_type, duration, temp_output)


def create_highlight_video(
    media_data,
    music_path,
    output_name="media/output/highlight_reel.mp4",
    image_duration: int = 5,
    quiet_volume: float = 0.05,
    fade_duration: float = 0.5,
):
    temp_dir = tempfile.mkdtemp()
    intermediate_files = []
    list_file_path = os.path.join(temp_dir, "concat_list.txt")
    clip_durations = []

    try:
        # --- STAGE 1: Normalize clips in parallel ---
        print(f"Stage 1: Normalizing {len(media_data)} clips...")
        args = [(i, item, temp_dir, image_duration) for i, item in enumerate(media_data)]
        results_raw = []

        with Pool(cpu_count()) as pool:
            for result in pool.imap_unordered(process_clip, args):
                results_raw.append(result)
                print(f"  > Processed index {result[0]}")

        results_raw.sort(key=lambda x: x[0])
        for i, media_type, duration, temp_output in results_raw:
            clip_durations.append((media_type, duration))
            intermediate_files.append(temp_output)

        with open(list_file_path, "w") as f:
            for fp in intermediate_files:
                f.write(f"file '{fp}'\n")

        # --- STAGE 2: Flatten the Video (The "Anti-Desync" Step) ---
        # We merge all normalized clips into one temporary video file before mixing audio.
        print("Stage 2: Merging normalized clips...")
        temp_merged_path = os.path.join(temp_dir, "merged_master.mp4")
        (ffmpeg.input(list_file_path, f="concat", safe=0).output(temp_merged_path, c="copy").run(overwrite_output=True, quiet=True))

        # --- STAGE 3: Build Music Timeline ---
        print("Stage 3: Building music timeline with ducking...")
        music_input = ffmpeg.input(music_path, stream_loop=-1).audio
        segments = []
        position = 0
        idx = 0

        while idx < len(clip_durations):
            m_type, dur = clip_durations[idx]

            # Logic to group photos so music doesn't "duck" for every single photo
            group_duration = 0
            is_video = m_type == "video"

            if is_video:
                group_duration = dur
                vol = quiet_volume
                idx += 1
            else:
                # Group consecutive images
                j = idx
                while j < len(clip_durations) and clip_durations[j][0] == "image":
                    group_duration += clip_durations[j][1]
                    j += 1
                vol = 1.0  # Full volume for photos
                idx = j

            seg = music_input.filter("atrim", start=position, end=position + group_duration).filter("asetpts", "PTS-STARTPTS").filter("volume", vol)

            if group_duration > fade_duration * 2:
                seg = seg.filter("afade", t="in", st=0, d=fade_duration)
                seg = seg.filter("afade", t="out", st=group_duration - fade_duration, d=fade_duration)

            segments.append(seg)
            position += group_duration

        music_track = ffmpeg.concat(*segments, v=0, a=1)

        # --- STAGE 4: Final Mix ---
        print("Stage 4: Rendering final output...")
        master_input = ffmpeg.input(temp_merged_path)

        # amix: inputs=2, duration=first (matches length of the video)
        # dropout_transition=0 prevents volume drops at the end
        final_audio = ffmpeg.filter([music_track, master_input.audio], "amix", inputs=2, duration="first", dropout_transition=0)

        os.makedirs(os.path.dirname(output_name), exist_ok=True)
        (
            ffmpeg.output(master_input.video, final_audio, output_name, vcodec="libx264", acodec="aac", pix_fmt="yuv420p", shortest=None).run(
                overwrite_output=True
            )
        )

        print(f"Success! Output: {output_name}")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# --- Example Usage ---
# media_items = [{"path": "vid1.mp4", "type": "video"}, {"path": "img1.jpg", "type": "image"}]
# create_highlight_video(media_items, "background_music.mp3")
