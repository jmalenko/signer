from __future__ import annotations

from pathlib import Path

from PIL import Image


def build_default_output_path(document_path: str | Path, preferred_directory: str | None = None) -> Path:
    doc = Path(document_path)
    directory = Path(preferred_directory) if preferred_directory else doc.parent
    base = f"{doc.stem}-signed"
    candidate = directory / f"{base}.jpg"

    if not candidate.exists():
        return candidate

    i = 1
    while True:
        candidate = directory / f"{base}-{i}.jpg"
        if not candidate.exists():
            return candidate
        i += 1


def composite_signature_to_jpg(
    document_image: Image.Image,
    signature_image: Image.Image,
    signature_x: float,
    signature_y: float,
    signature_scale: float,
    output_path: str | Path,
    jpg_quality: int = 95,
) -> None:
    doc_rgba = document_image.convert("RGBA")

    target_w = max(1, int(round(signature_image.width * signature_scale)))
    target_h = max(1, int(round(signature_image.height * signature_scale)))
    sig = signature_image.convert("RGBA").resize((target_w, target_h), Image.Resampling.LANCZOS)

    x = int(round(signature_x))
    y = int(round(signature_y))
    doc_rgba.alpha_composite(sig, dest=(x, y))

    out_rgb = doc_rgba.convert("RGB")
    out_rgb.save(str(output_path), format="JPEG", quality=jpg_quality, optimize=True)
