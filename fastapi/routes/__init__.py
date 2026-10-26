from fastapi import APIRouter

from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.predict import router as prediction_router
from routes.predictions import router as predictions_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(prediction_router)
api_router.include_router(predictions_router)
