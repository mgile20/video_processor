import io

from pathlib import Path

from dateutil import parser
from PIL import Image
from PIL.ExifTags import TAGS


class ImageProcessor:
    @classmethod
    def _get_exif_data(cls, exif: Image.Exif):
        exif_dict = {}
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            exif_dict[decoded] = value

        return exif_dict

    @classmethod
    def _get_created_dt(cls, exif: Image.Exif):
        try:
            exif_ifd = exif.get_ifd(0x8769)
            dt_str = exif_ifd.get(36867)
            tz_str = exif_ifd.get(36881)

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

        exif_dict = cls._get_exif_data(exif)
        created_dt = cls._get_created_dt(exif)
        thumbnail_bytes = cls._generate_thumbnail(image)

        print(created_dt)
