from datetime import datetime

from uniswap_v3_backtester.db.db import SessionLocal
from uniswap_v3_backtester.db.db_models import Block, UniswapV3Swap


def run_orm_query(pool: str, start: str, end: str):
    session = SessionLocal()
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")

        pool = pool.lower()

        results = (
            session.query(UniswapV3Swap, Block.block_date.label("timestamp"))
            .join(Block, UniswapV3Swap.block_number == Block.block_number)
            .filter(UniswapV3Swap.pool_address == pool)
            .filter(Block.block_date.between(start_dt, end_dt))
            .order_by(Block.block_date.asc())
            .all()
        )
    finally:
        session.close()

    return results
