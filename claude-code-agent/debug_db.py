
import asyncio
from sqlalchemy import select, func
from core.database import async_session_factory
from core.database.models import TaskDB

async def debug():
    async with async_session_factory() as session:
        # Check raw tasks
        print("Checking first 5 tasks:")
        res = await session.execute(select(TaskDB.created_at, TaskDB.cost_usd).limit(5))
        tasks = res.all()
        for t in tasks:
            print(f"Task: {t.created_at} | Cost: {t.cost_usd}")

        if not tasks:
            print("NO TASKS FOUND IN DB!")
            return

        # Test the hourly grouping logic
        print("\nTesting SQLite Grouping:")
        try:
            time_group = func.strftime('%Y-%m-%d %H:00:00', TaskDB.created_at)
            query = select(
                time_group.label("date"),
                func.count(TaskDB.task_id)
            ).group_by(time_group)
            
            res = await session.execute(query)
            rows = res.all()
            print(f"Grouped Rows: {len(rows)}")
            for r in rows:
                print(f"Row: {r}")
        except Exception as e:
            print(f"SQLite logic failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug())
