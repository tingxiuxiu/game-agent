import io
import asyncio
from typing import Optional

from PIL import Image
from async_adbutils import adb, AdbDevice
from pydantic import BaseModel

from ..logger import get_logger

logger = get_logger(__name__)


class ScreenSize(BaseModel):
    width: int
    height: int


class AdbController:
    """Async ADB Controller for Android device interaction."""

    def __init__(self, serial: Optional[str] = None):
        self.serial = serial
        self.device: Optional[AdbDevice] = None
        self._screen_size: Optional[ScreenSize] = None

    async def connect(self) -> bool:
        """Connects to the ADB device."""
        try:
            if self.serial:
                self.device = adb.device(self.serial)
            else:
                devices = await adb.devices()
                if not devices:
                    logger.error("No ADB devices found.")
                    return False
                self.device = devices[0]

            # Verify connection by getting device info
            prop = await self.device.shell("getprop ro.build.version.release")
            logger.info(
                f"Successfully connected to ADB device: {self.device.serial}, Android {prop.strip()}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ADB device: {e}", exc_info=True)
            return False

    async def _get_device(self) -> AdbDevice:
        if not self.device:
            connected = await self.connect()
            if not connected or not self.device:
                raise RuntimeError("Not connected to any ADB device")
        return self.device

    async def screenshot_bytes(self) -> bytes:
        """Takes a screenshot and returns raw bytes in PNG format."""
        device = await self._get_device()
        try:
            # -p captures in PNG format directly
            png_bytes = await device.shell("screencap -p", encoding=None)
            if not png_bytes or not png_bytes.startswith(b"\x89PNG"):
                logger.warning("screencap output does not seem to be a PNG, retrying with raw dump.")
                # fallback for some older devices
                raw_bytes = await device.shell("screencap", encoding=None)
                # raw bytes are RGBA or similar and will need manual conversion if we use this fallback
                raise ValueError("Unexpected screenshot format")
            return png_bytes
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}", exc_info=True)
            raise

    async def screenshot(self) -> Image.Image:
        """Takes a screenshot and returns a Pillow Image."""
        png_bytes = await self.screenshot_bytes()
        image = Image.open(io.BytesIO(png_bytes))
        self._screen_size = ScreenSize(width=image.width, height=image.height)
        return image

    async def click(self, x: int, y: int) -> None:
        """Simulates a click/tap on the screen."""
        device = await self._get_device()
        logger.debug(f"ADB Tap: ({x}, {y})")
        await device.shell(f"input tap {x} {y}")

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 500) -> None:
        """Simulates a swipe on the screen."""
        device = await self._get_device()
        logger.debug(f"ADB Swipe: ({x1}, {y1}) -> ({x2}, {y2}) duration: {duration_ms}ms")
        await device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    async def get_screen_size(self) -> ScreenSize:
        """Gets the device's screen size."""
        if not self._screen_size:
            device = await self._get_device()
            # Try via wm size
            output = await device.shell("wm size")
            # Output format: "Physical size: 1080x2400"
            try:
                size_str = output.strip().split(" ")[-1]
                w, h = size_str.split("x")
                self._screen_size = ScreenSize(width=int(w), height=int(h))
            except Exception:
                logger.warning("Failed to parse 'wm size', using screenshot to determine size.")
                image = await self.screenshot()
                self._screen_size = ScreenSize(width=image.width, height=image.height)
        return self._screen_size
