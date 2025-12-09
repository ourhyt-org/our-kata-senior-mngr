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

# Routers
app.include_router(start_router, prefix="/kata/auth")
app.include_router(document_router, prefix="/kata/auth")
app.include_router(liveness_router, prefix="/kata/auth")

handler = Mangum(app)