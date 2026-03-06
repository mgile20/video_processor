import io
import os

from datetime import datetime
from pathlib import Path
from typing import List

import cv2
import cv2.saliency
import numpy as np
import pillow_heif

from dateutil import parser
from PIL import Image
from PIL import ImageOps
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational

from app.logic import cv2_util
from app.models.image_processor_result_model import ImageProcessorResultModel

pillow_heif.register_heif_opener()


class ImageProcessor:
    @classmethod
    def _get_exif_data(cls, exif: Image.Exif):
        exif_dict = {}
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            if isinstance(value, IFDRational):
                exif_dict[decoded] = float(value)
            elif isinstance(value, bytes):
                continue
            else:
                exif_dict[decoded] = value

        return exif_dict

    @classmethod
    def _get_captured_dt(cls, exif: Image.Exif) -> datetime | None:
        try:
            exif_ifd = exif.get_ifd(0x8769)
            dt_str = exif_ifd.get(36867)
            tz_str = exif_ifd.get(36881)

            if not exif_ifd or not dt_str or not tz_str:
                return None

            full_str = f"{dt_str}{tz_str}" if tz_str else dt_str
            normalized = full_str.replace(":", "-", 2)

            return parser.parse(normalized)
        except Exception as ex:
            print(ex)

        return None

    # @classmethod
    # def _generate_thumbnail(cls, image: Image.Image, object_center: tuple, size=(320, 240)) -> bytes | None:
    #     try:
    #         buffer = io.BytesIO()

    #         image_copy = image.copy()
    #         image_copy.thumbnail(size)
    #         image_copy.convert("RGB").save(buffer, "JPEG")

    #         buffer.seek(0)

    #         return buffer.read()
    #     except Exception as ex:
    #         print(ex)

    #     return None

    @classmethod
    def _generate_thumbnail(cls, image: Image.Image, targets: List[dict] = [], size=(320, 240)):
        img_w, img_h = image.size
        target_w, target_h = size

        # 2. Determine Focus Point (Center of all detected faces)
        if targets:
            # Average the centers of all detected bounding boxes
            avg_x = sum((t["box"][0] + t["box"][2]) / 2 for t in targets) / len(targets)
            avg_y = sum((t["box"][1] + t["box"][3]) / 2 for t in targets) / len(targets)
        else:
            # Fallback to image center
            avg_x, avg_y = img_w / 2, img_h / 2

        # 3. Calculate Scale (Resize to cover the target dimensions)
        # We use 'cover' logic so no white bars appear, then crop the excess
        scale = max(target_w / img_w, target_h / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 4. Calculate Crop Coordinates based on scaled focus point
        focus_x, focus_y = avg_x * scale, avg_y * scale

        left = max(0, min(focus_x - target_w / 2, new_w - target_w))
        top = max(0, min(focus_y - target_h / 2, new_h - target_h))
        right = left + target_w
        bottom = top + target_h

        cropped = resized.crop((left, top, right, bottom))

        buffer = io.BytesIO()
        cropped.convert("RGB").save(buffer, "JPEG")
        buffer.seek(0)
        return buffer.read()

    @classmethod
    def _process_faces(cls, image: Image.Image):
        np_array = np.array(image.convert("RGB"))
        cv_img = cv2.cvtColor(np_array, cv2.COLOR_RGB2BGR)
        return cv2_util.detect_face_dnn(cv_img)

    @classmethod
    def run(cls, path: Path):
        image = Image.open(path)
        exif = image.getexif()

        transposed = ImageOps.exif_transpose(image)
        targets, all_found = cls._process_faces(transposed)

        return ImageProcessorResultModel(
            exif_data=cls._get_exif_data(exif),
            thumbnail_bytes=cls._generate_thumbnail(transposed, targets),
            captured_at=cls._get_captured_dt(exif),
            face_data_targets=cv2_util.sanitize_np_types(targets),
            face_data_all=cv2_util.sanitize_np_types(all_found),
        )
