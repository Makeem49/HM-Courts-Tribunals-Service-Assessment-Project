"""Task persistence model."""

from datetime import datetime, timezone

from sqlalchemy.types import TypeDecorator, DateTime as SQLDateTime

from app.extensions import db


class UTCDateTime(TypeDecorator):
    """Store datetimes as UTC and restore timezone awareness on retrieval."""

    impl = SQLDateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime values must include a timezone.")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Task(db.Model):
    """A task assigned to a caseworker."""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    due_at = db.Column(UTCDateTime(), nullable=False, index=True)
    created_at = db.Column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Task id={self.id} title={self.title!r}>"
