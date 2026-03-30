import io
from typing import Any, Optional, Dict
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

from ..config import config
from ..infra.adb_device import AdbController, ScreenSize
from ..logger import get_logger, log_task_execution

logger = get_logger(__name__)


class TaskType(Enum):
    SHIMEN = "shimen"
    DAILY = "daily"
    CUSTOM = "custom"


class GameState(BaseModel):
    """Context required by the agent during a run."""
    adb_controller: AdbController
    screen_size: Optional[ScreenSize] = None
    step_count: int = 0
    max_steps: int = 50


SYSTEM_PROMPT = """你是一个《幻唐志》游戏助手，你的目标是根据屏幕截图和当前任务自动完成游戏日常任务。

你可以使用提供的工具进行屏幕操作，包括：
- 点击 (click)
- 滑动 (swipe)
- 结束任务 (finish_task)

工作流程：
1. 观察游戏截图状态
2. 分析当前游戏界面和目标
3. 决定下一步操作，并调用相应工具
4. 重要：每次回复必须详细说明你的推理过程（thought process）以及你要执行的操作。

如果任务已完成，请调用 finish_task 结束此任务。
若找不到明确路径或遇到弹窗卡死，也请说明，使用相应的错误重试或滑动浏览。
"""

# Configure LLM Client
# Pydantic-AI uses OpenAIModel to support OpenAI-compatible endpoints natively.
# Passed through an OpenAIProvider instance.
provider = OpenAIProvider(
    base_url=config.nvidia_base_url,
    api_key=config.nvidia_api_key,
)

llm_model = OpenAIModel(
    config.llm_model,
    provider=provider,
)

# Initialize the Pydantic-AI Agent
agent = Agent(
    model=llm_model,
    system_prompt=SYSTEM_PROMPT,
    deps_type=GameState,
    retries=2,
)


@agent.tool
async def click(ctx: RunContext[GameState], x: int, y: int) -> str:
    """在屏幕指定坐标点击 (Click at specific x,y coordinates). Use this to interact with UI buttons/NPCs.
    
    Args:
        x: X坐标
        y: Y坐标
    """
    logger.info(f"LLM Tool Call: Click at ({x}, {y})")
    try:
        await ctx.deps.adb_controller.click(x, y)
        return f"成功点击坐标 ({x}, {y})"
    except Exception as e:
        logger.error(f"Click Tool failed: {e}")
        return f"点击失败: {str(e)}"


@agent.tool
async def swipe(ctx: RunContext[GameState], start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 500) -> str:
    """在屏幕上进行滑动操作 (Swipe across screen). Use this to scroll lists or move character.
    
    Args:
        start_x: 起始X坐标
        start_y: 起始Y坐标
        end_x: 结束X坐标
        end_y: 结束Y坐标
        duration_ms: 滑动持续时间(毫秒)，默认500ms
    """
    logger.info(f"LLM Tool Call: Swipe ({start_x}, {start_y}) to ({end_x}, {end_y})")
    try:
        await ctx.deps.adb_controller.swipe(start_x, start_y, end_x, end_y, duration_ms)
        return f"成功滑动从 ({start_x}, {start_y}) 到 ({end_x}, {end_y})"
    except Exception as e:
        logger.error(f"Swipe Tool failed: {e}")
        return f"滑动失败: {str(e)}"

@agent.tool
async def finish_task(ctx: RunContext[GameState], success: bool, message: str) -> str:
    """
    标记任务完成或无法继续。当任务目标达成或遇到不可修复的问题时调用。
    
    Args:
        success: 任务是否成功完成
        message: 结束时的总结说明
    """
    logger.info(f"LLM Tool Call: Task Finished. Success={success}, Message={message}")
    if success:
        return f"结束任务: {message} (成功)"
    else:
        return f"结束任务: {message} (失败)"

