from datetime import datetime
import json
from typing import Optional, Union
import uuid
from uuid import UUID




def serialize_for_json(obj):
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(serialize_for_json(item) for item in obj)
    return obj  # fallback





class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    
    
    
def to_naive(dt: Optional[Union[str, datetime]]) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo:
        return dt.astimezone(tz=None).replace(tzinfo=None)
    return dt

