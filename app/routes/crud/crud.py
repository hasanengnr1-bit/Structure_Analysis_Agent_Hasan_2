from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException

from database import Project, get_db, User
from services import get_current_user, get_logger

router = APIRouter()
logger = get_logger(__name__)

# List all
@router.get("/api/get_all_projects")
async def get_all_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 20,  # Number of records per page
    offset: int = 0,  # Number of records to skip
):
    try:
        query = (
            select(Project.id, Project.name)
            .where(Project.email == user.email)
            .order_by(Project.start_time.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return {"status_code": 200, "data": result.all()}
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")

# get project
@router.get("/api/get_project")
async def get_project(
    project_id: str = Query(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):  
    try:
        query = (
            select(Project.extracted_data)
            .where(Project.id == project_id)
            .first()
        )
        result = await db.execute(query)
        return {"status_code": 200, "data": result}
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")

# delete project
@router.get("/api/delete_project")
async def delete_projects(
    project_id: str = Query(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        query = (
            delete(Project)
            .where(Project.id == project_id)
        )
        await db.execute(query)
        return {"status_code": 200, "data": "Project Deleted Successfully."}
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")
