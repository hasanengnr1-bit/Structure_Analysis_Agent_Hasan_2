import sys
import json
import asyncio
from anyio import to_thread
from google.genai import types
from google.genai.errors import ClientError

from core.schema import (
    AgentState,
    ShearWallData,
    RoofSystemData,
    WallSystemData,
    PostData,
    FloorSystemData,
    FootingSystemData,
)
from core.llm.prompts import (
    SYS_PROMPT_FLOOR,
    SYS_PROMPT_FOOTING,
    SYS_PROMPT_POST,
    SYS_PROMPT_ROOF,
    SYS_PROMPT_SHEAR_WALL,
    SYS_PROMPT_WALL,
)
from services.utils import get_logger
from core.llm.clients import openai_client_async
from core.utils import fetch_with_id, fetch_with_id_kimi, process_pdf_to_payload


logger = get_logger(__name__)


async def visual_extractor(agent_state: AgentState):
    #try:
        floor_config = types.GenerateContentConfig(
            system_instruction=SYS_PROMPT_FLOOR,
            response_schema=FloorSystemData,
            response_mime_type="application/json",
        )
        footing_config = types.GenerateContentConfig(
            system_instruction=SYS_PROMPT_FOOTING,
            response_schema=FootingSystemData,
            response_mime_type="application/json",
        )
        post_config = types.GenerateContentConfig(
            system_instruction=SYS_PROMPT_POST,
            response_schema=PostData,
            response_mime_type="application/json",
        )
        roof_config = types.GenerateContentConfig(
            system_instruction=SYS_PROMPT_ROOF,
            response_schema=RoofSystemData,
            response_mime_type="application/json",
        )
        shear_wall_config = types.GenerateContentConfig(
            system_instruction=SYS_PROMPT_SHEAR_WALL,
            response_schema=ShearWallData,
            response_mime_type="application/json",
        )
        wall_config = types.GenerateContentConfig(
            system_instruction=SYS_PROMPT_WALL,
            response_schema=WallSystemData,
            response_mime_type="application/json",
        )

        file_uri = agent_state.file_uri
        configs = [
            ("floor", floor_config),
            ("footing", footing_config),
            ("post", post_config),
            ("roof", roof_config),
            ("shear_wall", shear_wall_config),
            ("wall", wall_config)
        ]

        tasks = []

        # Launch tasks with a slight stagger to prevent the 400 error
        for call_id, config in configs:
            tasks.append(fetch_with_id(call_id=call_id, config=config, file_uri=file_uri))
            await asyncio.sleep(1) # <--- Critical: Give the backend 1 second to breathe

        parsed_data = {}

        for task in asyncio.as_completed(tasks):
            call_id, data = await task
            parsed_data[call_id] = data
            logger.info(f"Finished {call_id}")

        return {
            "roof_system": parsed_data["roof"].model_dump(),
            "floor_system": parsed_data["floor"].model_dump(),
            "footing": parsed_data["footing"].model_dump(),
            "post": parsed_data["post"].model_dump(),
            "wall": parsed_data["wall"].model_dump(),
            "shear_wall": parsed_data["shear_wall"].model_dump(),
        }
    
    # except ClientError as e:
    #     logger.error(f"Google API Client Error: {e.message}")
    #     raise Exception("AI Quota exceeded or invalid request.")

    # except Exception as e:
    #     logger.critical("Error: ", e)
    #     raise Exception("Something went Wrong while extracting data from document")

async def visual_extractor_kimi(agent_state: AgentState):
    #try:
        floor_sys_prompt = SYS_PROMPT_FLOOR
        footing_sys_prompt = SYS_PROMPT_FOOTING
        post_sys_prompt = SYS_PROMPT_POST
        roof_sys_prompt = SYS_PROMPT_ROOF
        shear_wall_sys_prompt = SYS_PROMPT_SHEAR_WALL
        wall_sys_prompt = SYS_PROMPT_WALL

        sys_prompts = [
            ("floor", floor_sys_prompt),
            ("footing", footing_sys_prompt),
            ("post", post_sys_prompt),
            ("roof", roof_sys_prompt),
            ("shear_wall", shear_wall_sys_prompt),
            ("wall", wall_sys_prompt)
        ]

        tasks = []
        payload = await to_thread.run_sync(process_pdf_to_payload, agent_state.temp_file_path)
        
        # payload_json = json.dumps(payload)
        # actual_size_bytes = len(payload_json.encode('utf-8'))
        # actual_size_mb = actual_size_bytes / (1024 * 1024)

        # print(f"Fake sys.getsizeof Size: {sys.getsizeof(payload)} bytes")
        # print(f"ACTUAL Network Payload Size: {actual_size_mb:.2f} MB")
        for call_id, sys_prompt in sys_prompts:
            tasks.append(fetch_with_id_kimi(call_id=call_id, system_prompt=sys_prompt, payload=payload))
            await asyncio.sleep(1)

        parsed_data = {}

        for task in asyncio.as_completed(tasks):
            call_id, data = await task
            parsed_data[call_id] = data
            logger.info(f"Finished {call_id}")

        return {
            "roof_system": parsed_data["roof"],
            "floor_system": parsed_data["floor"],
            "footing": parsed_data["footing"],
            "post": parsed_data["post"],
            "wall": parsed_data["wall"],
            "shear_wall": parsed_data["shear_wall"],
        }
    
    # except ClientError as e:
    #     logger.error(f"Google API Client Error: {e.message}")
    #     raise Exception("AI Quota exceeded or invalid request.")

    # except Exception as e:
    #     logger.critical("Error: ", e)
    #     raise Exception("Something went Wrong while extracting data from document")
