import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import config
from .logger import setup_logging, get_logger
from .infra.adb_device import AdbController
from .agent.core import TaskType
from .agent.shimen import ShimenTaskRunner

app = FastAPI(title="Game Agent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger(__name__)

# Basic In-Memory DB for Tasks
tasks_db: Dict[str, Dict[str, Any]] = {}


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRequest(BaseModel):
    task_type: TaskType
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float
    result: Optional[Any] = None
    error: Optional[str] = None


def generate_task_id() -> str:
    return str(uuid.uuid4())


async def execute_game_task(task_id: str, request: TaskRequest):
    """Background task executor."""
    logger.info(f"Starting execution for TaskID: {task_id}, Type: {request.task_type.value}")
    
    tasks_db[task_id]["status"] = TaskStatus.RUNNING
    tasks_db[task_id]["progress"] = 0.1
    
    adb = AdbController(serial=config.adb_serial)
    
    try:
        if request.task_type == TaskType.SHIMEN:
            # Instantiate and run the specific sub-agent orchestrator for Shimen tasks
            params = request.params or {}
            max_tasks = params.get("max_tasks", 10)
            runner = ShimenTaskRunner(adb_controller=adb, max_tasks=max_tasks)
            result = await runner.run()
        else:
            # Generic Custom task or Daily
            result = {"message": f"Task {request.task_type} not fully implemented yet."}
            logger.warning(f"Fallback for {request.task_type}")

        tasks_db[task_id]["status"] = TaskStatus.COMPLETED
        tasks_db[task_id]["progress"] = 1.0
        tasks_db[task_id]["result"] = result
        logger.info(f"Task {task_id} COMPLETED successfully: {result}")
    except Exception as e:
        tasks_db[task_id]["status"] = TaskStatus.FAILED
        tasks_db[task_id]["progress"] = 0.0
        tasks_db[task_id]["error"] = str(e)
        logger.error(f"Task {task_id} FAILED: {str(e)}", exc_info=True)


@app.on_event("startup")
async def on_startup():
    # Set log level based on parsed config
    setup_logging(level=config.log_level)
    logger.info("Server Startup: Game Agent API initialized with Async DB support.")


@app.get("/health")
async def health_check():
    return {"status": "ok", "agent": "Pydantic-AI with ADB"}


@app.post("/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = generate_task_id()
    
    logger.info(f"Creating new task: task_id={task_id}, type={task_request.task_type}")
    
    tasks_db[task_id] = {
        "task_id": task_id,
        "task_type": task_request.task_type,
        "params": task_request.params,
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "result": None,
        "error": None,
    }

    # Dispatch to background task. 
    # For a simple local game agent, BackgroundTasks are sufficient.
    # In large scale, consider Celery or arq.
    background_tasks.add_task(execute_game_task, task_id, task_request)

    return TaskResponse(
        task_id=task_id, status=TaskStatus.PENDING, message="Task enqueued successfully"
    )


@app.get("/tasks", response_model=List[TaskStatusResponse])
async def list_tasks():
    logger.debug("Listing all tasks")
    return [TaskStatusResponse(**task) for task in tasks_db.values()]


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    logger.debug(f"Getting task status: {task_id}")
    if task_id not in tasks_db:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(**tasks_db[task_id])

