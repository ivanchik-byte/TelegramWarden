"""Base model definitions and reusable mixins."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class TimestampMixin:
    """Mixin adding created_at and updated_at timestamps in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class IDMixin:
    """Mixin adding an auto-incrementing primary key ID."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
