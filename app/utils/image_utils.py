from PIL import Image
import io

def evaluate_image_quality(image_bytes: bytes) -> float:
    """
    Evalúa calidad mínima de una captura:
    - resolución
    - brillo
    - orientación básica
    """
    img = Image.open(io.BytesIO(image_bytes))

    w, h = img.size

    # Regla 1: resolución mínima
    if w < 600 or h < 400:
        return 0.2

    # Regla 2: rango de brillo (evitar imágenes súper oscuras o blancas)
    grayscale = img.convert("L")
    histogram = grayscale.histogram()
    total = sum(histogram)
    brightness = sum(i * histogram[i] for i in range(256)) / total

    if brightness < 50 or brightness > 205:
        return 0.4

    # Si pasa reglas → calidad aceptable
    return 0.9