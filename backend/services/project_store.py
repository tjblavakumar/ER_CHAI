"""SQLite-backed project persistence for the FRBSF Chart Builder."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import aiosqlite

from backend.models.schemas import (
    ChartState,
    Project,
    ProjectCreate,
    ProjectSummary,
    ProjectUpdate,
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    chart_state TEXT NOT NULL,
    dataset_path TEXT NOT NULL,
    summary_text TEXT DEFAULT ''
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_projects_updated_at
ON projects(updated_at DESC);
"""


class ProjectStore:
    """Async CRUD interface for project persistence using SQLite."""

    def __init__(self, db_path: str = "projects.db") -> None:
        self._db_path = db_path
        self._initialised = False

    async def _ensure_schema(self) -> None:
        if self._initialised:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(_CREATE_TABLE)
            await db.execute(_CREATE_INDEX)
            await db.commit()
        self._initialised = True

    async def create(self, project: ProjectCreate) -> Project:
        """Persist a new project and return the full Project record."""
        await self._ensure_schema()
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        chart_state_json = project.chart_state.model_dump_json()

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO projects (id, name, created_at, updated_at,
                                      chart_state, dataset_path, summary_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    project.name,
                    now,
                    now,
                    chart_state_json,
                    project.dataset_path,
                    project.summary_text,
                ),
            )
            await db.commit()

        return Project(
            id=project_id,
            name=project.name,
            created_at=now,
            updated_at=now,
            chart_state=project.chart_state,
            dataset_path=project.dataset_path,
            summary_text=project.summary_text,
        )

    async def get(self, project_id: str) -> Project | None:
        """Return a project by ID, or ``None`` if not found."""
        await self._ensure_schema()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_project(row)

    async def list_all(self) -> list[ProjectSummary]:
        """Return summaries of all projects ordered by most recently updated."""
        await self._ensure_schema()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, name, updated_at FROM projects ORDER BY updated_at DESC"
            )
            rows = await cursor.fetchall()
            return [
                ProjectSummary(id=r["id"], name=r["name"], updated_at=r["updated_at"])
                for r in rows
            ]

    async def update(self, project_id: str, data: ProjectUpdate) -> Project:
        """Apply partial updates to an existing project. Raises ``KeyError`` if not found."""
        await self._ensure_schema()
        existing = await self.get(project_id)
        if existing is None:
            raise KeyError(f"Project not found: {project_id}")

        new_name = data.name if data.name is not None else existing.name
        new_chart_state = data.chart_state if data.chart_state is not None else existing.chart_state
        new_summary = data.summary_text if data.summary_text is not None else existing.summary_text
        now = datetime.now(timezone.utc).isoformat()

        chart_state_json = new_chart_state.model_dump_json()

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE projects
                SET name = ?, chart_state = ?, summary_text = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, chart_state_json, new_summary, now, project_id),
            )
            await db.commit()

        return Project(
            id=project_id,
            name=new_name,
            created_at=existing.created_at,
            updated_at=now,
            chart_state=new_chart_state,
            dataset_path=existing.dataset_path,
            summary_text=new_summary,
        )

    async def delete(self, project_id: str) -> None:
        """Delete a project by ID. No-op if the project does not exist."""
        await self._ensure_schema()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            await db.commit()

    @staticmethod
    def _row_to_project(row: aiosqlite.Row) -> Project:
        chart_state_data = json.loads(row["chart_state"])
        return Project(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            chart_state=ChartState(**chart_state_data),
            dataset_path=row["dataset_path"],
            summary_text=row["summary_text"],
        )
