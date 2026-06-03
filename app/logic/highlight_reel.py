import json
import os
import shutil
import tempfile
import traceback

from dataclasses import asdict
from dataclasses import dataclass
from multiprocessing import Pool
from multiprocessing import cpu_count
from typing import Any

import ffmpeg


@dataclass(frozen=True)
class SyncPolicy:
    fps: int = 30
    width: int = 1920
    height: int = 1080
    sample_rate: int = 44100
    channel_layout: str = "stereo"
    music_base_volume: float = 0.15
    music_offset_seconds: float = 0.0
    enable_async_resample: bool = False
    intermediate_audio_codec: str = "pcm_s16le"
    intermediate_ext: str = "mkv"
    fallback_intermediate_audio_codec: str = "pcm_s16le"
    intermediate_video_preset: str = "veryfast"
    intermediate_video_crf: int = 30
    fallback_intermediate_video_crf: int = 36
    drift_tolerance_ms: float = 40.0
    enable_diagnostics: bool = False
    diagnostics_path: str | None = None
    sidechain_threshold: float = 0.01
    sidechain_ratio: float = 8.0
    sidechain_attack_ms: int = 50
    sidechain_release_ms: int = 1500
    sidechain_knee: float = 2.5
    output_shortest: bool = True
    max_parallel_clips: int = 2


def _probe_duration_seconds(path: str) -> float:
    probe = ffmpeg.probe(path)
    return _probe_duration_from_json(probe)


def _probe_duration_from_json(probe: dict[str, Any]) -> float:
    stream_durations = []
    for stream in probe.get("streams", []):
        raw_duration = stream.get("duration")
        if raw_duration is None:
            continue
        try:
            stream_durations.append(float(raw_duration))
        except (TypeError, ValueError):
            continue

    if stream_durations:
        return max(stream_durations)

    format_duration = probe.get("format", {}).get("duration")
    try:
        return float(format_duration)
    except (TypeError, ValueError):
        return 0.0


def _stream_duration_seconds(probe: dict[str, Any], codec_type: str) -> float:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") != codec_type:
            continue
        raw_duration = stream.get("duration")
        try:
            return float(raw_duration)
        except (TypeError, ValueError):
            continue
    return 0.0


def _decode_ffmpeg_error(ex: ffmpeg.Error) -> dict[str, str]:
    def _safe_decode(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    return {
        "message": str(ex),
        "stdout": _safe_decode(ex.stdout),
        "stderr": _safe_decode(ex.stderr),
    }


def _tail_text(value: str, max_chars: int = 2000) -> str:
    if not value:
        return ""
    return value[-max_chars:]


def process_clip(args):
    i, item, temp_dir, image_duration, policy = args
    path = str(item["path"])
    media_type = item["type"]
    temp_output = os.path.join(temp_dir, f"clip_{i:03d}.{policy.intermediate_ext}")

    try:
        if media_type == "video":
            duration = _probe_duration_seconds(path)
            input_stream = ffmpeg.input(path)
        else:
            duration = float(image_duration)
            input_stream = ffmpeg.input(path, loop=1, t=image_duration)

        # Video Normalization
        v = (
            input_stream.video.filter("scale", policy.width, policy.height, force_original_aspect_ratio="decrease")
            .filter("pad", policy.width, policy.height, "(ow-iw)/2", "(oh-ih)/2")
            .filter("fps", policy.fps)
            .filter("setpts", "PTS-STARTPTS")
            .filter("setsar", 1)
            .filter("format", "yuv420p")
        )

        # Audio normalization for concat-friendly intermediates
        if media_type == "image":
            a = (
                ffmpeg.input(f"anullsrc=cl={policy.channel_layout}:r={policy.sample_rate}", f="lavfi", t=duration)
                .audio.filter("aresample", policy.sample_rate)
                .filter("aformat", sample_fmts="s16", channel_layouts=policy.channel_layout)
                .filter("asetpts", "PTS-STARTPTS")
            )
        else:
            a_resample_kwargs = {"async": 1} if policy.enable_async_resample else {}
            a = (
                input_stream.audio.filter("aresample", policy.sample_rate, **a_resample_kwargs)
                .filter("aformat", sample_fmts="s16", channel_layouts=policy.channel_layout)
                .filter("asetpts", "PTS-STARTPTS")
            )
            if duration > 0:
                a = a.filter("atrim", end=duration)

        try:
            (
                ffmpeg.output(
                    v,
                    a,
                    temp_output,
                    vcodec="libx264",
                    acodec=policy.intermediate_audio_codec,
                    ar=str(policy.sample_rate),
                    ac=2,
                    preset=policy.intermediate_video_preset,
                    crf=policy.intermediate_video_crf,
                )
                .global_args("-threads", "1")
                .run(overwrite_output=True, quiet=True)
            )
            used_fallback = False
        except ffmpeg.Error as primary_ex:
            fallback_output = os.path.join(temp_dir, f"clip_{i:03d}_fallback.{policy.intermediate_ext}")
            try:
                (
                    ffmpeg.output(
                        v,
                        a,
                        fallback_output,
                        vcodec="libx264",
                        acodec=policy.fallback_intermediate_audio_codec,
                        ar=str(policy.sample_rate),
                        ac=2,
                        preset=policy.intermediate_video_preset,
                        crf=policy.fallback_intermediate_video_crf,
                    )
                    .global_args("-threads", "1")
                    .run(overwrite_output=True, quiet=True)
                )
                temp_output = fallback_output
                used_fallback = True
            except ffmpeg.Error as fallback_ex:
                primary_error = _decode_ffmpeg_error(primary_ex)
                fallback_error = _decode_ffmpeg_error(fallback_ex)
                return {
                    "ok": False,
                    "index": i,
                    "path": path,
                    "type": media_type,
                    "error_type": "ffmpeg.Error",
                    "error": "primary and fallback normalization failed",
                    "stdout": primary_error["stdout"],
                    "stderr": primary_error["stderr"],
                    "fallback_stdout": fallback_error["stdout"],
                    "fallback_stderr": fallback_error["stderr"],
                }

        normalized_duration = _probe_duration_seconds(temp_output)
        return {
            "ok": True,
            "index": i,
            "source_duration": duration,
            "normalized_duration": normalized_duration,
            "path": temp_output,
            "type": media_type,
            "used_fallback": used_fallback,
        }
    except ffmpeg.Error as ex:
        ffmpeg_error = _decode_ffmpeg_error(ex)
        return {
            "ok": False,
            "index": i,
            "path": path,
            "type": media_type,
            "error_type": "ffmpeg.Error",
            "error": ffmpeg_error["message"],
            "stdout": ffmpeg_error["stdout"],
            "stderr": ffmpeg_error["stderr"],
        }
    except Exception as ex:
        return {
            "ok": False,
            "index": i,
            "path": path,
            "type": media_type,
            "error_type": type(ex).__name__,
            "error": str(ex),
            "traceback": traceback.format_exc(),
        }


def create_highlight_video(
    media_data,
    music_path,
    output_name="media/output/highlight_reel.mp4",
    image_duration: int = 5,
    music_base_volume: float = 0.15,  # Lowered default for a background feel
    sync_policy: SyncPolicy | None = None,
):
    policy = sync_policy or SyncPolicy(music_base_volume=music_base_volume)

    temp_dir = tempfile.mkdtemp()
    try:
        print("Stage 1: Normalizing clips...")
        args = [(i, item, temp_dir, image_duration, policy) for i, item in enumerate(media_data)]
        worker_count = max(1, min(cpu_count(), policy.max_parallel_clips))
        with Pool(processes=worker_count) as pool:
            results = list(pool.imap_unordered(process_clip, args))

        failed_results = [r for r in results if not r.get("ok", False)]
        if failed_results:
            failed_results.sort(key=lambda x: x["index"])
            examples = failed_results[:3]
            detail_lines = []
            for failure in examples:
                stderr_tail = _tail_text(failure.get("stderr", ""), max_chars=2000)
                stdout_tail = _tail_text(failure.get("stdout", ""), max_chars=500)
                fallback_stderr_tail = _tail_text(failure.get("fallback_stderr", ""), max_chars=2000)
                detail_lines.append(
                    f"index={failure['index']} type={failure.get('type')} path={failure.get('path')} error_type={failure.get('error_type')} error={failure.get('error')} stderr_tail={stderr_tail} stdout_tail={stdout_tail} fallback_stderr_tail={fallback_stderr_tail}"
                )
            raise RuntimeError(f"Failed to normalize {len(failed_results)} clip(s). Examples: {' | '.join(detail_lines)}")

        results = [r for r in results if r.get("ok", False)]
        results.sort(key=lambda x: x["index"])
        clip_paths = [r["path"] for r in results]
        total_duration = sum(r["normalized_duration"] or r["source_duration"] for r in results)
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")

        with open(concat_list_path, "w", encoding="utf-8") as concat_list:
            for clip_path in clip_paths:
                safe_path = clip_path.replace("'", "'\\''")
                concat_list.write(f"file '{safe_path}'\n")

        print("Stage 2: Concatenating...")
        merged_stream = ffmpeg.input(concat_list_path, f="concat", safe=0)
        v_merged = merged_stream.video
        a_merged = merged_stream.audio

        print("Stage 3: Mixing Audio...")
        a_split = a_merged.filter_multi_output("asplit")
        a_for_mix = a_split[0]
        a_for_sidechain = a_split[1]

        # Apply the volume to the music FIRST
        music_input = ffmpeg.input(music_path, stream_loop=-1).audio
        if policy.music_offset_seconds > 0:
            music_input = music_input.filter("atrim", start=policy.music_offset_seconds).filter("asetpts", "PTS-STARTPTS")

        music_resample_kwargs = {"async": 1} if policy.enable_async_resample else {}
        music_audio = (
            music_input.filter("aresample", policy.sample_rate, **music_resample_kwargs)
            .filter("aformat", sample_fmts="fltp", channel_layouts=policy.channel_layout)
            .filter("atrim", duration=total_duration)
            .filter("asetpts", "PTS-STARTPTS")
            .filter("volume", policy.music_base_volume)
        )

        # Sidechaining: The music ducks when people talk
        smart_music = ffmpeg.filter(
            [music_audio, a_for_sidechain],
            "sidechaincompress",
            threshold=policy.sidechain_threshold,
            ratio=policy.sidechain_ratio,
            attack=policy.sidechain_attack_ms,
            release=policy.sidechain_release_ms,
            knee=policy.sidechain_knee,
        )

        # Mixing and Normalizing
        # Program audio is first input, so amix duration=first keeps it as the timing authority.
        final_audio = ffmpeg.filter([a_for_mix, smart_music], "amix", inputs=2, duration="first", dropout_transition=0).filter(
            "loudnorm", I=-16, TP=-1.5
        )

        print("Stage 4: Rendering...")
        os.makedirs(os.path.dirname(output_name), exist_ok=True)
        output_kwargs = {
            "vcodec": "libx264",
            "acodec": "aac",
            "audio_bitrate": "192k",
            "ar": str(policy.sample_rate),
            "pix_fmt": "yuv420p",
            "preset": "medium",
            "movflags": "+faststart",
        }
        if policy.output_shortest:
            output_kwargs["shortest"] = None

        (
            ffmpeg.output(
                v_merged,
                final_audio,
                output_name,
                **output_kwargs,
            ).run(overwrite_output=True)
        )

        if policy.enable_diagnostics:
            output_probe = ffmpeg.probe(output_name)
            video_duration = _stream_duration_seconds(output_probe, "video")
            audio_duration = _stream_duration_seconds(output_probe, "audio")
            if video_duration <= 0:
                video_duration = _probe_duration_from_json(output_probe)
            if audio_duration <= 0:
                audio_duration = _probe_duration_from_json(output_probe)

            drift_ms = abs(video_duration - audio_duration) * 1000.0
            diagnostics_path = policy.diagnostics_path or f"{output_name}.sync_report.json"
            diagnostics = {
                "sync_policy": asdict(policy),
                "total_duration_seconds": total_duration,
                "output": {
                    "video_duration_seconds": video_duration,
                    "audio_duration_seconds": audio_duration,
                    "drift_ms": drift_ms,
                    "drift_tolerance_ms": policy.drift_tolerance_ms,
                    "is_within_tolerance": drift_ms <= policy.drift_tolerance_ms,
                },
                "clips": results,
            }
            with open(diagnostics_path, "w", encoding="utf-8") as report_file:
                json.dump(diagnostics, report_file, indent=2)
            print(f"Sync diagnostics written to: {diagnostics_path}")

        print(f"\n✨ Success! Video saved to: {output_name}")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
