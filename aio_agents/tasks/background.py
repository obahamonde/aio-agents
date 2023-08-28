from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from celery import Celery

from ..config import env

T = TypeVar("T")

worker = Celery("tasks", broker=env.REDIS_URL, backend=env.REDIS_URL)


def task(func: Callable[..., Awaitable[T]]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        task_name = f"{func.__module__}.{func.__name__}"
        worker.send_task(task_name, args=args, kwargs=kwargs)

    return wrapper
