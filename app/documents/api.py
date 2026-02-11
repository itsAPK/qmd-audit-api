from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pathlib import Path
from app.core.schemas import Response, ResponseStatus
from app.documents.models import Documents
from app.documents.dependencies import get_document_service
from app.documents.services import DocumentsService
from app.utils.upload import save_file

router = APIRouter()


@router.post("", response_model=Response[Documents])
async def create_document(
    description: str = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    service: DocumentsService = Depends(get_document_service),
):
    ext = Path(file.filename).suffix
    file_path = save_file(
            file.file, filename=file.filename
        )
    document = await service.create_document(
        name=name, path=file_path, description=description, type=ext
    )
    return Response(
        message="Document created successfully",
        data=document,
        success=True,
        status=ResponseStatus.CREATED,
    )


@router.get("", response_model=Response[List[Documents]])
async def get_documents(service: DocumentsService = Depends(get_document_service)):

    docs = await service.get_documents()
    return Response(
        message="Documents retrieved successfully",
        data=docs,
        success=True,
        status=ResponseStatus.SUCCESS,
    )


@router.delete("/{id}", response_model=Response[bool])
async def delete_document(
    id: UUID, service: DocumentsService = Depends(get_document_service)
):
    await service.delete_document(id=id)

    return Response(
        message="Document deleted successfully",
        success=True,
        status=ResponseStatus.SUCCESS,
        data=True,
    )
