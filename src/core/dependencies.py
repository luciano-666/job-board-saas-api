from typing import Annotated

from fastapi import Depends

from src.core.database import AsyncSessionLocal, AsyncSession


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]
