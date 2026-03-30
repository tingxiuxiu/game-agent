import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from game_agent.screen_ops import ScreenController


class TestScreenController:
    def test_initialization(self):
        controller = ScreenController(default_delay=0.5, retry_count=5)
        assert controller.default_delay == 0.5
        assert controller.retry_count == 5

    @patch('game_agent.screen_ops.pyautogui')
    def test_move_to(self, mock_pyautogui):
        controller = ScreenController()
        controller.move_to(100, 200, duration=0.5)
        mock_pyautogui.moveTo.assert_called_once_with(100, 200, duration=0.5)

    @patch('game_agent.screen_ops.pyautogui')
    def test_click_at(self, mock_pyautogui):
        controller = ScreenController()
        controller.click_at(100, 200, button='right', clicks=2, interval=0.2)
        mock_pyautogui.click.assert_called_once_with(100, 200, button='right', clicks=2, interval=0.2)

    @patch('game_agent.screen_ops.pyautogui')
    def test_press_key(self, mock_pyautogui):
        controller = ScreenController()
        controller.press_key('enter', presses=3, interval=0.15)
        mock_pyautogui.press.assert_called_once_with('enter', presses=3, interval=0.15)

    @patch('game_agent.screen_ops.pyautogui')
    def test_type_text(self, mock_pyautogui):
        controller = ScreenController()
        controller.type_text('test text', interval=0.1)
        mock_pyautogui.typewrite.assert_called_once_with('test text', interval=0.1)

    @patch('game_agent.screen_ops.pyautogui')
    def test_hotkey(self, mock_pyautogui):
        controller = ScreenController()
        controller.hotkey('ctrl', 'c')
        mock_pyautogui.hotkey.assert_called_once_with('ctrl', 'c')

    @patch('game_agent.screen_ops.pyautogui')
    def test_screenshot(self, mock_pyautogui, mock_image):
        mock_pyautogui.screenshot.return_value = mock_image
        controller = ScreenController()
        result = controller.screenshot(region=(0, 0, 100, 100))
        mock_pyautogui.screenshot.assert_called_once_with(region=(0, 0, 100, 100))
        assert result == mock_image

    @patch('game_agent.screen_ops.pyautogui')
    def test_save_screenshot(self, mock_pyautogui, mock_image):
        mock_pyautogui.screenshot.return_value = mock_image
        mock_image.save = MagicMock()
        controller = ScreenController()
        controller.save_screenshot('test.png', region=(0, 0, 100, 100))
        mock_pyautogui.screenshot.assert_called_once_with(region=(0, 0, 100, 100))
        mock_image.save.assert_called_once_with('test.png')

    @patch('game_agent.screen_ops.user32')
    def test_find_window(self, mock_user32):
        controller = ScreenController()
        hwnd = controller.find_window('Test Window')
        mock_user32.EnumWindows.assert_called_once()

    @patch('game_agent.screen_ops.user32')
    def test_get_window_rect(self, mock_user32):
        mock_user32.GetWindowRect.return_value = False
        controller = ScreenController()
        rect = controller.get_window_rect(123)
        assert rect is None

    @patch('game_agent.screen_ops.user32')
    def test_activate_window(self, mock_user32):
        controller = ScreenController()
        controller.activate_window(123)
        mock_user32.SetForegroundWindow.assert_called_once_with(123)
        mock_user32.SetFocus.assert_called_once_with(123)

    @patch('game_agent.screen_ops.pyautogui')
    def test_get_screen_size(self, mock_pyautogui):
        mock_pyautogui.size.return_value = (1920, 1080)
        controller = ScreenController()
        size = controller.get_screen_size()
        assert size == (1920, 1080)

    @patch('game_agent.screen_ops.pyautogui')
    def test_get_mouse_position(self, mock_pyautogui):
        mock_pyautogui.position.return_value = (500, 500)
        controller = ScreenController()
        pos = controller.get_mouse_position()
        assert pos == (500, 500)

    @patch('game_agent.screen_ops.pyautogui')
    def test_retry_operation_success(self, mock_pyautogui):
        mock_pyautogui.moveTo.side_effect = [Exception('fail'), Exception('fail'), None]
        controller = ScreenController(retry_count=3)
        controller.move_to(100, 200)
        assert mock_pyautogui.moveTo.call_count == 3

    @patch('game_agent.screen_ops.pyautogui')
    def test_retry_operation_failure(self, mock_pyautogui):
        mock_pyautogui.moveTo.side_effect = Exception('always fail')
        controller = ScreenController(retry_count=2)
        with pytest.raises(Exception):
            controller.move_to(100, 200)
        assert mock_pyautogui.moveTo.call_count == 2
