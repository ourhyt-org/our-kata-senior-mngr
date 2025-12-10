
from dataclasses import dataclass
from typing import Optional, Tuple, List
from io import BytesIO
import re
import os 

from PIL import Image

import boto3

s3 = boto3.client("s3")

DOC_IMAGE_BUCKET = os.getenv("DOC_IMAGE_BUCKET", "ourhyt-assets")
DOC_IMAGE_PREFIX = os.getenv("DOC_IMAGE_PREFIX", "idcard/")

from app.services.ocr_service import extract_text_from_image


@dataclass
class DocumentEvaluationResult:
    auth_id: str
    quality_score: float
    document_status: str
    reason: Optional[str]
    next_step: str
    ocr_doc_number: Optional[str]
    doc_match: bool
    fraud_suspected: bool


def _evaluate_image_quality(img: Image.Image) -> Tuple[float, List[str]]:
    width, height = img.size
    fmt = (img.format or "").upper()

    reasons: List[str] = []
    quality = 1.0

    if fmt not in ("JPEG", "JPG", "PNG", "WEBP", "HEIC"):
        reasons.append(f"Formato no permitido: {fmt}")
        quality -= 0.3

    if width < 600 or height < 400:
        reasons.append(f"Resolución muy baja: {width}x{height}")
        quality -= 0.4

    aspect = height / width if width else 0
    if aspect < 0.6 or aspect > 2.0:
        reasons.append("Relación de aspecto extraña, intenta centrar mejor la cédula")
        quality -= 0.2

    quality = max(0.0, min(1.0, quality))
    return quality, reasons

def _store_document_image_in_s3(
    jwt_doc_number: str,
    image_bytes: bytes,
    img: Image.Image,
) -> str:
    ext = (img.format or "JPEG").lower()
    if ext not in ("jpeg", "jpg", "png", "webp", "heic"):
        ext = "jpg"

    key = f"{DOC_IMAGE_PREFIX}{jwt_doc_number}.{ext}"

    content_type = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
    }.get(ext, "image/jpeg")

    s3.put_object(
        Bucket=DOC_IMAGE_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType=content_type,
    )

    print(f"[DOCUMENT] Imagen de referencia guardada en s3://{DOC_IMAGE_BUCKET}/{key}")
    return key


def _extract_doc_number_from_text(text: str) -> Optional[str]:
    cleaned = text.replace("\n", " ").replace("\r", " ")

    pattern_with_separators = r"(\d[\d\.\-\s]{6,20}\d)"
    matches = re.findall(pattern_with_separators, cleaned)

    candidates = []

    for m in matches:
        normalized = re.sub(r"[^\d]", "", m)

        if 8 <= len(normalized) <= 12:
            candidates.append(normalized)

    if not candidates:
        matches = re.findall(r"\b\d{8,12}\b", cleaned)
        candidates.extend(matches)

    if not candidates:
        return None

    candidates_sorted = sorted(candidates, key=len, reverse=True)

    return candidates_sorted[0]


def evaluate_document(
    auth_id: str,
    jwt_doc_number: str,
    image_bytes: bytes,
) -> DocumentEvaluationResult:
    try:
        img = Image.open(BytesIO(image_bytes))
        img.verify()
    except Exception:
        raise ValueError("El archivo no es una imagen válida")

    img = Image.open(BytesIO(image_bytes))

    quality, reasons = _evaluate_image_quality(img)

    try:
        ocr_text = extract_text_from_image(image_bytes)
        print("[OCR] Texto extraído (truncado):", ocr_text[:300])
    except Exception as e:
        reasons.append(f"Error en OCR Textract: {str(e)}")
        ocr_text = ""

    ocr_doc_number = _extract_doc_number_from_text(ocr_text) if ocr_text else None

    doc_match = False
    fraud_suspected = False

    if ocr_doc_number:
        doc_match = str(ocr_doc_number) == str(jwt_doc_number)
        if not doc_match:
            fraud_suspected = True
            reasons.append(
                f"Número de documento no coincide: OCR={ocr_doc_number}, JWT={jwt_doc_number}"
            )
    else:
        reasons.append("No se pudo extraer un número de documento por OCR")

    if fraud_suspected:
        status = "MISMATCH"
        next_step = "REJECTED"
    else:
        if quality < 0.6:
            status = "RETAKE"
            next_step = "RETAKE_DOCUMENT"
        else:
            status = "OK"
            next_step = "LIVENESS"

    reason_text = "; ".join(reasons) if reasons else None

    document_ref_key: Optional[str] = None
    if not fraud_suspected and status == "OK":
        try:
            document_ref_key = _store_document_image_in_s3(
                jwt_doc_number=jwt_doc_number,
                image_bytes=image_bytes,
                img=img,
            )
        except Exception as e:
            print(f"[DOCUMENT] Error guardando imagen de referencia en S3: {e}")

    return DocumentEvaluationResult(
        auth_id=auth_id,
        quality_score=quality,
        document_status=status,
        reason=reason_text,
        next_step=next_step,
        ocr_doc_number=ocr_doc_number,
        doc_match=doc_match,
        fraud_suspected=fraud_suspected,
    )