"""REST endpoints for tasks."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.schemas.task_schema import (
    STATUSES,
    TaskCreateSchema,
    TaskResponseSchema,
    TaskStatusSchema,
    TaskUpdateSchema,
)
from app.services.task_service import TaskService


tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
service = TaskService()
create_schema = TaskCreateSchema()
status_schema = TaskStatusSchema()
update_schema = TaskUpdateSchema()
response_schema = TaskResponseSchema()


def validation_error(error):
    return jsonify({"error": "Validation failed", "details": error.messages}), 400


@tasks_bp.get("")
def list_tasks():
    status = request.args.get("status")
    if status and status not in STATUSES:
        return jsonify({"error": "Validation failed", "details": {"status": ["Unsupported status."]}}), 400
    tasks = service.list_tasks(status=status)
    return jsonify({"items": response_schema.dump(tasks, many=True), "count": len(tasks)})


@tasks_bp.post("")
def create_task():
    try:
        data = create_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return validation_error(error)
    task = service.create_task(data)
    return jsonify(response_schema.dump(task)), 201


@tasks_bp.get("/<int:task_id>")
def get_task(task_id):
    return jsonify(response_schema.dump(service.get_task(task_id)))


@tasks_bp.patch("/<int:task_id>/status")
def update_task_status(task_id):
    try:
        data = status_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return validation_error(error)
    task = service.update_task(task_id, data)
    return jsonify(response_schema.dump(task))


@tasks_bp.patch("/<int:task_id>")
def update_task(task_id):
    try:
        data = update_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return validation_error(error)
    task = service.update_task(task_id, data)
    return jsonify(response_schema.dump(task))


@tasks_bp.delete("/<int:task_id>")
def delete_task(task_id):
    service.delete_task(task_id)
    return "", 204
