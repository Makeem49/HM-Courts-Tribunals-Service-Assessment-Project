"""Data access layer for task records."""

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Task


def _escape_like(value):
    """Escape LIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _commit():
    """Commit, rolling back first if a constraint is violated so the session stays usable."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise


class TaskRepository:
    """Encapsulate database operations for tasks."""

    @staticmethod
    def get(task_id):
        return db.session.get(Task, task_id)

    @staticmethod
    def list_page(page, page_size, status=None, search=None):
        query = Task.query
        if status:
            query = query.filter_by(status=status)
        if search:
            pattern = f"%{_escape_like(search)}%"
            query = query.filter(or_(
                Task.title.ilike(pattern, escape="\\"),
                Task.description.ilike(pattern, escape="\\"),
            ))
        return query.order_by(Task.due_at.asc(), Task.id.asc()).paginate(
            page=page, per_page=page_size, error_out=False,
        )

    @staticmethod
    def title_exists(title, exclude_id=None):
        query = Task.query.filter(db.func.lower(Task.title) == db.func.lower(title))
        if exclude_id is not None:
            query = query.filter(Task.id != exclude_id)
        return db.session.query(query.exists()).scalar()

    @staticmethod
    def count_by_status():
        rows = db.session.query(Task.status, db.func.count(Task.id)).group_by(Task.status).all()
        return dict(rows)

    @staticmethod
    def add(task):
        db.session.add(task)
        _commit()
        return task

    @staticmethod
    def save(task):
        _commit()
        return task

    @staticmethod
    def delete(task):
        db.session.delete(task)
        db.session.commit()
