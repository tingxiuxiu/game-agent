import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from game_agent.game_agent import GameAgent, TaskType
from game_agent.llm_api import LLMClient
from game_agent.screen_ops import ScreenController


class TestGameAgent:
    @patch("game_agent.game_agent.Agent")
    @patch("game_agent.game_agent.LLMClient")
    @patch("game_agent.game_agent.ScreenController")
    def test_initialization(self, mock_screen_controller, mock_llm_client, mock_agent):
        mock_llm_instance = MagicMock()
        mock_screen_instance = MagicMock()
        mock_agent_instance = MagicMock()
        mock_llm_client.return_value = mock_llm_instance
        mock_screen_controller.return_value = mock_screen_instance
        mock_agent.return_value = mock_agent_instance

        agent = GameAgent()

        assert agent.llm_client == mock_llm_instance
        assert agent.screen_controller == mock_screen_instance
        mock_agent.assert_called_once()

    @patch("game_agent.game_agent.Agent")
    def test_initialization_with_dependencies(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_llm = MagicMock(spec=LLMClient)
        mock_screen = MagicMock(spec=ScreenController)

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        assert agent.llm_client == mock_llm
        assert agent.screen_controller == mock_screen

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_click_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.click(MagicMock(), 100, 200, button="right", clicks=2)

        mock_screen.click_at.assert_called_once_with(100, 200, button="right", clicks=2)
        assert result == "已在坐标 (100, 200) 点击 2 次"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_move_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.move(MagicMock(), 300, 400)

        mock_screen.move_to.assert_called_once_with(300, 400)
        assert result == "已移动到坐标 (300, 400)"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_press_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.press(MagicMock(), "enter")

        mock_screen.press_key.assert_called_once_with("enter")
        assert result == "已按下按键: enter"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_type_text_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.type_text(MagicMock(), "test text")

        mock_screen.type_text.assert_called_once_with("test text")
        assert result == "已输入文本: test text"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_hotkey_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.hotkey(MagicMock(), ["ctrl", "c"])

        mock_screen.hotkey.assert_called_once_with("ctrl", "c")
        assert result == "已按下热键: ctrl+c"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_screenshot_tool(self, mock_agent, mock_image):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        mock_screen.screenshot.return_value = mock_image

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.screenshot(MagicMock(), region=(0, 0, 100, 100))

        mock_screen.screenshot.assert_called_once_with(region=(0, 0, 100, 100))
        assert "已截图" in result

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_find_window_tool_found(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        mock_screen.find_window.return_value = 12345

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.find_window(MagicMock(), "Test Game")

        mock_screen.find_window.assert_called_once_with("Test Game")
        assert "找到窗口" in result
        assert "12345" in result

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_find_window_tool_not_found(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        mock_screen.find_window.return_value = None

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.find_window(MagicMock(), "Non Existent")

        mock_screen.find_window.assert_called_once_with("Non Existent")
        assert "未找到" in result

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_activate_window_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.activate_window(MagicMock(), 12345)

        mock_screen.activate_window.assert_called_once_with(12345)
        assert "已激活窗口" in result

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_get_window_position_tool(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        mock_screen.get_window_rect.return_value = (100, 200, 800, 600)

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.get_window_position(MagicMock(), 12345)

        mock_screen.get_window_rect.assert_called_once_with(12345)
        assert "窗口位置" in result
        assert "100" in result
        assert "200" in result
        assert "800" in result
        assert "600" in result

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_get_window_position_tool_none(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        mock_screen.get_window_rect.return_value = None

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.get_window_position(MagicMock(), 12345)

        assert "无法获取" in result

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_call_llm(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.return_value = "LLM response"

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent._call_llm([{"role": "user", "content": "test"}])

        mock_llm.chat_completion.assert_called_once()
        assert result == "LLM response"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_run_method(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value="Task completed")
        mock_agent.return_value = mock_agent_instance

        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.run(TaskType.DAILY)

        mock_agent_instance.run.assert_called_once()
        assert result == "Task completed"

    @patch("game_agent.game_agent.Agent")
    @pytest.mark.asyncio
    async def test_run_custom_task(self, mock_agent):
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value="Custom task done")
        mock_agent.return_value = mock_agent_instance

        mock_screen = MagicMock(spec=ScreenController)
        mock_llm = MagicMock(spec=LLMClient)

        agent = GameAgent(llm_client=mock_llm, screen_controller=mock_screen)

        result = await agent.run(TaskType.CUSTOM, description="My custom task")

        mock_agent_instance.run.assert_called_once()
        assert result == "Custom task done"
