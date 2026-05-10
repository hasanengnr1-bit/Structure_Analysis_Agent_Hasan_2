from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
from taskiq_task.utils import visual_extractor
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from services import get_logger
from core.llm.clients import google_client_async


REDIS_ENDPOINT = os.environ.get("REDIS_ENDPOINT")

# Setup where results are stored
result_backend = RedisAsyncResultBackend(
    redis_url=REDIS_ENDPOINT,
    result_ex_time=1800 # auto-delete results after 1 hour
)

# Setup the Broker
broker = RedisStreamBroker(
    url=REDIS_ENDPOINT
).with_result_backend(result_backend)

logger = get_logger(__file__)

@broker.task
async def data_extraction_task(file_uri: str, project_id:str):
    try:
        file_info = await google_client_async.files.get(name=file_uri)
        
        while file_info.state.name == "PROCESSING":
            await asyncio.sleep(2)
            file_info = await google_client_async.files.get(name=file_uri)
        
        if file_info.state.name == "FAILED":
            return {"error": "Processing failed"}
        
        extracted_data = await visual_extractor(file_uri=file_uri)

        return {
            "status":"success",
            "data":extracted_data,
            "project_id":project_id
        }
    
    except Exception as e:
       logger.critical(f"Error: {e}")
       return {
            "status":"error",
            "data":"Something Went Wrong!"
        } 