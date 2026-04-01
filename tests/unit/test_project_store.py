"""Unit tests for ProjectStore CRUD operations and edge cases."""

from __future__ import annotations

import os
import tempfile

import pytest

from backend.models.schemas import (
    AxesConfig,
    ChartElementState,
    ChartState,
    GridlineConfig,
    LegendConfig,
    Position,
    ProjectCreate,
    ProjectUpdate,
    SeriesConfig,
)
from backend.services.project_store import ProjectStore


def _make_chart_state(**overrides) -> ChartState:
    """Build a minimal valid ChartState for testing."""
    defaults = dict(
        chart_type="line",
        title=ChartElementState(text="Test Chart", position=Position(x=0, y=0)),
        axes=AxesConfig(x_label="Date", y_label="Value"),
        series=[SeriesConfig(name="s1", column="col1", chart_type="line", color="#000000")],
        legend=LegendConfig(visible=True, position=Position(x=0, y=0), entries=[]),
        gridlines=GridlineConfig(),
        annotations=[],
        data_table=None,
        elements_positions={},
        dataset_path="data/test.csv",
        dataset_columns=["date", "col1"],
    )
    defaults.update(overrides)
    return ChartState(**defaults)


@pytest.fixture
async def store(tmp_path):
    """Provide a ProjectStore backed by a temp database."""
    db_path = str(tmp_path / "test_projects.db")
    return ProjectStore(db_path=db_path)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_returns_project_with_id(store):
    cs = _make_chart_state()
    pc = ProjectCreate(name="My Project", chart_state=cs, dataset_path="data/f.csv")
    project = await store.create(pc)

    assert project.id  # non-empty UUID
    assert project.name == "My Project"
    assert project.created_at
    assert project.updated_at
    assert project.chart_state == cs
    assert project.dataset_path == "data/f.csv"
    assert project.summary_text == ""


async def test_create_with_summary_text(store):
    cs = _make_chart_state()
    pc = ProjectCreate(
        name="Summarised", chart_state=cs, dataset_path="d.csv", summary_text="A summary."
    )
    project = await store.create(pc)
    assert project.summary_text == "A summary."


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

async def test_get_existing_project(store):
    cs = _make_chart_state()
    created = await store.create(
        ProjectCreate(name="Fetch Me", chart_state=cs, dataset_path="d.csv")
    )
    fetched = await store.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Fetch Me"
    assert fetched.chart_state == cs


async def test_get_missing_project_returns_none(store):
    result = await store.get("nonexistent-id")
    assert result is None


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_all_empty(store):
    projects = await store.list_all()
    assert projects == []


async def test_list_all_returns_summaries(store):
    cs = _make_chart_state()
    await store.create(ProjectCreate(name="A", chart_state=cs, dataset_path="a.csv"))
    await store.create(ProjectCreate(name="B", chart_state=cs, dataset_path="b.csv"))

    summaries = await store.list_all()
    assert len(summaries) == 2
    names = {s.name for s in summaries}
    assert names == {"A", "B"}
    # Each summary has required fields
    for s in summaries:
        assert s.id
        assert s.updated_at


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def test_update_name(store):
    cs = _make_chart_state()
    created = await store.create(
        ProjectCreate(name="Old Name", chart_state=cs, dataset_path="d.csv")
    )
    updated = await store.update(created.id, ProjectUpdate(name="New Name"))

    assert updated.name == "New Name"
    assert updated.chart_state == cs  # unchanged
    assert updated.updated_at >= created.updated_at


async def test_update_chart_state(store):
    cs1 = _make_chart_state(chart_type="line")
    created = await store.create(
        ProjectCreate(name="P", chart_state=cs1, dataset_path="d.csv")
    )
    cs2 = _make_chart_state(chart_type="bar")
    updated = await store.update(created.id, ProjectUpdate(chart_state=cs2))

    assert updated.chart_state.chart_type == "bar"
    assert updated.name == "P"  # unchanged


async def test_update_summary_text(store):
    cs = _make_chart_state()
    created = await store.create(
        ProjectCreate(name="P", chart_state=cs, dataset_path="d.csv")
    )
    updated = await store.update(created.id, ProjectUpdate(summary_text="New summary"))
    assert updated.summary_text == "New summary"


async def test_update_nonexistent_raises(store):
    with pytest.raises(KeyError, match="Project not found"):
        await store.update("no-such-id", ProjectUpdate(name="X"))


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_removes_project(store):
    cs = _make_chart_state()
    created = await store.create(
        ProjectCreate(name="Gone", chart_state=cs, dataset_path="d.csv")
    )
    await store.delete(created.id)
    assert await store.get(created.id) is None


async def test_delete_nonexistent_is_noop(store):
    # Should not raise
    await store.delete("does-not-exist")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

async def test_special_characters_in_name(store):
    cs = _make_chart_state()
    special_name = "Project: <Test> & 'Quotes' \"Double\" — Ñoño 日本語"
    created = await store.create(
        ProjectCreate(name=special_name, chart_state=cs, dataset_path="d.csv")
    )
    fetched = await store.get(created.id)
    assert fetched is not None
    assert fetched.name == special_name


async def test_large_chart_state(store):
    """Verify a chart state with many series round-trips correctly."""
    series = [
        SeriesConfig(name=f"series_{i}", column=f"col_{i}", chart_type="line", color="#112233")
        for i in range(50)
    ]
    cs = _make_chart_state(series=series, dataset_columns=[f"col_{i}" for i in range(50)])
    created = await store.create(
        ProjectCreate(name="Big", chart_state=cs, dataset_path="d.csv")
    )
    fetched = await store.get(created.id)
    assert fetched is not None
    assert len(fetched.chart_state.series) == 50


async def test_create_multiple_then_list_order(store):
    """Projects should be listed most-recently-updated first."""
    cs = _make_chart_state()
    p1 = await store.create(ProjectCreate(name="First", chart_state=cs, dataset_path="a.csv"))
    p2 = await store.create(ProjectCreate(name="Second", chart_state=cs, dataset_path="b.csv"))
    # p2 was created after p1, so it should appear first
    summaries = await store.list_all()
    assert summaries[0].id == p2.id
    assert summaries[1].id == p1.id


async def test_delete_one_preserves_others(store):
    cs = _make_chart_state()
    p1 = await store.create(ProjectCreate(name="Keep", chart_state=cs, dataset_path="a.csv"))
    p2 = await store.create(ProjectCreate(name="Remove", chart_state=cs, dataset_path="b.csv"))
    await store.delete(p2.id)

    assert await store.get(p1.id) is not None
    assert await store.get(p2.id) is None
    summaries = await store.list_all()
    assert len(summaries) == 1
