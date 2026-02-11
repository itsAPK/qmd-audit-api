

from uuid import UUID

from sqlalchemy import select
from app.documents.models import Documents


class DocumentsService:
    def __init__(self,session):
        self.session = session
        
    async def create_document(self,name : str,path : str,description : str,type : str):
        document = Documents(name=name,path=path,description=description,type=type)
        self.session.add(document)
        await self.session.commit()
        return document
    
    async def get_documents(self):
         documents = await self.session.execute(select(Documents))
         documents = documents.scalars().all()
         return documents
     
    async def delete_document(self,id : UUID):
        document = await self.session.execute(select(Documents).where(Documents.id == id))
        self.session.delete(document)
        await self.session.commit()
        return document