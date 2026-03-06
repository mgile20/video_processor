from pathlib import Path
from typing import Self

from pydantic import BaseModel

from app.common import util


class PathsModel(BaseModel):
    project_root: Path
    model_proto: Path
    model_weight: Path

    @classmethod
    def default(cls) -> Self:
        project_root = Path(util.get_project_root())
        return PathsModel(
            project_root=project_root,
            model_proto=project_root.joinpath("ml_models/deploy.prototxt"),
            model_weight=project_root.joinpath("ml_models/res10_300x300_ssd_iter_140000.caffemodel"),
        )
