import pathlib

import pillow_heif

from PIL import Image

pillow_heif.register_heif_opener()


def get_file_name_and_ext(basename: str):
    parts = basename.split(".")

    return parts[0], parts[1]


input_directory = pathlib.Path("input")
for item in input_directory.iterdir():
    if item.is_file():
        file_name, ext = get_file_name_and_ext(item.name)

        img = Image.open(str(item))
        img.save(f"output/{file_name}.png", format("png"))
