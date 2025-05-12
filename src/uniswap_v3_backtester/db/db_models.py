from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UniswapV3Swap(Base):
    __tablename__ = "uniswap_v3_swap_42161"
    __table_args__ = {"schema": "public"}

    tx_hash = Column(String(66), primary_key=True)
    block_number = Column(Integer)
    event_index = Column(Integer)
    volume_token0 = Column(String)
    volume_token1 = Column(String)
    sqrt_price_x96 = Column(String)
    liquidity = Column(String)
    tick = Column(Integer)
    pool_address = Column(String(42))


class Block(Base):
    __tablename__ = "blocks_42161"
    __table_args__ = {"schema": "public"}

    block_number = Column(Integer, primary_key=True)
    block_date = Column(DateTime)
