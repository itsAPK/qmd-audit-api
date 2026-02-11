import logging
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.config import settings
from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncEngine


DATABASE_URL = settings.DATABASE_URL
print("DATABASE_URL =", repr(DATABASE_URL))

engine = create_async_engine(DATABASE_URL, echo=False, future=True,    pool_pre_ping=True,
)




async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 1:
        logging.warning(f"Slow query ({total:.2f}s): {statement}")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


# redis_client = redis.from_url(settings.REDIS_URL)

# async def get_redis_connection():
#     return redis_client

# @asynccontextmanager
# async def distributed_lock(lock_name: str, timeout: int = 60):
#     lock = redis_client.lock(lock_name, timeout=timeout)
#     acquired = await lock.acquire(blocking=False)
#     if not acquired:
#         raise RuntimeError("Could not acquire lock, task already running")
#     try:
#         yield
#     finally:
#         await lock.release()
        
