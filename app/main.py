import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from services.utils import get_logger
from database import init_db
from routes.auth import local_auth


logger = get_logger(__name__)
app = FastAPI()

app.include_router(local_auth.router, prefix="", tags=["Auth"])

try:
    from routes.auth import google_sso

    app.include_router(google_sso.router, prefix="", tags=["Auth"])
except Exception as e:
    logger.warning(f"Google SSO routes disabled: {e}")

try:
    from routes.crud import crud

    app.include_router(crud.router, prefix="", tags=["CRUD"])
except Exception as e:
    logger.warning(f"CRUD routes disabled: {e}")

try:
    from routes.analysis import analysis

    app.include_router(analysis.router, prefix="", tags=["Analysis"])
except Exception as e:
    logger.warning(f"Analysis routes disabled: {e}")

try:
    from routes.agent import agent_routes

    app.include_router(agent_routes.router, prefix="", tags=["Agent"])
except Exception as e:
    logger.warning(f"Agent routes disabled: {e}")

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=os.getenv("FRONTEND_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1)(:\d+)?"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key="replace-this-with-a-secure-random-string")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/health")
async def health():
    try:
        return JSONResponse(content="App running...", status_code=200)
    except Exception as e:
        logger.critical("Error: ", e)
        raise HTTPException(status_code=500, detail="Something went wrong")
