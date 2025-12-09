# app/main.py
import os
import sys

# Agregar /var/task/packages al sys.path
CURRENT_DIR = os.path.dirname(__file__)
PACKAGES_DIR = os.path.join(CURRENT_DIR, "..", "packages")
if PACKAGES_DIR not in sys.path:
    sys.path.insert(0, PACKAGES_DIR)

from fastapi import FastAPI
from mangum import Mangum

from app.routers.start import router as start_router
from app.routers.document import router as document_router
from app.routers.liveness import router as liveness_router

app = FastAPI(
    title="Kata Authentication Service",
    version="1.0.0",
    description="Autenticación inteligente con OCR y Liveness"
)

app.include_router(start_router, prefix="/kata/auth")
app.include_router(document_router, prefix="/kata/auth")
app.include_router(liveness_router, prefix="/kata/auth")

handler = Mangum(app)