"""Data access layer for task records."""

from app.extensions import db
from app.models import Task


class TaskRepository:
    """Encapsulate database operations for tasks."""

    @staticmethod
    def get(task_id):
        return db.session.get(Task, task_id)

    @staticmethod
    def list_all(status=None):
        query = Task.query
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Task.due_at.asc(), Task.id.asc()).all()

    @staticmethod
    def add(task):
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def save(task):
        db.session.commit()
        return task

    @staticmethod
    def delete(task):
        db.session.delete(task)
        db.session.commit()
