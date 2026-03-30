import asyncio
import base64
import time
from typing import Optional, Dict, Any

from pydantic_ai.messages import ModelRequest, UserPromptPart, ModelMessage, SystemPromptPart

from .core import TaskType, GameState, agent
from ..infra.adb_device import AdbController
from ..logger import get_logger

logger = get_logger(__name__)


class ShimenTaskRunner:
    """Orchestrator for the Shimen Agent loop using Pydantic-AI and ADB."""
    
    def __init__(self, adb_controller: AdbController, max_tasks: int = 10):
        self.adb = adb_controller
        self.max_tasks = max_tasks
        self.state = GameState(adb_controller=adb_controller, max_steps=50)

    async def run(self) -> Dict[str, Any]:
        """Main loop: Take screenshot -> Ask Agent -> Perform action."""
        if not await self.adb.connect():
            return {"success": False, "error": "Could not connect to ADB"}
        
        self.state.screen_size = await self.adb.get_screen_size()
        logger.info(f"Starting Shimen Task. Screen resolution: {self.state.screen_size.width}x{self.state.screen_size.height}")
        
        step_count = 0
        max_steps = self.state.max_steps
        loop_delay = 2.0  # seconds between screenshots
        messages: list[ModelMessage] = []
        is_finished = False
        success = False

        while step_count < max_steps and not is_finished:
            step_count += 1
            self.state.step_count = step_count
            logger.info(f"--- Step {step_count}/{max_steps} ---")
            
            # Step 1: Capture Screenshot
            try:
                png_bytes = await self.adb.screenshot_bytes()
                base64_img = base64.b64encode(png_bytes).decode('utf-8')
                img_url = f"data:image/png;base64,{base64_img}"
            except Exception as e:
                logger.error(f"Failed to capture screen: {e}")
                time.sleep(loop_delay)
                continue

            # Step 2: Formulate Vision Prompt
            # Some LLMs accept images in the specific multimodal format. 
            # Pydantic-AI uses standard markdown '![image](img_url)' or specific dict format.
            # We inject the image into the prompt part.
            prompt = (
                f"这是当前屏幕截图。屏幕分辨率：{self.state.screen_size.width} x {self.state.screen_size.height}。\n"
                f"我要完成的日常任务是：【师门任务】。\n"
                f"请分析界面上的可用按钮、NPC和任务提示框。\n"
                f"结合目标，调用合适的工具执行点击（click）或滑动（swipe）。\n"
                f"如果你认为一轮或全部任务已经结束，请调用 finish_task 工具并带上总结。"
            )

            # Pydantic-AI messages context handling:
            # We create a new UserPrompt containing the text and image parts
            part_text = prompt
            part_image = f"![Screen]({img_url})"

            # Wait, in pydantic-ai, typical multimodal input depends on the underlying provider.
            # OpenAI supports passing a list of content dicts or URLs.
            # Pydantic-AI might not perfectly abstract standard image URLs easily if we just drop strings.
            # Actually, we can just pass the base64 URL inside the prompt if the model supports it via markdown,
            # or use standard pydantic-ai multimodal structures if available. 
            # For simplicity, we just pass the text + markdown image since `OpenAIModel` converts appropriately 
            # or the Nvidia API backend interprets base64 URLs if standard.
            combined_prompt = f"{part_text}\n\n{part_image}"

            # Step 3: Call Agent
            logger.info("Sending screen to LLM Agent...")
            try:
                result = await agent.run(
                    combined_prompt, 
                    deps=self.state,
                    message_history=messages[-6:]  # Keep last few turns for context, clear old to save tokens
                )
                
                # Save context
                messages = result.new_messages()
                
                # Log LLM thoughts
                logger.info(f"Agent Action text: {result.data}")
                
            except Exception as e:
                logger.error(f"Agent LLM error: {e}", exc_info=True)
                time.sleep(loop_delay)
                continue

            # Step 4: Check if finished
            # We assume finish_task logs output or agent text contains success markers (custom check if needed)
            if "结束任务" in str(result.data) or "完成" in str(result.data).lower():
                is_finished = True
                success = True
                logger.info("Agent signaled task completion.")
                # the tool `finish_task` was either called or the agent returned completion text.

            # We wait a short duration before the next cycle to let UI animations finish
            time.sleep(loop_delay)

        if not is_finished:
            logger.warning(f"Reached max steps ({max_steps}) without finishing the task.")

        return {
            "success": success,
            "steps": step_count,
            "max_tasks_configured": self.max_tasks
        }
