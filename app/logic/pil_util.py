from pathlib import Path

import numpy as np
import pillow_heif

from PIL import Image

pillow_heif.register_heif_opener()


def to_np_array(path: Path | str):
    img = Image.open(path)
    return np.array(img.convert("RGB"))
