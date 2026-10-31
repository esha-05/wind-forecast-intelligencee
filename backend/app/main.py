import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Wind Forecast Intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(router)
