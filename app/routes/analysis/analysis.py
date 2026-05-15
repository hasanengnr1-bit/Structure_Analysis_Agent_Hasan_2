from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from services.analysis import run_structural_analysis
from services.auth import get_current_user
from database import get_db, User, Project

router = APIRouter()


@router.get("/api/analysis/get_final_analysis")
async def get_final_analysis(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Project.extracted_data).where(
        Project.id == project_id,
        Project.user_email == user.email,
    )
    result = await db.execute(stmt)
    extracted_data = result.scalar_one_or_none()

    if not extracted_data:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        analysis = run_structural_analysis(extracted_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return {
        "status_code": 200,
        "data": analysis,
    }
