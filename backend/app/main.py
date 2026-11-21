from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.config import settings
from app.routers import health


def route_name_as_operation_id(route: APIRoute) -> str:
    """Use the route function name (e.g. `health`) so orval generates `useHealth`."""
    return route.name


app = FastAPI(title="chearip API", generate_unique_id_function=route_name_as_operation_id)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
