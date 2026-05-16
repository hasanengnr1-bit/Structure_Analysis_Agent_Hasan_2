import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URL")
    if explicit_url:
        return explicit_url

    postgres_keys = ["DB_USER", "DB_PASSWORD", "DB_NAME", "DB_HOST", "DB_PORT"]
    if all(os.getenv(key) for key in postgres_keys):
        username = os.environ["DB_USER"]
        password = os.environ["DB_PASSWORD"]
        db_name = os.environ["DB_NAME"]
        host = os.environ["DB_HOST"]
        port = os.environ["DB_PORT"]
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{db_name}"

    return "sqlite+aiosqlite:///./structure_agent_local.db"


def _engine_options(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"echo": False}
    return {"echo": False, "pool_size": 10, "max_overflow": 20}


SQLALCHEMY_DATABASE_URL = _build_database_url()

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    **_engine_options(SQLALCHEMY_DATABASE_URL),
)

local_async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False, # Recommended for async to avoid unexpected lazy loads
)


async def init_db():
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with local_async_session() as db:
        try:
            yield db
        finally:
            await db.close()
