import os
import shutil
import tempfile

from multiprocessing import Pool
from multiprocessing import cpu_count

import ffmpeg


def process_clip(args):
    i, item, temp_dir, image_duration = args
    path = item["path"]
    media_type = item["type"]
    temp_output = os.path.join(temp_dir, f"clip_{i:03d}.mp4")

    if media_type == "video":
        probe = ffmpeg.probe(path)
        duration = float(probe["format"].get("duration", 0))
        input_stream = ffmpeg.input(path)
    else:
        duration = image_duration
        input_stream = ffmpeg.input(path, loop=1, t=image_duration)

    # Video Normalization
    v = (
        input_stream.video.filter("scale", 1920, 1080, force_original_aspect_ratio="decrease")
        .filter("pad", 1920, 1080, "(ow-iw)/2", "(oh-ih)/2")
        .filter("fps", 30)
        .filter("setsar", 1)  # Force square pixels to fix the Concat error
        .filter("format", "yuv420p")
    )

    # Audio Normalization
    if media_type == "image":
        a = ffmpeg.input("anullsrc=cl=stereo:r=44100", f="lavfi", t=duration).audio
    else:
        try:
            a = (
                input_stream.audio.filter("aresample", 44100, **{"async": 1})
                .filter("aformat", sample_fmts="fltp", channel_layouts="stereo")
                .filter("atrim", duration=duration)
            )
        except Exception:
            a = ffmpeg.input("anullsrc=cl=stereo:r=44100", f="lavfi", t=duration).audio

    # Changed acodec to 'ac3' for TV compatibility
    (
        ffmpeg.output(v, a, temp_output, vcodec="libx264", acodec="ac3", preset="ultrafast")
        .global_args("-threads", "1")
        .run(overwrite_output=True, quiet=True)
    )
    return (i, duration, temp_output)


def create_highlight_video(
    media_data,
    music_path,
    output_name="media/output/highlight_reel.mp4",
    image_duration: int = 5,
    music_base_volume: float = 0.2,
):
    temp_dir = tempfile.mkdtemp()
    try:
        print("Stage 1: Normalizing clips..")
        args = [(i, item, temp_dir, image_duration) for i, item in enumerate(media_data)]
        with Pool(cpu_count()) as pool:
            results = list(pool.imap_unordered(process_clip, args))
        results.sort(key=lambda x: x[0])
        clip_paths = [r[2] for r in results]

        print("Stage 2: Concatenating via filter graph...")
        input_clips = [ffmpeg.input(p) for p in clip_paths]
        concat_streams = []
        for c in input_clips:
            concat_streams.append(c.video)
            concat_streams.append(c.audio)

        joined = ffmpeg.concat(*concat_streams, v=1, a=1).node
        v_merged = joined[0]
        a_merged = joined[1]

        print("Stage 3: Splitting and Mixing Audio...")
        a_split = a_merged.filter_multi_output("asplit")
        a_for_sidechain = a_split[0]
        a_for_mix = a_split[1]

        music_audio = ffmpeg.input(music_path, stream_loop=-1).audio.filter("volume", music_base_volume)

        smart_music = ffmpeg.filter(
            [music_audio, a_for_sidechain],
            "sidechaincompress",
            threshold=0.015,  # Lower threshold = more sensitive to quiet speech
            ratio=4,  # Lower ratio = gentler volume reduction (less "aggressive")
            attack=50,  # Faster attack = music ducks quicker when speech starts
            release=2000,  # Longer release = music fades back in slowly/naturally
            knee=2.5,  # Softer knee = smoother transition into compression
        )

        final_audio = ffmpeg.filter([smart_music, a_for_mix], "amix", inputs=2, duration="first").filter("loudnorm", I=-16, LRA=11, TP=-1.5)

        print("Stage 4: Rendering...")
        os.makedirs(os.path.dirname(output_name), exist_ok=True)

        # Final render using AC3 and a standard bitrate
        (
            ffmpeg.output(
                v_merged,
                final_audio,
                output_name,
                vcodec="libx264",
                acodec="libmp3lame",  # Switched to MP3
                audio_bitrate="192k",
                ar="44100",  # Standard MP3 sample rate
                pix_fmt="yuv420p",
                preset="medium",
                movflags="+faststart",
            ).run(overwrite_output=True)
        )
        print(f"\n✨ Success! Video saved to: {output_name}")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
