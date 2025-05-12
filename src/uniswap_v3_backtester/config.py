import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_DRIVER = os.getenv("DB_DRIVER", "postgresql+psycopg")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
    DB_CONNECT_TIMEOUT = os.getenv("DB_CONNECT_TIMEOUT", "15")
    DB_OPTIONS = os.getenv("DB_OPTIONS", "-c statement_timeout=15000")

    @classmethod
    def sqlalchemy_url(cls):
        return (
            f"{cls.DB_DRIVER}://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
            f"?sslmode={cls.DB_SSLMODE}&connect_timeout={cls.DB_CONNECT_TIMEOUT}&options={cls.DB_OPTIONS}"
        )
