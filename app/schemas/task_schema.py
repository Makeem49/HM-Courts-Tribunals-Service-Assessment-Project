"""Marshmallow schemas for validating and serialising tasks."""

from datetime import datetime, timezone

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


STATUSES = ("pending", "in_progress", "completed")


def parse_due_at(value):
    """Require an ISO-8601 datetime with a timezone offset."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("Use an ISO-8601 datetime, e.g. 2026-10-20T15:00:00Z.") from exc
    else:
        raise ValidationError("A valid ISO-8601 due date/time is required.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError("Include a timezone, for example Z or +01:00.")
    return parsed.astimezone(timezone.utc)


class TaskCreateSchema(Schema):
    """Validate fields accepted when creating a task."""

    title = fields.String(required=True, validate=validate.Length(min=1, max=160))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=5000))
    status = fields.String(load_default="pending", validate=validate.OneOf(STATUSES))
    due_at = fields.DateTime(required=True, format="iso", data_key="due_at")

    @validates_schema
    def validate_title(self, data, **kwargs):
        if "title" in data:
            data["title"] = data["title"].strip()
            if not data["title"]:
                raise ValidationError({"title": ["Title must not be blank."]})
        if "description" in data and data["description"] is not None:
            data["description"] = data["description"].strip()
        due_at = data.get("due_at")
        if due_at is not None:
            if due_at.tzinfo is None or due_at.utcoffset() is None:
                raise ValidationError({"due_at": ["Include a timezone, e.g. Z or +01:00."]})
            data["due_at"] = due_at.astimezone(timezone.utc)


class TaskStatusSchema(Schema):
    """Validate status-only updates."""

    status = fields.String(required=True, validate=validate.OneOf(STATUSES))


class TaskUpdateSchema(Schema):
    """Validate partial task updates."""

    title = fields.String(validate=validate.Length(min=1, max=160))
    description = fields.String(allow_none=True, validate=validate.Length(max=5000))
    due_at = fields.DateTime(format="iso")
    status = fields.String(validate=validate.OneOf(STATUSES))

    @validates_schema
    def validate_fields(self, data, **kwargs):
        if not data:
            raise ValidationError("Provide at least one field to update.")
        if "title" in data:
            data["title"] = data["title"].strip()
            if not data["title"]:
                raise ValidationError({"title": ["Title must not be blank."]})
        if "description" in data and data["description"] is not None:
            data["description"] = data["description"].strip()
        if "due_at" in data:
            due_at = data["due_at"]
            if due_at.tzinfo is None or due_at.utcoffset() is None:
                raise ValidationError({"due_at": ["Include a timezone, e.g. Z or +01:00."]})
            data["due_at"] = due_at.astimezone(timezone.utc)


class TaskResponseSchema(Schema):
    """Public task representation returned by the API."""

    id = fields.Integer(dump_only=True)
    title = fields.String()
    description = fields.String(allow_none=True)
    status = fields.String()
    due_at = fields.DateTime(format="iso")
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")
