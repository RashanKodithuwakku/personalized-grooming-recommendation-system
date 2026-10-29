"""Check local model/template assets required for the real preview pipeline."""
from pathlib import Path
import json
from app.config import BACKEND_DIR, TEMPLATE_DIR

PROJECT_DIR = BACKEND_DIR.parent
MODEL_REPO = PROJECT_DIR / "face-parsing.PyTorch"
WEIGHTS = MODEL_REPO / "res" / "cp" / "79999_iter.pth"
LIBRARY = TEMPLATE_DIR / "library.json"
POINTS = TEMPLATE_DIR / "points_raw.json"

checks = [
    ("BiSeNet repository", MODEL_REPO.is_dir(), str(MODEL_REPO)),
    ("BiSeNet model weights", WEIGHTS.is_file(), str(WEIGHTS)),
    ("Template library metadata", LIBRARY.is_file(), str(LIBRARY)),
    ("Template landmark metadata", POINTS.is_file(), str(POINTS)),
    ("Male template directory", (TEMPLATE_DIR / "male").is_dir(), str(TEMPLATE_DIR / "male")),
    ("Female template directory", (TEMPLATE_DIR / "female").is_dir(), str(TEMPLATE_DIR / "female")),
]
for label, ok, path in checks:
    print(f"{'OK' if ok else 'MISSING'} | {label} | {path}")

missing_templates = []
if LIBRARY.is_file():
    try:
        library = json.loads(LIBRARY.read_text(encoding="utf-8"))
        for name, metadata in library.items():
            gender = metadata.get("gender")
            if gender not in {"male", "female"}:
                continue
            folder = TEMPLATE_DIR / gender
            matches = [folder / f"{name}{ext}" for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")]
            if not any(path.is_file() for path in matches):
                missing_templates.append(name)
    except Exception as exc:
        print(f"ERROR | Could not read library: {exc}")
if missing_templates:
    print(f"MISSING | Template images for {len(missing_templates)} library entries:")
    for name in missing_templates:
        print(f"  - {name}")
else:
    print("OK | All metadata-referenced template images found")

if not all(ok for _, ok, _ in checks[:4]) or missing_templates:
    raise SystemExit(1)
print("Asset check passed. This confirms file presence only, not model inference quality.")
