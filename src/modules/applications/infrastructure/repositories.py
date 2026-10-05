from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_, literal, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.applications.application.interfaces import IApplicationRepository
from src.modules.applications.domain.entities import Application
from src.modules.applications.infrastructure.models import ApplicationModel
from src.modules.applications.presentation.exceptions import ApplicationException
from src.modules.shared.presentation.exceptions import StandardException
from src.modules.applications.application.dto import ApplicationCursor, ApplicationFilters
from src.modules.jobs.application.dto import CursorPage

logger = structlog.get_logger(__name__)


class SqlAlchemyApplicationRepository(IApplicationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # CREATE
    async def create(self, application: Application) -> None:
        try:
            logger.info(
                f"Creating application {application.id} for candidate "
                f"{application.candidate_id} to job {application.job_id}."
            )

            db_application = ApplicationModel.from_entity(application)

            self.session.add(db_application)
            await self.session.flush()

            logger.info(f"Application {application.id} created successfully.")
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the create application repository.", exc_info=e
            )
            raise ApplicationException()

    # READ
    async def get_by_id(self, id: UUID) -> Optional[Application]:
        try:
            logger.info(f"Retrieving application with id {id} from database.")

            statement = select(ApplicationModel).where(
                ApplicationModel.id == id, ApplicationModel.is_active.is_(True)
            )

            result = await self.session.execute(statement)
            application_model: Optional[ApplicationModel] = result.scalar_one_or_none()

            if application_model is None:
                logger.info(f"Application with id {id} not found in database.")
                return None

            application = application_model.to_entity()

            logger.info(f"Application {application.id} retrieved successfully.")
            return application
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the get application by id repository.",
                exc_info=e,
            )
            raise ApplicationException()

    async def exists_by_candidate_and_job(
        self, candidate_id: UUID, job_id: UUID
    ) -> bool:
        try:
            logger.info(
                f"Checking if candidate {candidate_id} has already applied to "
                f"job {job_id}."
            )

            statement = (
                select(ApplicationModel.id)
                .where(
                    ApplicationModel.candidate_id == candidate_id,
                    ApplicationModel.job_id == job_id,
                    ApplicationModel.is_active.is_(True),
                )
                .limit(1)
            )

            result = await self.session.scalar(statement)
            exists = result is not None

            logger.info(
                f"Existence check for candidate {candidate_id} on job {job_id} "
                f"completed. Exists: {exists}."
            )
            return exists
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred during the existence check of an application "
                "in the database.",
                exc_info=e,
            )
            raise ApplicationException()

    # UPDATE
    async def update(self, application: Application) -> None:
        try:
            logger.info(f"Updating application {application.id} in database.")

            db_application = ApplicationModel.from_entity(application)
            await self.session.merge(db_application)
            await self.session.flush()

            logger.info(f"Application {application.id} updated successfully.")
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the update application repository.", exc_info=e
            )
            raise ApplicationException()

    async def list_by_filters(
        self,
        filters: ApplicationFilters,
        *,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[Application]:
        try:
            logger.info("Listing applications by filters with cursor pagination.")

            conditions = [ApplicationModel.is_active.is_(True)]

            if filters.job_id is not None:
                conditions.append(ApplicationModel.job_id == filters.job_id)
            if filters.candidate_id is not None:
                conditions.append(ApplicationModel.candidate_id == filters.candidate_id)
            if filters.status is not None:
                conditions.append(ApplicationModel.status == filters.status)

            if cursor is not None:
                decoded = ApplicationCursor.decode(cursor)
                conditions.append(
                    tuple_(ApplicationModel.created_at, ApplicationModel.id)
                    < tuple_(
                        literal(decoded.created_at), literal(decoded.application_id)
                    )
                )

            statement = (
                select(ApplicationModel)
                .where(and_(*conditions))
                .order_by(
                    ApplicationModel.created_at.desc(), ApplicationModel.id.desc()
                )
                .limit(limit + 1)
            )

            result = await self.session.execute(statement)
            models = list(result.scalars().all())

            has_more = len(models) > limit
            page_models = models[:limit]
            items = [m.to_entity() for m in page_models]

            next_cursor = None
            if has_more and items:
                last = items[-1]
                next_cursor = ApplicationCursor(
                    created_at=last.created_at, application_id=last.id
                ).encode()

            logger.info(f"Listed {len(items)} applications successfully.")
            return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
        except StandardException:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the list applications by filters repository.",
                exc_info=e,
            )
            raise ApplicationException()
