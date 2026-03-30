import logging
import time
import functools
import os
from pathlib import Path
from loguru import logger as loguru_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "game-agent.log"


def setup_logging(level: int | str = logging.DEBUG):
    LOG_DIR.mkdir(exist_ok=True)

    loguru_logger.remove()

    level_map = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
    }

    if isinstance(level, str):
        loguru_level = level.upper()
    else:
        loguru_level = level_map.get(level, "DEBUG")

    loguru_logger.add(
        LOG_FILE,
        level=loguru_level,
        rotation="10 MB",
        retention="5 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[module]} | {message}",
        encoding="utf-8",
    )

    loguru_logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[module]}</cyan> | <level>{message}</level>",
        colorize=True,
    )

    return loguru_logger


def get_logger(name=None):
    class CompatibleLogger:
        def __init__(self, module_name):
            self.module_name = module_name

        def _log(self, level, msg, *args, **kwargs):
            exc_info = kwargs.pop("exc_info", False)

            if args or kwargs:
                try:
                    msg = msg.format(*args, **kwargs)
                except (IndexError, KeyError):
                    pass

            if exc_info:
                loguru_logger.bind(module=self.module_name).exception(msg)
            else:
                loguru_logger.bind(module=self.module_name).log(level, msg)

        def debug(self, msg, *args, **kwargs):
            self._log("DEBUG", msg, *args, **kwargs)

        def info(self, msg, *args, **kwargs):
            self._log("INFO", msg, *args, **kwargs)

        def warning(self, msg, *args, **kwargs):
            self._log("WARNING", msg, *args, **kwargs)

        def error(self, msg, *args, **kwargs):
            self._log("ERROR", msg, *args, **kwargs)

    if name:
        return CompatibleLogger(name)
    return CompatibleLogger("game_agent")


def log_function_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(
            f"Calling function: {func.__name__} with args: {args}, kwargs: {kwargs}"
        )
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(
                f"Function {func.__name__} failed with error: {str(e)}", exc_info=True
            )
            raise

    return wrapper


def log_execution_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            logger.info(
                f"Function {func.__name__} executed in {execution_time:.4f} seconds"
            )
            return result
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.4f} seconds with error: {str(e)}",
                exc_info=True,
            )
            raise

    return wrapper


def log_api_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.perf_counter()
        logger.debug(f"API call: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            logger.info(
                f"API call {func.__name__} completed in {execution_time:.4f} seconds"
            )
            return result
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            logger.error(
                f"API call {func.__name__} failed after {execution_time:.4f} seconds with error: {str(e)}",
                exc_info=True,
            )
            raise

    return wrapper


def log_task_execution(task_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger("tasks")
            logger.info(f"Starting task: {task_name}")
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                logger.info(
                    f"Completed task: {task_name} in {execution_time:.4f} seconds"
                )
                return result
            except Exception as e:
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                logger.error(
                    f"Task {task_name} failed after {execution_time:.4f} seconds with error: {str(e)}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator
