from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.tariff import Tariff
from app.schemas.tariff import TariffResponse

router = APIRouter(prefix="/tariffs", tags=["tariffs"])


@router.get("", response_model=list[TariffResponse])
async def list_tariffs(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Tariff]:
    return list(await session.scalars(select(Tariff).order_by(Tariff.id)))
