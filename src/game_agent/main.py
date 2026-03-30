from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid
import asyncio
from .game_agent import GameAgent, TaskType
from .logger import setup_logging, get_logger

logger = get_logger(__name__)

app = FastAPI(title="Game Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


tasks_db: Dict[str, Dict[str, Any]] = {}
game_agent_instance = GameAgent()


def generate_task_id() -> str:
    return str(uuid.uuid4())


async def execute_task(task_id: str, task_type: TaskType, params: Dict[str, Any]):
    logger.info(f"Starting task execution: task_id={task_id}, type={task_type}")
    try:
        tasks_db[task_id]["status"] = TaskStatus.RUNNING
        tasks_db[task_id]["progress"] = 0.1
        logger.debug(f"Task {task_id} status changed to RUNNING")

        result = await game_agent_instance.run(task_type, **params)

        tasks_db[task_id]["status"] = TaskStatus.COMPLETED
        tasks_db[task_id]["progress"] = 1.0
        tasks_db[task_id]["result"] = result
        logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        tasks_db[task_id]["status"] = TaskStatus.FAILED
        tasks_db[task_id]["progress"] = 0.0
        tasks_db[task_id]["error"] = str(e)
        logger.error(f"Task {task_id} failed with error: {str(e)}", exc_info=True)


@app.get("/health")
async def health_check():
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = generate_task_id()
    logger.info(f"Creating new task: task_id={task_id}, type={task_request.task_type}")
    task_info = {
        "task_id": task_id,
        "task_type": task_request.task_type,
        "params": task_request.params,
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "result": None,
        "error": None,
    }
    tasks_db[task_id] = task_info

    background_tasks.add_task(
        execute_task, task_id, task_request.task_type, task_request.params
    )

    return TaskResponse(
        task_id=task_id, status=TaskStatus.PENDING, message="Task created successfully"
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    logger.debug(f"Getting task status: {task_id}")
    if task_id not in tasks_db:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_db[task_id]
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        result=task["result"],
        error=task["error"],
    )


@app.get("/tasks", response_model=List[TaskStatusResponse])
async def list_all_tasks():
    logger.debug("Listing all tasks")
    task_list = []
    for task in tasks_db.values():
        task_list.append(
            TaskStatusResponse(
                task_id=task["task_id"],
                status=task["status"],
                progress=task["progress"],
                result=task["result"],
                error=task["error"],
            )
        )
    return task_list


if __name__ == "__main__":
    setup_logging()
    logger.info("Starting Game Agent API server")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
