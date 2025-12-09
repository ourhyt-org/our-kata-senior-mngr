# app/services/liveness_service.py
from dataclasses import dataclass
from typing import Optional
from io import BytesIO

from PIL import Image, ImageChops


@dataclass
class LivenessResult:
    auth_id: str
    challenge_type: str
    liveness_score: float
    passed: bool
    reason: Optional[str]
    next_step: str


def _prepare_image(image_bytes: bytes) -> Image.Image:
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("L")
    img = img.resize((64, 64))
    return img


def evaluate_liveness(
    auth_id: str,
    challenge_type: str,
    frame1_bytes: bytes,
    frame2_bytes: bytes,
    threshold: float = 0.08,
) -> LivenessResult:
    try:
        img1 = _prepare_image(frame1_bytes)
        img2 = _prepare_image(frame2_bytes)
    except Exception as e:
        raise ValueError(f"Alguno de los frames no es una imagen válida: {str(e)}")

    diff = ImageChops.difference(img1, img2)

    histogram = diff.histogram()
    total_pixels = 64 * 64
    sum_diff = 0

    for value, count in enumerate(histogram):
        sum_diff += value * count

    avg_diff = sum_diff / float(total_pixels)

    score = avg_diff / 255.0

    if score < threshold:
        passed = False
        reason = (
            f"Cambio muy bajo entre frames (score={score:.3f}). "
            "Podría ser una foto fija o video sin interacción."
        )
        next_step = "REJECTED"
    else:
        passed = True
        reason = None
        next_step = "COMPLETED"

    print(
        f"[LIVENESS] authId={auth_id} challenge={challenge_type} "
        f"score={score:.3f} passed={passed}"
    )

    return LivenessResult(
        auth_id=auth_id,
        challenge_type=challenge_type,
        liveness_score=score,
        passed=passed,
        reason=reason,
        next_step=next_step,
    )