from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from uniswap_v3_backtester.config import Config



def get_engine():
    return create_engine(Config.sqlalchemy_url())


engine = create_engine(Config.sqlalchemy_url())
SessionLocal = sessionmaker(bind=engine)
