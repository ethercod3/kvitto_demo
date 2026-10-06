from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tariff import Tariff

DEFAULT_TARIFFS = (
    {"code": "basic", "title": "Basic", "price": 990_000},
    {"code": "standard", "title": "Standard", "price": 1_990_000},
    {"code": "premium", "title": "Premium", "price": 2_990_000},
)


async def seed_tariffs(session: AsyncSession) -> None:
    existing_codes = set(await session.scalars(select(Tariff.code)))
    session.add_all(
        Tariff(**tariff) for tariff in DEFAULT_TARIFFS if tariff["code"] not in existing_codes
    )
    await session.commit()
