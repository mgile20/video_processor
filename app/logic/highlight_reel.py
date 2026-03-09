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
        duration = float(probe["format"]["duration"])
        input_stream = ffmpeg.input(path)
    else:
        duration = image_duration
        input_stream = ffmpeg.input(path, loop=1, t=image_duration)

    v = (
        input_stream.video.filter("scale", 1920, 1080, force_original_aspect_ratio="decrease")
        .filter("pad", 1920, 1080, "(ow-iw)/2", "(oh-ih)/2")
        .filter("fps", 30)
        .filter("format", "yuv420p")
    )

    if media_type == "image":
        a = ffmpeg.input(
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            f="lavfi",
            t=duration,
        ).audio
    else:
        try:
            a = input_stream.audio.filter("aresample", 44100).filter("aformat", sample_fmts="fltp", channel_layouts="stereo")
        except Exception:
            a = ffmpeg.input(
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                f="lavfi",
                t=duration,
            ).audio

    (
        ffmpeg.output(
            v,
            a,
            temp_output,
            vcodec="libx264",
            acodec="aac",
            preset="ultrafast",
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

    print(f"Stage 1: Normalizing {len(media_data)} clips...")

    try:
        # -------------------------------------------------------
        # STAGE 1: Normalize clips (Multiprocessing)
        # -------------------------------------------------------

        args = [(i, item, temp_dir, image_duration) for i, item in enumerate(media_data)]

        with Pool(cpu_count()) as pool:
            results = pool.map(process_clip, args)

        results.sort(key=lambda x: x[0])

        for i, media_type, duration, temp_output in results:
            clip_durations.append((media_type, duration))
            intermediate_files.append(temp_output)
            print(f"Processed {i + 1}/{len(media_data)}")

        # -------------------------------------------------------
        # STAGE 2: Build concat list
        # -------------------------------------------------------

        with open(list_file_path, "w") as f:
            for file_path in intermediate_files:
                safe_path = file_path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        main_video_audio = ffmpeg.input(list_file_path, f="concat", safe=0)

        print("Stage 2: Building music timeline with ducking...")

        music_input = ffmpeg.input(music_path, stream_loop=-1).audio

        segments = []
        position = 0
        i = 0

        while i < len(clip_durations):
            media_type, duration = clip_durations[i]

            if media_type == "video":
                seg = (
                    music_input.filter("atrim", start=position, end=position + duration)
                    .filter("asetpts", "PTS-STARTPTS")
                    .filter("volume", quiet_volume)
                )

                if duration > fade_duration * 2:
                    seg = seg.filter("afade", t="in", st=0, d=fade_duration)
                    seg = seg.filter("afade", t="out", st=duration - fade_duration, d=fade_duration)

                segments.append(seg)

                position += duration
                i += 1
                continue

            # ----- GROUP CONSECUTIVE PHOTOS -----

            group_duration = 0
            j = i

            while j < len(clip_durations) and clip_durations[j][0] == "image":
                group_duration += clip_durations[j][1]
                j += 1

            seg = music_input.filter("atrim", start=position, end=position + group_duration).filter("asetpts", "PTS-STARTPTS")

            if group_duration > fade_duration * 2:
                seg = seg.filter("afade", t="in", st=0, d=fade_duration)
                seg = seg.filter("afade", t="out", st=group_duration - fade_duration, d=fade_duration)

            segments.append(seg)

            position += group_duration
            i = j

        music_track = ffmpeg.concat(*segments, v=0, a=1)

        # -------------------------------------------------------
        # STAGE 3: Final Audio Mix
        # -------------------------------------------------------

        final_audio = ffmpeg.filter(
            [music_track, main_video_audio.audio],
            "amix",
            inputs=2,
            duration="first",
        )

        os.makedirs(os.path.dirname(output_name), exist_ok=True)

        print("Stage 3: Rendering final video...")

        (
            ffmpeg.output(
                main_video_audio.video,
                final_audio,
                output_name,
                vcodec="libx264",
                acodec="aac",
                pix_fmt="yuv420p",
            ).run(overwrite_output=True)
        )

        print(f"Success! Output: {output_name}")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
