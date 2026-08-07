from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class Repository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], database: Session):
        self.model = model
        self.database = database

    def get(self, entity_id: UUID) -> ModelType | None:
        return self.database.get(self.model, entity_id)

    def list(self, offset: int = 0, limit: int = 20) -> tuple[list[ModelType], int]:
        statement: Select[tuple[ModelType]] = select(self.model)
        if hasattr(self.model, "eliminado_at"):
            statement = statement.where(getattr(self.model, "eliminado_at").is_(None))
        total = self.database.scalar(select(func.count()).select_from(statement.subquery())) or 0
        return list(self.database.scalars(statement.offset(offset).limit(limit))), total

    def add(self, entity: ModelType) -> ModelType:
        self.database.add(entity)
        self.database.flush()
        self.database.refresh(entity)
        return entity

    def update(self, entity: ModelType, values: dict[str, Any]) -> ModelType:
        for field, value in values.items():
            setattr(entity, field, value)
        self.database.flush()
        self.database.refresh(entity)
        return entity

    def soft_delete(self, entity: ModelType) -> None:
        if hasattr(entity, "eliminado_at"):
            setattr(entity, "eliminado_at", datetime.now(UTC))
        elif hasattr(entity, "activo"):
            setattr(entity, "activo", False)
        self.database.flush()
