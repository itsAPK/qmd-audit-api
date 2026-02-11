
from app.core.schemas import BaseModel


class Documents(BaseModel,table=True):
    path : str
    name : str
    description : str
    type : str