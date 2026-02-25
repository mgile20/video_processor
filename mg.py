import json

from bson import ObjectId

from app.models.media_item_model import MediaItemModel

item = {"_id": "699f3a932fa8d8ca7c3c3c54", "name": "asdf"}
item_s = json.dumps(item)
model = MediaItemModel.model_validate_json(item_s)
print(model.model_dump_json())
