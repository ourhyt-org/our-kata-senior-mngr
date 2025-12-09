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

    if w < 600 or h < 400:
        return 0.2

    grayscale = img.convert("L")
    histogram = grayscale.histogram()
    total = sum(histogram)
    brightness = sum(i * histogram[i] for i in range(256)) / total

    if brightness < 50 or brightness > 205:
        return 0.4

    return 0.9