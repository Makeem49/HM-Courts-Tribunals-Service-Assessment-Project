"""Business logic for task management."""

from flask import abort
from sqlalchemy.exc import IntegrityError

from app.models import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task_schema import STATUSES


DUPLICATE_TITLE_MESSAGE = "A task with this title already exists."


class TaskService:
    """Coordinate task operations and enforce business rules."""

    def __init__(self, repository=TaskRepository):
        self.repository = repository

    def list_tasks(self, page, page_size, status=None, search=None):
        return self.repository.list_page(page, page_size, status=status, search=search)

    def summarise_tasks(self):
        counts = self.repository.count_by_status()
        return {
            "total": sum(counts.values()),
            **{status: counts.get(status, 0) for status in STATUSES},
        }

    def get_task(self, task_id):
        task = self.repository.get(task_id)
        if task is None:
            abort(404, description=f"Task {task_id} was not found.")
        return task

    def create_task(self, data):
        self._ensure_title_available(data["title"])
        task = Task(**data)
        return self._persist(self.repository.add, task)

    def update_task(self, task_id, data):
        task = self.get_task(task_id)
        if "title" in data:
            self._ensure_title_available(data["title"], exclude_id=task_id)
        for key, value in data.items():
            setattr(task, key, value)
        return self._persist(self.repository.save, task)

    def delete_task(self, task_id):
        task = self.get_task(task_id)
        self.repository.delete(task)

    def _ensure_title_available(self, title, exclude_id=None):
        if self.repository.title_exists(title, exclude_id=exclude_id):
            abort(409, description=DUPLICATE_TITLE_MESSAGE)

    @staticmethod
    def _persist(write, task):
        # The unique index catches a duplicate that slips past the check under concurrent writes.
        try:
            return write(task)
        except IntegrityError:
            abort(409, description=DUPLICATE_TITLE_MESSAGE)
