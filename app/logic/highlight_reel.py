import os
import shutil
import tempfile

from multiprocessing import Pool
from multiprocessing import cpu_count

import ffmpeg


def process_clip(args):
    """
    Stage 1: Normalize clips.
    Standardizes everything to 1080p, 30fps, and Stereo 44.1kHz.
    """
    i, item, temp_dir, image_duration = args
    path = item["path"]
    media_type = item["type"]
    temp_output = os.path.join(temp_dir, f"clip_{i:03d}.mp4")

    if media_type == "video":
        probe = ffmpeg.probe(path)
        duration = float(probe["format"]["duration"])
        input_stream = ffmpeg.input(path)
    else:
        duration = image_duration
        input_stream = ffmpeg.input(path, loop=1, t=image_duration)

    # Video Normalization
    v = (
        input_stream.video.filter("scale", 1920, 1080, force_original_aspect_ratio="decrease")
        .filter("pad", 1920, 1080, "(ow-iw)/2", "(oh-ih)/2")
        .filter("fps", 30)
        .filter("format", "yuv420p")
    )

    # Audio Normalization (Strictly Stereo 44.1k)
    if media_type == "image":
        a = ffmpeg.input("anullsrc=cl=stereo:r=44100", f="lavfi", t=duration).audio
    else:
        try:
            a = (
                input_stream.audio.filter("aresample", 44100)
                .filter("aformat", sample_fmts="fltp", channel_layouts="stereo")
                .filter("atrim", duration=duration)
            )
        except Exception:
            # Fallback if video has no audio track
            a = ffmpeg.input("anullsrc=cl=stereo:r=44100", f="lavfi", t=duration).audio

    (
        ffmpeg.output(v, a, temp_output, vcodec="libx264", acodec="aac", preset="ultrafast")
        .global_args("-threads", "1")
        .run(overwrite_output=True, quiet=True)
    )
    return (i, duration, temp_output)


def create_highlight_video(
    media_data,
    music_path,
    output_name="media/output/highlight_reel.mp4",
    image_duration: int = 5,
    music_base_volume: float = 0.5,
):
    temp_dir = tempfile.mkdtemp()
    try:
        # --- STAGE 1: Parallel Normalization ---
        print("Stage 1: Normalizing clips...")
        args = [(i, item, temp_dir, image_duration) for i, item in enumerate(media_data)]
        results = []
        with Pool(cpu_count()) as pool:
            for res in pool.imap_unordered(process_clip, args):
                results.append(res)
        results.sort(key=lambda x: x[0])

        list_file_path = os.path.join(temp_dir, "concat_list.txt")
        with open(list_file_path, "w") as f:
            for r in results:
                f.write(f"file '{r[2]}'\n")

        # --- STAGE 2: Flatten Timeline ---
        # This merges clips into one file to prevent audio drift during the complex mix.
        print("Stage 2: Merging timeline...")
        temp_merged = os.path.join(temp_dir, "merged_master.mp4")
        (ffmpeg.input(list_file_path, f="concat", safe=0).output(temp_merged, c="copy").run(overwrite_output=True, quiet=True))

        # --- STAGE 3: Natural Sidechain Ducking ---
        print("Stage 3: Mixing audio with natural ducking...")
        video_input = ffmpeg.input(temp_merged)
        music_input = ffmpeg.input(music_path, stream_loop=-1)

        # 1. Prepare Music Stream
        music_audio = music_input.audio.filter("volume", music_base_volume)

        # 2. Apply Sidechain Compression
        # Threshold 0.08: Triggers when speech is present
        # Ratio 4: Subtle, non-robotic reduction
        # Attack 100ms: Smooth fade out
        # Release 1200ms: Prevents 'pumping' during pauses in speech

        smart_music = ffmpeg.filter(
            [music_audio, video_input.audio], "sidechaincompress", threshold=0.08, ratio=4, attack=100, release=1200, knee=2.5
        )

        # 3. Final Mix + Limiter
        # alimiter ensures that adding two loud sounds doesn't cause 'clipping'
        final_audio = ffmpeg.filter([smart_music, video_input.audio], "amix", inputs=2, duration="first", dropout_transition=0).filter(
            "alimiter", limit=0.95
        )

        # --- STAGE 4: Final Render ---
        print("Stage 4: Rendering final video...")
        os.makedirs(os.path.dirname(output_name), exist_ok=True)
        (
            ffmpeg.output(
                video_input.video,
                final_audio,
                output_name,
                vcodec="libx264",
                acodec="aac",
                pix_fmt="yuv420p",
                # Use faster preset for testing; change to 'medium' for final quality
                preset="medium",
            ).run(overwrite_output=True)
        )
        print(f"\n✨ Success! Video saved to: {output_name}")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# --- Example of how to run ---
# if __name__ == "__main__":
#     my_media = [
#         {"path": "vids/intro.mp4", "type": "video"},
#         {"path": "images/photo1.jpg", "type": "image"},
#         {"path": "vids/interview.mp4", "type": "video"},
#     ]
#     create_highlight_video(my_media, "music/background_track.mp3")
