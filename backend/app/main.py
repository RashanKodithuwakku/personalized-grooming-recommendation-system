"""FastAPI API for Component 4 preview, top-five lists, feedback and optional AI render."""
import os
import uuid
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import BACKEND_DIR, UPLOAD_DIR, MAX_UPLOAD_BYTES, ALLOWED_IMAGE_EXTENSIONS, STANDARD_SIZE
from app.main_flow import generate_preview, process_feedback, process_advanced_preview_choice
from app.database import init_db, get_all_feedback
from app.mock_component3 import get_ranked_styles
from app.segmentation import load_bisenet_model
from app.hairfastgan import get_status as hairfastgan_status, run_advanced_preview
from app.config import BACKEND_DIR as _BACKEND_DIR
from app.alignment_evaluation import calculate_fixed_alignment_metrics

APP_DIR = Path(__file__).resolve().parent
MODEL_PATH = BACKEND_DIR.parent / "face-parsing.PyTorch" / "res" / "cp" / "79999_iter.pth"
OUTPUT_DIR = UPLOAD_DIR

logger = logging.getLogger("component4.advanced_preview")

app = FastAPI(title="Grooming Recommendation System — Component 4", version="1.1.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
init_db()
try:
    bisenet_model = load_bisenet_model(str(MODEL_PATH))
    model_load_error = None
except Exception as exc:
    bisenet_model = None
    model_load_error = str(exc)


def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "photo.jpg").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Upload a JPG, JPEG, PNG, or WEBP image.")
    content = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB limit.")
    path = UPLOAD_DIR / f"upload_{uuid.uuid4().hex}{suffix}"
    path.write_bytes(content)
    return path


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": bisenet_model is not None,
        "model_error": model_load_error,
        "hairfastgan": hairfastgan_status(),
    }


@app.get("/styles")
def styles(gender: str = Query("male"), style_type: str = Query("hairstyle")):
    if gender not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'.")
    if style_type not in {"hairstyle", "beard"}:
        raise HTTPException(status_code=400, detail="style_type must be 'hairstyle' or 'beard'.")
    ranked = sorted(get_ranked_styles(gender, style_type), key=lambda item: item.get("rank", 999))[:5]
    return {"gender": gender, "style_type": style_type, "styles": ranked, "available_count": len(ranked), "requested_top_n": 5}


@app.post("/generate-preview")
def generate_preview_endpoint(
    file: UploadFile = File(...),
    gender: str = "male",
    style_type: str = "hairstyle",
    current_rank: int = Query(default=1, ge=1),
):
    if gender not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'.")
    if style_type not in {"hairstyle", "beard"}:
        raise HTTPException(status_code=400, detail="style_type must be 'hairstyle' or 'beard'.")
    if bisenet_model is None:
        raise HTTPException(status_code=503, detail=f"BiSeNet model is unavailable: {model_load_error}")
    path = _save_upload(file)
    try:
        result = generate_preview(
            user_id="test_user", user_photo_path=str(path), gender=gender,
            style_type=style_type, current_rank=current_rank, bisenet_model=bisenet_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {exc}") from exc
    if "error" in result:
        # Keep the API response structured so Flutter can show a useful message.
        raise HTTPException(status_code=422, detail=result["error"])
    for key in ("preview_path", "before_after_path"):
        if result.get(key):
            result[key] = "/outputs/" + Path(result[key]).name
    return result


@app.get("/outputs/{filename}")
def get_output(filename: str):
    # Never permit path traversal; only files directly inside test_photos are served.
    if Path(filename).name != filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid output filename.")
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Preview image not found.")
    return FileResponse(path)


@app.post("/alignment-metrics")
def alignment_metrics_endpoint(
    file: UploadFile | None = File(default=None),
    gender: str = Query(default="male"),
):
    """Calculate fixed-reference NME metrics; uploaded image does not change the saved reference landmarks."""
    if gender not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'.")
    try:
        result = calculate_fixed_alignment_metrics(
            gender=gender,
            style_prefix="male_crew_cut" if gender == "male" else "female_crew_cut",
            backend_dir=Path(_BACKEND_DIR),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Fixed alignment metrics failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Alignment metrics failed: {exc}") from exc


class FeedbackRequest(BaseModel):
    user_id: str = Field(default="test_user", min_length=1, max_length=128)
    current_rank: int = Field(ge=1, le=100)
    feedback_value: str
    style_shown: str = Field(min_length=1, max_length=128)
    variant_shown: str = Field(min_length=1, max_length=128)
    gender: str
    style_type: str = "hairstyle"


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    if request.feedback_value.lower() not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="feedback_value must be 'like' or 'dislike'.")
    if request.gender not in {"male", "female"} or request.style_type not in {"hairstyle", "beard"}:
        raise HTTPException(status_code=400, detail="Invalid gender or style_type.")
    return process_feedback(
        user_id=request.user_id, current_rank=request.current_rank,
        feedback_value=request.feedback_value.lower(), style_shown=request.style_shown,
        variant_shown=request.variant_shown, gender=request.gender, style_type=request.style_type,
    )


@app.get("/feedback")
def feedback_history():
    return {"items": get_all_feedback()}


def _resolve_style_reference(style_name: str, gender: str) -> Path:
    """Resolve a requested hairstyle name to an existing template reference image."""
    if gender not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'.")

    # Support both project layouts:
    #   backend/template/<gender>/...   (singular, matching template/library.json)
    #   backend/templates/<gender>/...  (plural, older layout)
    template_dirs = [
        _BACKEND_DIR / "template" / gender,
        _BACKEND_DIR / "templates" / gender,
    ]
    template_dir = next((folder for folder in template_dirs if folder.is_dir()), None)
    if template_dir is None:
        checked = ", ".join(str(folder) for folder in template_dirs)
        raise HTTPException(
            status_code=404,
            detail=f"Template image directory not found. Checked: {checked}",
        )

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = sorted(
        p for p in template_dir.iterdir()
        if p.is_file() and p.suffix.lower() in valid_exts
    )
    if not files:
        raise HTTPException(
            status_code=404,
            detail=f"No hairstyle reference images found in {template_dir}",
        )

    requested = Path(style_name).stem.strip().lower()
    # First try exact template filename, then a style-prefix match.
    exact = [p for p in files if p.stem.lower() == requested]
    matches = exact or [p for p in files if p.stem.lower().startswith(requested + "_") or p.stem.lower() == requested]

    # UI may currently send the placeholder "selected_style"; resolve it to
    # the first ranked hairstyle so the endpoint remains testable before the UI
    # is updated to send the actual selected style name.
    if requested in {"", "selected_style"}:
        ranked = sorted(
            get_ranked_styles(gender, "hairstyle"),
            key=lambda item: item.get("rank", 999),
        )
        if ranked:
            prefix = str(ranked[0].get("style", "")).lower()
            matches = [p for p in files if p.stem.lower().startswith(prefix)]

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No template reference matches style_name='{style_name}' for gender='{gender}'. "
                "Pass a style prefix or exact template filename stem."
            ),
        )
    return matches[0]


class AdvancedPreviewRequest(BaseModel):
    wants_advanced: bool


@app.post("/advanced-preview-choice")
def advanced_preview_choice(request: AdvancedPreviewRequest):
    result = process_advanced_preview_choice(request.wants_advanced)
    if request.wants_advanced:
        result["hairfastgan"] = hairfastgan_status()
    return result


@app.post("/advanced-preview")
def advanced_preview_endpoint(
    file: UploadFile = File(...),
    style_name: str = Query(default="selected_style", min_length=1, max_length=128),
    gender: str = Query(default="male"),
):
    """Generate a HairFastGAN preview and log enough detail to diagnose failures."""
    request_id = uuid.uuid4().hex[:12]
    logger.info(
        "Advanced preview request %s: filename=%r content_type=%r style_name=%r gender=%r",
        request_id, file.filename, file.content_type, style_name, gender,
    )

    status = hairfastgan_status()
    if not status["configured"]:
        logger.error("Advanced preview %s: HairFastGAN not configured: %s", request_id, status)
        raise HTTPException(status_code=503, detail=status["message"])
    if gender not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'.")

    input_path = None
    output_path = None
    reference_path = None
    try:
        input_path = _save_upload(file)
        upload_size = input_path.stat().st_size
        logger.info(
            "Advanced preview %s: saved face image path=%s size=%d bytes",
            request_id, input_path, upload_size,
        )
        if upload_size == 0:
            raise ValueError("Uploaded face image is empty.")

        # Decode-check the upload before sending it to the remote model.
        from PIL import Image
        with Image.open(input_path) as uploaded_image:
            uploaded_image.verify()
        with Image.open(input_path) as uploaded_image:
            logger.info(
                "Advanced preview %s: uploaded image format=%s dimensions=%s mode=%s",
                request_id, uploaded_image.format, uploaded_image.size, uploaded_image.mode,
            )

        reference_path = _resolve_style_reference(style_name, gender)
        if not reference_path.is_file():
            raise FileNotFoundError(f"Hairstyle reference image not found: {reference_path}")
        logger.info(
            "Advanced preview %s: reference image path=%s size=%d bytes",
            request_id, reference_path, reference_path.stat().st_size,
        )

        output_path = OUTPUT_DIR / f"advanced_{uuid.uuid4().hex}.png"
        logger.info("Advanced preview %s: calling HairFastGAN remote/local renderer", request_id)
        result_path = run_advanced_preview(
            input_path=input_path,
            output_path=output_path,
            reference_path=reference_path,
            style_name=style_name,
        )

        result_path = Path(result_path).resolve()
        if not result_path.is_file() or result_path.stat().st_size == 0:
            raise RuntimeError(f"HairFastGAN returned no output image at: {result_path}")

        # Verify the output is a readable image before returning its URL.
        with Image.open(result_path) as generated_image:
            generated_image.verify()

        logger.info(
            "Advanced preview %s: SUCCESS output=%s size=%d bytes",
            request_id, result_path, result_path.stat().st_size,
        )
        return {
            "status": "completed",
            "preview_path": "/outputs/" + result_path.name,
            "engine": "HairFastGAN",
            "style_name": style_name,
            "gender": gender,
            "reference_image": reference_path.name,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Advanced preview %s FAILED: %s: %s",
            request_id, type(exc).__name__, exc,
        )
        logger.error("Advanced preview %s traceback:\n%s", request_id, traceback.format_exc())
        raise HTTPException(
            status_code=502,
            detail=f"Advanced preview failed (request {request_id}): {type(exc).__name__}: {exc}",
        ) from exc
    finally:
        # Keep the uploaded photo for debugging; do not delete user inputs here.
        logger.info("Advanced preview %s: request finished", request_id)
