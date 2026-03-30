import pytest
from unittest.mock import MagicMock
from PIL import Image
import io


@pytest.fixture
def mock_pyautogui():
    mock = MagicMock()
    mock.FAILSAFE = True
    mock.PAUSE = 0.3
    return mock


@pytest.fixture
def mock_ctypes():
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_user32():
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_image():
    img = Image.new('RGB', (100, 100), color='red')
    return img


@pytest.fixture
def mock_requests():
    mock = MagicMock()
    return mock
