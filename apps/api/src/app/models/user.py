"""Modèle utilisateur (authentification & rôles)."""

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import UserRole


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, length=20, name="user_role"),
        nullable=False,
        default=UserRole.lecteur,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
