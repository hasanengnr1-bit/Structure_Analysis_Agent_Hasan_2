import random
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, Form, File, Depends, APIRouter, HTTPException

from database import get_db
from services import get_logger
from database import User, Project
from core.llm.clients import google_client_async
from taskiq_task import data_extraction_task, broker

router = APIRouter()

logger = get_logger(__name__)


@router.post("/api/start_agent")
async def start_agent(
    structure_plan: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    try:
        project_id = random.randint(0, 10000) - random.randint(0, 999)
        filename = structure_plan.filename

        uploaded_file = await google_client_async.files.upload(
            file=structure_plan.file,
            config={
                "mime_type": "application/pdf",
                "display_name": f"project_{project_id}.pdf",
            },
        )

        task = await data_extraction_task.kiq(
            file_uri=uploaded_file.uri, project_id=project_id
        )

        project = Project(id=project_id, user_email="test@gmail.com", filename=filename)
        await db.add(project)
        await db.commit()

        return {
            "status_code": 200,
            "data": "data extraction started",
            "task_id": task.task_id,
            "file_uri": uploaded_file.name,
        }

    except Exception as e:
        logger.critical(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong")


@router.get("/api/check_status")
async def check_status(task_id: str = Form(...), db: AsyncSession = Depends(get_db)):
    try:
        result_backend = broker.result_backend

        if not result_backend:
            raise HTTPException(status_code=500, detail="Result backend not configured")

        is_ready = await result_backend.is_ready(task_id)

        if not is_ready:
            return {
                "task_id": task_id,
                "status": "PENDING",
                "message": "Task is still being processed by the worker.",
            }

        result = await result_backend.get_result(task_id)

        if result.return_value["status"] == "success":
            stmt = (
                update(Project)
                .where(Project.id == result.return_value["project_id"])
                .values(extracted_data=result.return_value["extracted_data"])
            )
            await db.execute(stmt)
            await db.commit()

            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "data": result.return_value["extracted_data"],
            }

        else:
            return {
                "task_id": task_id,
                "status": "ERROR",
                "data": result.return_value,
            }

    except Exception as e:
        logger.critical(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong")
