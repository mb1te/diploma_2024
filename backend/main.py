from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app():
    app = FastAPI(lifespan=lifespan)
    origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    return app



if __name__ == "__main__":
    uvicorn.run(
        "main:create_app",
        host="127.0.0.1",
        port=8080,
        log_level="debug",
        reload=True,
    )
