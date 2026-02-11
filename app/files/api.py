import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
router = APIRouter()

@router.get("/download/{bucket:path}")
async def download_file(bucket: str):
        # Calculate the full file path
        file_path = os.path.join(bucket)
        
        # Check if file exists
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail={
                "message": "File not found",
                "success": False,
                "status": 404,
                "data": None
            })
        
        return FileResponse(file_path)