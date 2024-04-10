# kafkaesqueue
File-based Persistent Queue System for time intensive tasks.

## Flow

- Enqueue a task

Request:

```sh
POST: KAFKA/v1/enqueue
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


## Libraries Used
- httpx
- asyncio
- fastAPI
- pydantic
