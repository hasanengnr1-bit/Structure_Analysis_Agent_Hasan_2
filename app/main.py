from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from services import get_logger
from routes.agent import agent_routes

logger = get_logger(__name__)
app = FastAPI()

app.include_router(agent_routes.router, prefix="", tags=["Agent"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # any origin
    allow_credentials=True,
    allow_methods=["*"],          # any HTTP method
    allow_headers=["*"],          # any headers
)
app.add_middleware(SessionMiddleware, secret_key="replace-this-with-a-secure-random-string")

@app.get("/health")
async def health():
    try:
        return JSONResponse(content="App running...", status_code=200)
    except Exception as e:
        logger.critical("Error: ", e)
        raise HTTPException(status_code=500, detail="Something went wrong")