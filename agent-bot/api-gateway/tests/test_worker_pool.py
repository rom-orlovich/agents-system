import pytest
import asyncio
from core.worker_pool import WorkerPool, ParallelRequestHandler, WorkerResult


@pytest.mark.asyncio
async def test_worker_pool_executes_all_tasks():
    pool = WorkerPool(max_workers=3)

    async def task(value: int):
        await asyncio.sleep(0.01)
        return value * 2

    tasks = [lambda v=i: task(v) for i in range(5)]
    results = await pool.execute_parallel(tasks)

    assert len(results) == 5
    assert all(r.success for r in results)
    assert [r.result for r in results] == [0, 2, 4, 6, 8]


@pytest.mark.asyncio
async def test_worker_pool_handles_failures():
    pool = WorkerPool(max_workers=3)

    async def failing_task():
        raise ValueError("Task failed")

    async def successful_task():
        return "success"

    tasks = [failing_task, successful_task, failing_task]
    results = await pool.execute_parallel(tasks)

    assert len(results) == 3
    assert results[0].success is False
    assert results[1].success is True
    assert results[2].success is False
    assert results[1].result == "success"


@pytest.mark.asyncio
async def test_worker_pool_respects_max_workers():
    pool = WorkerPool(max_workers=2)
    concurrent_tasks = 0
    max_concurrent = 0

    async def task():
        nonlocal concurrent_tasks, max_concurrent
        concurrent_tasks += 1
        max_concurrent = max(max_concurrent, concurrent_tasks)
        await asyncio.sleep(0.05)
        concurrent_tasks -= 1
        return "done"

    tasks = [task for _ in range(5)]
    results = await pool.execute_parallel(tasks)

    assert len(results) == 5
    assert all(r.success for r in results)
    assert max_concurrent <= 2


@pytest.mark.asyncio
async def test_parallel_request_handler():
    handler = ParallelRequestHandler(max_concurrent=3)

    async def process_request(req: dict):
        await asyncio.sleep(0.01)
        return {"result": req["value"] * 2}

    requests = [{"value": i} for i in range(5)]
    results = await handler.handle_batch(requests, process_request)

    assert len(results) == 5
    assert all(r.success for r in results)
    expected = [{"result": i * 2} for i in range(5)]
    assert [r.result for r in results] == expected
