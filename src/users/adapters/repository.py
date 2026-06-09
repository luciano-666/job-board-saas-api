from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.repository import AbstractRepository
from src.users.domain.model import User


class UserRepository(AbstractRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__()
        self.session = session
