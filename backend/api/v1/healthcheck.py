from fastapi import APIRouter

router = APIRouter()

@router.get(path="/healthcheck")
def healthcheck():
    return {"status": "ok"}
