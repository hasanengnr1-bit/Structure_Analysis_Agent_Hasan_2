from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException

from services.utils import get_logger
from database import Project, get_db, User
from services.auth import get_current_user
from services.visualization import build_visualization_payload

router = APIRouter()
logger = get_logger(__name__)

# List all
@router.get("/api/crud/get_all_projects")
async def get_all_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 20,  # Number of records per page
    offset: int = 0,  # Number of records to skip
):
    try:
        query = (
            select(Project.id, Project.filename)
            .where(Project.user_email == user.email)
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
@router.get("/api/crud/get_project")
async def get_project(
    project_id: str = Query(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):  
    try:
        query = (
            select(Project.extracted_data)
            .where(Project.id == project_id)
        )
        result = await db.execute(query)
        result = result.scalar_one_or_none()

        return {"status_code": 200, "data": result}
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")


@router.get("/api/crud/get_project_visualization")
async def get_project_visualization(
    project_id: str = Query(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        query = (
            select(Project.extracted_data)
            .where(Project.id == project_id, Project.user_email == user.email)
        )
        result = await db.execute(query)
        extracted_data = result.scalar_one_or_none()

        if not extracted_data:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "status_code": 200,
            "data": extracted_data.get("visualization") or build_visualization_payload(extracted_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")

# delete project
@router.delete("/api/crud/delete_project")
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
