# kafkaesqueue
File-based Persistent Queue System for time intensive tasks.

## Flow

### Enqueue a task

Request:

```sh
POST: <url>/KAFKA/v1/enqueue
```

Body:

```json
{
    "api_route": "https://pythonapi.mastersofterp.in/RFARS/hello-world",
    "api_key": "uGTj66kW9oy7NBQjlK9AruXAn0aPHPZkvdGtSks",
    "input": {},
    "request_type": "GET"
}
```

Result:

```json
{
    "task_id": "fcfed825-8223-4fa7-b5f4-81b0b012b0e3",
    "task_status": "queued",
    "created_at": "2024-04-10T06:45:07.964450+00:00",
    "updated_at": "2024-04-10T06:45:07.964468+00:00",
    "result": null,
    "result_status_code": null
}
```

### Get status of queued task

Request:

```sh
POST: <url>/KAFKA/v1/task_status/<task_id>
```

Body:

```json

{
    "task_id": "e5f21d19-1195-49be-990c-67abc160b5f3",
    "task_status": "completed",
    "created_at": "2024-04-10T06:35:12.719320+00:00",
    "updated_at": "2024-04-10T06:35:12.876490+00:00",
    "result": {
        "message": "hello!"
    },
    "result_status_code": 200
}

``` 


## Libraries Used
- httpx
- asyncio
- fastAPI
- pydantic
