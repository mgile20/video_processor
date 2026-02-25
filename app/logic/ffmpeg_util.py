import json
import subprocess


def identify_file(file_path):
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        file_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        data = json.loads(result.stdout)
        print(json.dumps(indent=4))
        return data["format"]["format_long_name"]
    else:
        return "Unknown/Error"
