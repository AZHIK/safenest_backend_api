from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/api/v1/health")
def health_check():
    return JSONResponse(content={"status": "ok"})
