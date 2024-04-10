import time
import os
import httpx
import asyncio
from fastapi import Body, FastAPI, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

load_dotenv()

TASK_STATUS_FILE: str = "tasks.json"
task_list: List[Dict[str, Any]] = []

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)
BEARER_TOKEN = os.getenv("KFK_BEARER_TOKEN")
# PORT = 5050


# Pydantic Models
class Numbers(BaseModel):
    x: float
    y: float


class QueueTask(BaseModel):
    task_id: str
    task_status: str
    created_at: str
    updated_at: str
    result: Any | None = None
    result_status_code: int | None = None

    @field_validator("task_status")
    def validate_task_status(cls, v):
        valid_statuses = ["queued", "processing", "completed", "failed"]
        if v.lower() not in valid_statuses:
            raise ValueError(
                "Invalid task status. Expected one of: queued, processing, completed, failed"
            )
        return v.lower()


class EnqueueRequest(BaseModel):
    api_route: str
    request_type: str
    api_key: str | None = None
    input: Dict[str, Any] | List[Dict[str, Any]] | None = None


async def authenticate(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="No Bearer Token sent.")
    token = credentials.credentials
    if token != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Bearer Token.")


async def get_uuid():
    return str(uuid4())


async def get_utc_time():
    return datetime.now(timezone.utc).isoformat()


async def write_tasks_to_file(tasks: List[Dict[str, Any]]):
    with open(TASK_STATUS_FILE, "w") as file:
        json.dump(tasks, file, indent=2)


# Update task in file
async def update_task_file(task: QueueTask):
    updated = False
    if not os.path.exists(TASK_STATUS_FILE):
        tasks = [task.model_dump(mode="json")]
        await write_tasks_to_file(tasks)
        return None

    with open(TASK_STATUS_FILE, "r") as file:
        tasks = json.load(file)
        print(tasks[0])

    for file_task in tasks:
        if file_task.get("task_id") == task.task_id:
            file_task["task_status"] = task.task_status
            file_task["updated_at"] = await get_utc_time()
            file_task["result"] = task.result
            file_task["result_status_code"] = task.result_status_code
            updated = True
            break

    if not updated:
        tasks.append(task.model_dump(mode="json"))

    await write_tasks_to_file(tasks)
    return None


async def make_request(task: QueueTask, enqueue_request: EnqueueRequest) -> QueueTask:
    try:
        print(1)
        if enqueue_request.api_key:
            print(2)
            headers = {"Authorization": f"Bearer {enqueue_request.api_key}"}
        else:
            print(3)
            headers = None

        print(4)
        async with httpx.AsyncClient(timeout=30) as client:
            print(5)
            if enqueue_request.request_type == "GET":
                res = await client.get(
                    url=enqueue_request.api_route,
                    headers=headers,
                )
            elif enqueue_request.request_type == "POST":
                res = await client.post(
                    url=enqueue_request.api_route,
                    headers=headers,
                    json=enqueue_request.input,
                )
            else:
                raise HTTPException(
                    400, f"`{enqueue_request.request_type}` method not allowed."
                )

            print(6)
            print(res)
            print(7)

            if res.is_success:
                print(8)
                task.updated_at = await get_utc_time()
                task.task_status = "completed"
                task.result = res.json()
                task.result_status_code = res.status_code
                await update_task_file(task)
                return task
            else:
                print(9)
                task.updated_at = await get_utc_time()
                task.task_status = "failed"
                task.result = res.json()
                task.result_status_code = res.status_code
                await update_task_file(task)
                return task
    except Exception as err:
        print(10)
        print(err, type(err))
        task.updated_at = await get_utc_time()
        task.task_status = "failed"
        task.result = {"error": str(err)}
        task.result_status_code = 500
        await update_task_file(task)
        return task


async def process_task(enqueue_request: EnqueueRequest, task: QueueTask):
    task.task_status = "processing"
    task.updated_at = await get_utc_time()
    await update_task_file(task)
    asyncio.create_task((make_request(task=task, enqueue_request=enqueue_request)))

    # t = asyncio.create_task(make_request(task=task, enqueue_request=enqueue_request))
    # task = await t
    # await update_task_file(task)  # TODO: check if this is necessary


@app.get("/", response_model=Dict[str, str])
async def hello(token: str = Depends(authenticate)):
    return {"message": "hello from kafkaesqueue!"}


@app.post("/divide", response_model=Dict[str, float])
async def divide(numbers: Numbers, token: str = Depends(authenticate)):
    if numbers.y == 0:
        raise HTTPException(400, "Division by zero not allowed")
    result = numbers.x / numbers.y
    return {"result": result}


@app.post("/v1/enqueue", response_model=Dict[str, Any])
async def enqueue(enqueue_request: EnqueueRequest, token: str = Depends(authenticate)):
    global queue
    task_id: str = await get_uuid()
    task: QueueTask = QueueTask(
        task_id=task_id,
        task_status="queued",
        created_at=await get_utc_time(),
        updated_at=await get_utc_time(),
        result=None,
    )
    await update_task_file(task)

    asyncio.create_task(process_task(enqueue_request, task))

    return task.dict()


@app.get("/v1/task_status/{task_id}", response_model=QueueTask)
async def get_task_status(task_id: str, token: str = Depends(authenticate)):
    print(task_id)
    if not os.path.exists(TASK_STATUS_FILE):
        raise HTTPException(status_code=404, detail="Task status file not found")

    with open(TASK_STATUS_FILE, "r") as file:
        tasks = json.load(file)

    for task in tasks:
        if task["task_id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")
