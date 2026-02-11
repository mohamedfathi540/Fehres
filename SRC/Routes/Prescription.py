from fastapi import APIRouter, UploadFile, status, Request
from fastapi.responses import JSONResponse
import os
import tempfile
import logging
from Helpers.Config import get_settings, settings
from Controllers.PrescriptionController import PrescriptionController
from Models.enums.ResponsEnums import ResponseSignal

logger = logging.getLogger("uvicorn.error")

prescription_router = APIRouter(
    prefix="/api/v1/prescription",
    tags=["api_v1", "prescription"],
)

# Allowed image types for prescription uploads
ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
]


@prescription_router.post("/analyze")
async def analyze_prescription(request: Request, file: UploadFile):
    """
    Upload a prescription image, perform OCR, extract medicine names,
    and search for active ingredients + images for each medicine.
    """
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value,
                "error": f"Unsupported file type: {file.content_type}. "
                         f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
            },
        )

    # Save uploaded file to a temp location
    suffix = os.path.splitext(file.filename or "upload.jpg")[-1]
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await file.read()
        tmp_file.write(content)
        tmp_file.flush()
        tmp_file.close()

        # Run analysis pipeline
        controller = PrescriptionController()
        result = await controller.analyze_prescription(
            file_path=tmp_file.name,
            genration_client=request.app.genration_client,
        )

        medicines = result.get("medicines", [])
        ocr_text = result.get("ocr_text", "")

        if not medicines:
            signal = ResponseSignal.PRESCRIPTION_NO_MEDICINES_FOUND.value
        else:
            signal = ResponseSignal.PRESCRIPTION_ANALYZED.value

        return JSONResponse(
            content={
                "signal": signal,
                "ocr_text": ocr_text,
                "medicines": medicines,
            }
        )

    except Exception as e:
        logger.error("Error analyzing prescription: %s", e, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.PRESCRIPTION_OCR_FAILED.value,
                "error": str(e),
            },
        )

    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_file.name)
        except OSError:
            pass
