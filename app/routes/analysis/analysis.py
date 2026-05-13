import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from services.auth import get_current_user
from database import get_db, User, Project

router = APIRouter()


@router.get("/api/analysis/get_final_analysis")
async def get_final_analysis(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Project.extracted_data).where(Project.id == project_id)
    result = await db.execute(stmt)
    extracted_data = result.scalar_one_or_none()

    if not extracted_data:
        raise HTTPException(status_code=401, detail="Invalid Project id.")
    
    extracted_data_dict = json.loads(extracted_data)

    for component,data in extracted_data_dict.values():
        pass
