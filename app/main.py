import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from services.utils import get_logger
from routes.crud import crud
from routes.agent import agent_routes
from routes.analysis import analysis
from routes.auth import google_sso, local_auth


logger = get_logger(__name__)
app = FastAPI()

app.include_router(agent_routes.router, prefix="", tags=["Agent"])
app.include_router(local_auth.router, prefix="", tags=["Auth"])
app.include_router(google_sso.router, prefix="", tags=["Auth"])
app.include_router(crud.router, prefix="", tags=["CRUD"])
app.include_router(analysis.router, prefix="", tags=["Analysis"])

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

@app.get("/health")
async def health():
    try:
        return JSONResponse(content="App running...", status_code=200)
    except Exception as e:
        logger.critical("Error: ", e)
        raise HTTPException(status_code=500, detail="Something went wrong")
