from typing import Literal

class PromptManager:
    def __init__(
        self,
        type_=Literal[
            "floor_system",
            "footing",
            "shear_wall",
            "roof_system",
            "post",
            "wall_system",
            "struct_vectorization",
            "visual_context",
        ],
    ):
        with open(f"core/llm/prompts/system_prompts/{type_}.txt", encoding="utf-8") as file:
            self.sys_prompt = file.read()

    def get_sys_prompt(self):
        return self.sys_prompt


SYS_PROMPT_FLOOR = PromptManager(type_="floor_system").get_sys_prompt()
SYS_PROMPT_FOOTING = PromptManager(type_="footing").get_sys_prompt()
SYS_PROMPT_SHEAR_WALL = PromptManager(type_="shear_wall").get_sys_prompt()
SYS_PROMPT_ROOF = PromptManager(type_="roof_system").get_sys_prompt()
SYS_PROMPT_POST = PromptManager(type_="post").get_sys_prompt()
SYS_PROMPT_WALL = PromptManager(type_="wall_system").get_sys_prompt()
SYS_PROMPT_STRUCT_VECTOR = PromptManager(type_="struct_vectorization").get_sys_prompt()
SYS_PROMPT_VISUAL_CONTEXT = PromptManager(type_="visual_context").get_sys_prompt()
