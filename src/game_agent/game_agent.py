from enum import Enum
from typing import Optional, Tuple, Any
from pydantic_ai import Agent, RunContext
from PIL import Image
import io
import base64
import logging

from openai import OpenAI
from .screen_ops import ScreenController
from .logger import get_logger, log_task_execution

logger = get_logger(__name__)
try:
    from .shimen_task import ShimenTask
except ImportError:
    ShimenTask = None


class TaskType(Enum):
    SHIMEN = "shimen"
    DAILY = "daily"
    CUSTOM = "custom"


SYSTEM_PROMPT = """你是一个《幻唐志》游戏助手，目标是自动完成游戏日常任务。

你可以使用提供的工具进行屏幕操作，包括：
- 鼠标点击、移动
- 键盘按键、输入、热键
- 屏幕截图
- 窗口查找和激活

工作流程：
1. 先观察游戏状态（使用截图工具）
2. 根据截图分析当前游戏界面
3. 决定下一步操作
4. 执行操作
5. 重复直到任务完成

请按照这个流程逐步完成任务。"""


class GameAgent:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        screen_controller: Optional[ScreenController] = None,
        shimen_config: Optional[dict] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.screen_controller = screen_controller or ScreenController()
        self.shimen_config = shimen_config

        self.agent = Agent(
            model=self._get_model_wrapper(),
            system_prompt=SYSTEM_PROMPT,
            tools=[
                self.click,
                self.move,
                self.press,
                self.type_text,
                self.hotkey,
                self.screenshot,
                self.find_window,
                self.activate_window,
                self.get_window_position,
            ],
        )

    def _get_model_wrapper(self):
        async def model_wrapper(messages: list, **kwargs):
            return await self._call_llm(messages, **kwargs)

        return model_wrapper

    async def _call_llm(self, messages: list, **kwargs) -> str:
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(msg)
            else:
                formatted_messages.append(
                    {
                        "role": getattr(msg, "role", "user"),
                        "content": getattr(msg, "content", str(msg)),
                    }
                )

        response = self.llm_client.chat_completion(
            messages=formatted_messages, use_conversation_history=False, **kwargs
        )
        return response

    async def click(
        self, ctx: RunContext, x: int, y: int, button: str = "left", clicks: int = 1
    ) -> str:
        """鼠标点击工具，在指定坐标点击

        Args:
            x: X坐标
            y: Y坐标
            button: 鼠标按钮，'left'或'right'
            clicks: 点击次数
        """
        logger.debug(f"Clicking at ({x}, {y}), button={button}, clicks={clicks}")
        self.screen_controller.click_at(x, y, button=button, clicks=clicks)
        return f"已在坐标 ({x}, {y}) 点击 {clicks} 次"

    async def move(self, ctx: RunContext, x: int, y: int) -> str:
        """鼠标移动工具，移动到指定坐标

        Args:
            x: X坐标
            y: Y坐标
        """
        logger.debug(f"Moving to ({x}, {y})")
        self.screen_controller.move_to(x, y)
        return f"已移动到坐标 ({x}, {y})"

    async def press(self, ctx: RunContext, key: str) -> str:
        """键盘按键工具，按下指定按键

        Args:
            key: 按键名称，如 'enter', 'space', 'esc' 等
        """
        logger.debug(f"Pressing key: {key}")
        self.screen_controller.press_key(key)
        return f"已按下按键: {key}"

    async def type_text(self, ctx: RunContext, text: str) -> str:
        """键盘输入工具，输入文本

        Args:
            text: 要输入的文本
        """
        logger.debug(f"Typing text: {text[:50]}...")
        self.screen_controller.type_text(text)
        return f"已输入文本: {text}"

    async def hotkey(self, ctx: RunContext, keys: list[str]) -> str:
        """热键工具，按下组合键

        Args:
            keys: 按键列表，如 ['ctrl', 'c']
        """
        logger.debug(f"Pressing hotkey: {'+'.join(keys)}")
        self.screen_controller.hotkey(*keys)
        return f"已按下热键: {'+'.join(keys)}"

    async def screenshot(
        self, ctx: RunContext, region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """屏幕截图工具，获取当前屏幕截图

        Args:
            region: 截图区域 (left, top, width, height)，None表示全屏
        """
        logger.debug(f"Taking screenshot, region={region}")
        img = self.screen_controller.screenshot(region=region)

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return f"已截图，尺寸: {img.size}"

    async def find_window(self, ctx: RunContext, title: str) -> str:
        """查找窗口工具，根据标题查找窗口

        Args:
            title: 窗口标题（部分匹配）
        """
        logger.debug(f"Finding window with title containing: {title}")
        hwnd = self.screen_controller.find_window(title)
        if hwnd:
            logger.debug(f"Window found, hwnd={hwnd}")
            return f"找到窗口，句柄: {hwnd}"
        logger.debug(f"Window not found")
        return f"未找到标题包含 '{title}' 的窗口"

    async def activate_window(self, ctx: RunContext, hwnd: int) -> str:
        """激活窗口工具，将窗口置于前台

        Args:
            hwnd: 窗口句柄
        """
        logger.debug(f"Activating window, hwnd={hwnd}")
        self.screen_controller.activate_window(hwnd)
        return f"已激活窗口，句柄: {hwnd}"

    async def get_window_position(self, ctx: RunContext, hwnd: int) -> str:
        """获取窗口位置工具

        Args:
            hwnd: 窗口句柄
        """
        logger.debug(f"Getting window position, hwnd={hwnd}")
        rect = self.screen_controller.get_window_rect(hwnd)
        if rect:
            return f"窗口位置: left={rect[0]}, top={rect[1]}, width={rect[2]}, height={rect[3]}"
        return f"无法获取窗口位置，句柄: {hwnd}"

    @log_task_execution("Game Task")
    async def run(self, task_type: TaskType, **kwargs) -> Any:
        """执行游戏任务

        Args:
            task_type: 任务类型
            **kwargs: 其他任务参数
        """
        logger.info(f"Starting game task: {task_type}")
        if task_type == TaskType.SHIMEN and ShimenTask is not None:
            try:
                logger.info("使用专用师门任务逻辑")
                shimen_task = ShimenTask(
                    screen_controller=self.screen_controller, config=self.shimen_config
                )
                max_tasks = kwargs.get("max_tasks", 10)
                result = shimen_task.run(max_tasks=max_tasks)
                logger.info(f"Game task {task_type} completed with shimen logic")
                return result
            except Exception as e:
                logger.warning(f"师门任务专用逻辑失败: {e}，回退到AI Agent")

        task_descriptions = {
            TaskType.SHIMEN: "完成师门任务",
            TaskType.DAILY: "完成日常任务",
            TaskType.CUSTOM: kwargs.get("description", "执行自定义任务"),
        }

        prompt = f"请执行以下任务：{task_descriptions[task_type]}"

        result = await self.agent.run(prompt)
        logger.info(f"Game task {task_type} completed")
        return result
