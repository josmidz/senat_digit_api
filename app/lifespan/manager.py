from contextlib import asynccontextmanager
from app.lifespan.shutdown import shutdown_application
from app.lifespan.startup import initialize_application
from fastapi import FastAPI
# from .startup import initialize_application
# from .shutdown import shutdown_application


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Main lifespan context manager"""
    resources = await initialize_application()
    
    try:
        yield resources
    finally:
        await shutdown_application(resources)