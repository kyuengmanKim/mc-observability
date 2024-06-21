from fastapi import APIRouter

router = APIRouter()

return_body = {
    "state": "Success"
}


@router.get("/health", tags=["health_check"],
            responses={200: {"description": "Health check 성공",
                             "content": {"application/json": {"example": return_body}}}})
def health_check():
    return return_body
