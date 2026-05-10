import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

USERNAME = os.environ['DB_USER']
PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']
HOST = os.environ['DB_HOST']
PORT = os.environ['DB_PORT']

SQLALCHEMY_DATABASE_URL = f"mysql+aiomysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"charset": "utf8mb4"},
    echo=False,
)

local_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False, # Recommended for async to avoid unexpected lazy loads
)

Base = declarative_base()

async def get_db():
    async with local_session() as db:
        try:
            yield db
        finally:
            await db.close()