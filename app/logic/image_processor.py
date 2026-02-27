import io

from datetime import datetime
from pathlib import Path

from dateutil import parser
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational

from app.models.image_processor_result_model import ImageProcessorResultModel


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

    @classmethod
    def _generate_thumbnail(cls, image: Image.Image, size=(320, 240)) -> bytes | None:
        try:
            buffer = io.BytesIO()

            thumbnail_image = image.copy()
            thumbnail_image.thumbnail(size)
            thumbnail_image.convert("RGB").save(buffer, "JPEG")

            buffer.seek(0)
            return buffer.read()
        except Exception as ex:
            print(ex)

        return None

    @classmethod
    def run(cls, path: Path):
        image = Image.open(path)
        exif = image.getexif()

        return ImageProcessorResultModel(
            exif_data=cls._get_exif_data(exif),
            thumbnail_bytes=cls._generate_thumbnail(image),
            captured_at=cls._get_captured_dt(exif),
        )
