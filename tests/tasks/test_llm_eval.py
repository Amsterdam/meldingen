import asyncio
import contextlib
from datetime import datetime
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from meldingen.models import LlmEvalRun, LlmEvalRunStatus
from meldingen.schemas.llm_eval import (
    LlmEvalClassificationInput,
    LlmEvalRunInput,
    LlmEvalTestCaseInput,
)
from meldingen.tasks.llm_eval import execute_llm_eval_run, sweep_orphaned_runs
from tests.conftest import DatabaseSessionManager


class _SharedConnectionSessionManager(DatabaseSessionManager):
    """Test-only manager that pins every session to a single connection.

    The production `DatabaseSessionManager` opens a fresh connection per call to
    `session()`. The test override at `tests/conftest.py` mirrors that, with each
    session rolled back at teardown so the real DB stays clean.

    For background-task tests we need a different shape: the task opens multiple
    sessions sequentially (one to mark `running`, one per case, one to finalize)
    and a peer test session needs to observe what the task committed. Routing
    everything through one connection (with savepoints for isolation between
    sessions, and an outer transaction we roll back at teardown) gives us that
    visibility without leaking changes past the test boundary.
    """

    _connection: Any
    _outer_transaction: Any

    def __init__(self, engine: AsyncEngine):
        super().__init__(engine)
        self._connection = None
        self._outer_transaction = None

    async def _ensure_connection(self) -> Any:
        if self._connection is None:
            self._connection = await self._engine.connect()
            self._outer_transaction = await self._connection.begin()
        return self._connection

    async def close(self) -> None:
        if self._outer_transaction is not None:
            await self._outer_transaction.rollback()
            self._outer_transaction = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        connection = await self._ensure_connection()
        sessionmaker = async_sessionmaker(
            autocommit=False, bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        session = sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def db_manager(db_engine: AsyncEngine) -> AsyncIterator[DatabaseSessionManager]:
    """Override the project-wide `db_manager` for task tests so the task's per-call
    sessions and the test's `db_session` see each other's writes via savepoints on
    a shared connection."""
    manager = _SharedConnectionSessionManager(db_engine)
    try:
        yield manager
    finally:
        await manager.close()


def _make_agent(classification_value: str) -> MagicMock:
    agent = MagicMock()
    mock_output = MagicMock()
    mock_output.classification = classification_value
    agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
    return agent


def _make_payload() -> LlmEvalRunInput:
    return LlmEvalRunInput(
        classifications=[
            LlmEvalClassificationInput(name="Zwerfvuil", instructions="Rondslingerend afval"),
            LlmEvalClassificationInput(name="Straatverlichting", instructions="Kapotte lantaarns"),
        ],
        test_cases=[
            LlmEvalTestCaseInput(text="Er ligt rommel op straat", expected="Zwerfvuil"),
            LlmEvalTestCaseInput(text="De lantaarn is kapot", expected="Straatverlichting"),
        ],
    )


@pytest.fixture
async def seeded_run(db_session: AsyncSession) -> LlmEvalRun:
    payload = _make_payload()
    run = LlmEvalRun()
    run.request_payload = payload.model_dump(mode="json")
    run.total = len(payload.test_cases)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest.mark.anyio
async def test_completes_run_writes_results_and_counts(
    db_manager: DatabaseSessionManager, db_session: AsyncSession, seeded_run: LlmEvalRun
) -> None:
    agent = _make_agent("Zwerfvuil")
    payload = _make_payload()

    await execute_llm_eval_run(seeded_run.id, payload, agent, db_manager)

    await db_session.refresh(seeded_run)
    assert seeded_run.status == LlmEvalRunStatus.completed
    assert seeded_run.passed == 1  # "Zwerfvuil" matches first expected
    assert seeded_run.failed == 1  # "Straatverlichting" expected, "Zwerfvuil" returned
    assert seeded_run.errored == 0
    assert len(seeded_run.results) == 2
    assert seeded_run.started_at is not None
    assert seeded_run.finished_at is not None


@pytest.mark.anyio
async def test_per_case_exception_recorded_as_errored(
    db_manager: DatabaseSessionManager, db_session: AsyncSession, seeded_run: LlmEvalRun
) -> None:
    agent = MagicMock()
    agent.run = AsyncMock(side_effect=RuntimeError("LLM exploded"))
    payload = _make_payload()

    await execute_llm_eval_run(seeded_run.id, payload, agent, db_manager)

    await db_session.refresh(seeded_run)
    assert seeded_run.status == LlmEvalRunStatus.completed
    assert seeded_run.errored == 2
    assert seeded_run.passed == 0
    assert seeded_run.failed == 0
    for result in seeded_run.results:
        assert result["actual"] is None
        assert result["error"] == "Classification failed for this test case."
        assert result["passed"] is False


@pytest.mark.anyio
async def test_results_written_incrementally(
    db_manager: DatabaseSessionManager, db_session: AsyncSession, seeded_run: LlmEvalRun
) -> None:
    """After case 1 completes but before case 2 starts, the row already has 1 result."""
    case1_started = asyncio.Event()
    case2_unblock = asyncio.Event()
    call_count = 0

    async def fake_run(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            case1_started.set()
            await case2_unblock.wait()
        out = MagicMock()
        out.classification = "Zwerfvuil"
        return MagicMock(output=out)

    agent = MagicMock()
    agent.run = AsyncMock(side_effect=fake_run)

    task = asyncio.create_task(execute_llm_eval_run(seeded_run.id, _make_payload(), agent, db_manager))

    # Wait until case 2 has started (= case 1 has completed and been committed).
    await asyncio.wait_for(case1_started.wait(), timeout=5.0)

    # Inspect mid-run state in a fresh session.
    async with db_manager.session() as read_session:
        mid = await read_session.get(LlmEvalRun, seeded_run.id)
        assert mid is not None
        assert len(mid.results) == 1
        assert mid.status == LlmEvalRunStatus.running

    case2_unblock.set()
    await task

    await db_session.refresh(seeded_run)
    assert seeded_run.status == LlmEvalRunStatus.completed
    assert len(seeded_run.results) == 2


@pytest.mark.anyio
async def test_unexpected_exception_marks_run_failed(
    db_manager: DatabaseSessionManager,
    db_session: AsyncSession,
    seeded_run: LlmEvalRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If something outside the per-case try raises, the run is marked failed."""

    def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("adapter init failed")

    monkeypatch.setattr("meldingen.tasks.llm_eval.AgentClassifierAdapter", boom)

    await execute_llm_eval_run(seeded_run.id, _make_payload(), MagicMock(), db_manager)

    await db_session.refresh(seeded_run)
    assert seeded_run.status == LlmEvalRunStatus.failed
    assert seeded_run.error == "Run failed unexpectedly"
    assert seeded_run.finished_at is not None
    # Must not leak internal detail
    assert "adapter init failed" not in (seeded_run.error or "")


@pytest.mark.anyio
async def test_sweep_marks_running_runs_as_failed(db_manager: DatabaseSessionManager, db_session: AsyncSession) -> None:
    run = LlmEvalRun()
    run.status = LlmEvalRunStatus.running
    run.started_at = datetime.now()
    run.total = 5
    db_session.add(run)
    await db_session.commit()
    run_id = run.id

    await sweep_orphaned_runs(db_manager)

    async with db_manager.session() as read_session:
        swept = await read_session.get(LlmEvalRun, run_id)
        assert swept is not None
        assert swept.status == LlmEvalRunStatus.failed
        assert swept.error == "Server restarted during run"
        assert swept.finished_at is not None


@pytest.mark.anyio
async def test_sweep_marks_pending_runs_as_failed(db_manager: DatabaseSessionManager, db_session: AsyncSession) -> None:
    run = LlmEvalRun()
    run.status = LlmEvalRunStatus.pending
    run.total = 5
    db_session.add(run)
    await db_session.commit()
    run_id = run.id

    await sweep_orphaned_runs(db_manager)

    async with db_manager.session() as read_session:
        swept = await read_session.get(LlmEvalRun, run_id)
        assert swept is not None
        assert swept.status == LlmEvalRunStatus.failed


@pytest.mark.anyio
async def test_sweep_leaves_completed_runs_alone(db_manager: DatabaseSessionManager, db_session: AsyncSession) -> None:
    completed = LlmEvalRun()
    completed.status = LlmEvalRunStatus.completed
    completed.total = 5
    completed.finished_at = datetime.now()

    failed = LlmEvalRun()
    failed.status = LlmEvalRunStatus.failed
    failed.total = 5
    failed.error = "Some previous error"
    failed.finished_at = datetime.now()

    db_session.add_all([completed, failed])
    await db_session.commit()
    completed_id, failed_id = completed.id, failed.id

    await sweep_orphaned_runs(db_manager)

    async with db_manager.session() as read_session:
        c = await read_session.get(LlmEvalRun, completed_id)
        f = await read_session.get(LlmEvalRun, failed_id)
        assert c is not None and c.status == LlmEvalRunStatus.completed
        assert f is not None and f.status == LlmEvalRunStatus.failed
        assert f.error == "Some previous error"
