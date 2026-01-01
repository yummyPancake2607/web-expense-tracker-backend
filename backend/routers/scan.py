from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.vision import extract_receipt_data
from google.api_core.exceptions import PermissionDenied

router = APIRouter(
    prefix="/scan",
    tags=["scan"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload")
async def scan_receipt(file: UploadFile = File(...)):
    """
    Upload a receipt image and extract data.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    contents = await file.read()
    
    try:
        data = extract_receipt_data(contents)
        return data
    except PermissionDenied as e:
        print(f"Billing Error: {e}")
        raise HTTPException(status_code=402, detail="Google Cloud Billing is disabled. Please enable it in the Google Cloud Console.")
    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
