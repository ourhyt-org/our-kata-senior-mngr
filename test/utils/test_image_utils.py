
from io import BytesIO

from PIL import Image

from app.utils.image_utils import evaluate_image_quality


class TestEvaluateImageQuality:
    
    def test_evaluate_high_quality_image(self, valid_image_bytes):
        quality = evaluate_image_quality(valid_image_bytes)
        
        assert quality >= 0.9
    
    def test_evaluate_low_resolution_image(self, small_image_bytes):
        quality = evaluate_image_quality(small_image_bytes)
        
        assert quality == 0.2
    
    def test_evaluate_dark_image(self, dark_image_bytes):
        quality = evaluate_image_quality(dark_image_bytes)
        
        assert quality == 0.4
    
    def test_evaluate_bright_image(self, bright_image_bytes):
        quality = evaluate_image_quality(bright_image_bytes)
        
        assert quality <= 0.9
    
    def test_evaluate_medium_brightness_image(self):
        img = Image.new("RGB", (800, 600), color=(128, 128, 128))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality == 0.9
    
    def test_evaluate_exact_minimum_resolution(self):
        img = Image.new("RGB", (600, 400), color=(128, 128, 128))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality >= 0.4
    
    def test_evaluate_just_below_minimum_width(self):
        img = Image.new("RGB", (599, 600), color=(128, 128, 128))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality == 0.2
    
    def test_evaluate_just_below_minimum_height(self):
        img = Image.new("RGB", (800, 399), color=(128, 128, 128))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality == 0.2
    
    def test_evaluate_very_large_image(self):
        img = Image.new("RGB", (4000, 3000), color=(128, 128, 128))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality == 0.9
    
    def test_evaluate_png_format(self):
        img = Image.new("RGB", (800, 600), color=(128, 128, 128))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality >= 0.4
    
    def test_evaluate_image_with_low_brightness(self):
        img = Image.new("RGB", (800, 600), color=(20, 20, 20))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality == 0.4
    
    def test_evaluate_image_with_high_brightness(self):
        img = Image.new("RGB", (800, 600), color=(250, 250, 250))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        
        quality = evaluate_image_quality(image_bytes)
        
        assert quality == 0.4

