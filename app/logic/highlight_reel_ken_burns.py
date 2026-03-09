import os
import shutil
import tempfile

import ffmpeg


def create_highlight_video(
    media_data,
    music_path,
    output_name="media/output/highlight_reel_kb.mp4",
    image_duration: int = 5,
):
    temp_dir = tempfile.mkdtemp()
    intermediate_files = []
    list_file_path = os.path.join(temp_dir, "concat_list.txt")

    clip_durations = []
    fade_duration = 0.5
    fps = 30

    print(f"Stage 1: Normalizing {len(media_data)} clips...")

    try:

        for i, item in enumerate(media_data):

            path = item["path"]
            media_type = item["type"]
            faces = item.get("faces", [])

            temp_output = os.path.join(temp_dir, f"clip_{i:03d}.mp4")

            if media_type == "video":
                probe = ffmpeg.probe(path)
                duration = float(probe["format"]["duration"])
                input_stream = ffmpeg.input(path)

            else:
                duration = image_duration
                input_stream = ffmpeg.input(path, loop=1, t=image_duration)

            if media_type == "image":

                if faces:

                    # choose largest detected face
                    face = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = face

                    cx = x + w / 2
                    cy = y + h / 2

                    total_frames = int(duration * fps)

                    v = input_stream.video.filter(
                        "zoompan", z="min(zoom+0.0015,1.2)", x=f"{cx}-(iw/zoom/2)", y=f"{cy}-(ih/zoom/2)", d=total_frames, s="1920x1080", fps=fps
                    ).filter("format", "yuv420p")

                else:
                    total_frames = int(duration * fps)

                    v = input_stream.video.filter(
                        "zoompan", z="min(zoom+0.0015,1.15)", x="iw/2-(iw/zoom/2)", y="ih/2-(ih/zoom/2)", d=total_frames, s="1920x1080", fps=fps
                    ).filter("format", "yuv420p")

            else:

                v = (
                    input_stream.video.filter("scale", 1920, 1080, force_original_aspect_ratio="decrease")
                    .filter("pad", 1920, 1080, "(ow-iw)/2", "(oh-ih)/2")
                    .filter("fps", fps)
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
                ).run(overwrite_output=True, quiet=True)
            )

            clip_durations.append((media_type, duration))
            intermediate_files.append(temp_output)

            print(f"processing {i+1}/{len(media_data)}")

        # -------------------------------------------------------
        # CONCAT FILE
        # -------------------------------------------------------

        with open(list_file_path, "w") as f:
            for file_path in intermediate_files:
                safe_path = file_path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        main_video_audio = ffmpeg.input(list_file_path, f="concat", safe=0)

        print("Stage 2: Building music timeline...")

        music_input = ffmpeg.input(music_path, stream_loop=-1).audio

        segments = []
        position = 0

        i = 0
        while i < len(clip_durations):

            media_type, duration = clip_durations[i]

            if media_type == "video":

                silence = ffmpeg.input(
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                    f="lavfi",
                    t=duration,
                ).audio

                segments.append(silence)

                position += duration
                i += 1
                continue

            group_duration = duration
            j = i + 1

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

        final_audio = ffmpeg.filter(
            [music_track, main_video_audio.audio],
            "amix",
            inputs=2,
            duration="first",
        )

        os.makedirs(os.path.dirname(output_name), exist_ok=True)

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
        shutil.rmtree(temp_dir)
