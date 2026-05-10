import random
import aiofiles
import aiofiles.os
import aiofiles.tempfile
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, Query, File, Depends, APIRouter, HTTPException

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
    tmp_path = None
    try:
        project_id = str(random.randint(0, 10000) - random.randint(0, 999))
        filename = structure_plan.filename

        file_content = await structure_plan.read()

        async with aiofiles.tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as tmp_file:
            await tmp_file.write(file_content)
            tmp_path = tmp_file.name

        uploaded_file = await google_client_async.files.upload(
            file=tmp_path,
            config={
                "mime_type": "application/pdf",
                "display_name": f"project_{project_id}.pdf",
            },
        )

        task = await data_extraction_task.kiq(
            file_uri=uploaded_file.uri, project_id=project_id
        )
        print("Task id: ",task.task_id)

        project = Project(id=project_id, user_email="test@gmail.com", filename=filename, task_id=str(task.task_id))
        print(project)
        db.add(project)
        await db.commit()

        return {
            "status_code": 200,
            "data": "data extraction started",
            "task_id": task.task_id,
            "file_uri": uploaded_file.name,
        }

    # except Exception as e:
    #     logger.error(f"Error: {e}")
    #     raise HTTPException(status_code=500, detail="Something Went Wrong")

    finally:
        if tmp_path:
            try:
                await aiofiles.os.remove(tmp_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to delete temp file {tmp_path}: {cleanup_error}")


@router.get("/api/check_status")
async def check_status(task_id: str = Query(), db: AsyncSession = Depends(get_db)):
    try:
        result_backend = broker.result_backend

        if not result_backend:
            raise HTTPException(status_code=500, detail="Result backend not configured")

        is_ready = await result_backend.is_result_ready(task_id)

        if not is_ready:
            return {
                "task_id": task_id,
                "status": "PENDING",
                "message": "Task is still being processed by the worker.",
            }

        result = await result_backend.get_result(task_id)

        if result.is_err:
             return {
                "task_id": task_id,
                "status": "WORKER_ERROR",
                "message": "The worker encountered an execution error.",
            }

        data = result.return_value

        if data.get("status") == "success":
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "data": data["data"],
            }

        else:
            return {
                "task_id": task_id,
                "status": "ERROR",
                "data": data,
            }

    except Exception as e:
        logger.error(f"Error checking status: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong")
