from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from storage.models import Task, WebhookEvent, TaskResult, APICall
from core.models import TaskStatus, WebhookProvider
from datetime import datetime, timezone
from typing import List


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_by_task_id(self, task_id: str) -> Task | None:
        result = await self.session.execute(
            select(Task).where(Task.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, task_id: str, status: TaskStatus, error_message: str | None = None
    ) -> bool:
        values = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if status == TaskStatus.COMPLETED or status == TaskStatus.FAILED:
            values["completed_at"] = datetime.now(timezone.utc)
        if error_message:
            values["error_message"] = error_message

        result = await self.session.execute(
            update(Task).where(Task.task_id == task_id).values(**values)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def list_by_user(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_status(
        self, status: TaskStatus, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.status == status)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class WebhookEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: WebhookEvent) -> WebhookEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_by_event_id(self, event_id: str) -> WebhookEvent | None:
        result = await self.session.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def mark_processed(self, event_id: str) -> bool:
        result = await self.session.execute(
            update(WebhookEvent)
            .where(WebhookEvent.event_id == event_id)
            .values(processed=True)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def list_unprocessed(
        self, provider: WebhookProvider | None = None, limit: int = 100
    ) -> List[WebhookEvent]:
        query = select(WebhookEvent).where(WebhookEvent.processed == False)
        if provider:
            query = query.where(WebhookEvent.provider == provider)
        query = query.order_by(WebhookEvent.created_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class TaskResultRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, result: TaskResult) -> TaskResult:
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result

    async def get_by_task_id(self, task_id: str) -> TaskResult | None:
        result = await self.session.execute(
            select(TaskResult).where(TaskResult.task_id == task_id)
        )
        return result.scalar_one_or_none()


class APICallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, api_call: APICall) -> APICall:
        self.session.add(api_call)
        await self.session.flush()
        await self.session.refresh(api_call)
        return api_call

    async def list_by_task(self, task_id: str) -> List[APICall]:
        result = await self.session.execute(
            select(APICall)
            .where(APICall.task_id == task_id)
            .order_by(APICall.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_by_service(
        self, service: str, limit: int = 100, offset: int = 0
    ) -> List[APICall]:
        result = await self.session.execute(
            select(APICall)
            .where(APICall.service == service)
            .order_by(APICall.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
