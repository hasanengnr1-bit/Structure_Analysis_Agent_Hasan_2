from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import Project, get_db


router =APIRouter()

# List all
@router.get("/api/get_all_projects")
async def get_all_projects(db: AsyncSession = Depends(get_db)):
    projects = await db.query(Project).filter(email="")
    raise NotImplementedError


# get project
@router.get("/api/get_project")
async def get_project(project_id: str = Query(), db: AsyncSession = Depends(get_db)):
    raise NotImplementedError


# get project
@router.get("/api/delete_project")
async def delete_projects(project_id: str = Query(), db: AsyncSession = Depends(get_db)):
    raise NotImplementedError

