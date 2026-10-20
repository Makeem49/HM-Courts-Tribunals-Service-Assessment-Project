"""Business logic for task management."""

from flask import abort

from app.models import Task
from app.repositories.task_repository import TaskRepository


class TaskService:
    """Coordinate task operations and enforce business rules."""

    def __init__(self, repository=TaskRepository):
        self.repository = repository

    def list_tasks(self, status=None):
        return self.repository.list_all(status=status)

    def get_task(self, task_id):
        task = self.repository.get(task_id)
        if task is None:
            abort(404, description=f"Task {task_id} was not found.")
        return task

    def create_task(self, data):
        task = Task(**data)
        return self.repository.add(task)

    def update_task(self, task_id, data):
        task = self.get_task(task_id)
        for key, value in data.items():
            setattr(task, key, value)
        return self.repository.save(task)

    def delete_task(self, task_id):
        task = self.get_task(task_id)
        self.repository.delete(task)
