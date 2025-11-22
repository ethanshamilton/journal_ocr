# data-schemas

## Journals
### Embeddings Local File
```json
{
    "filename": [0, 1, 2, 3],
}
```
### LanceDB Table
|date|title|text|tags|embedding|
|---|---|---|---|---|
|str|str|str|list[str]|list[f64]|

## Chat Data
### Local File
This was the elasticsearch data. I needed to export
it to load into LanceDB but then I'll probably change
the format again. 
```json
{
    "threads": {
        "thread_id": "0bea13b9-c0e2-4b37-a0b0-c9fee16e3855",
        "title": "thread title",
        "tags": ["str1", "str2"],
        "created_at": "2025-10-19T03:33:52.571597",
        "updated_at": "2025-10-19T03:33:52.702378"
    },
    "messages": {
        "message_id": "4318a80a-e925-4628-bb60-9996e1f1a168",
        "thread_id": "0bea13b9-c0e2-4b37-a0b0-c9fee16e3855",
        "timestamp": "2025-10-19T03:33:52.677127",
        "role": "user",
        "content": "the chat message"
    }
}
```

### Tables
#### Threads
|thread_id|title|tags|created_at|updated_at|
|---------|-----|----|----------|----------|
|`uuid`|`str`|`list[str]`|`datetime`|`datetime`|
#### Messages
|message_id|thread_id|timestamp|role|content|
|---------|-----|----|----------|----------|
|`uuid`|`uuid`|`datetime`|`str`|`str`|
