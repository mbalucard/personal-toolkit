from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.server import DockerPostgreSQL


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def build_db_url() -> str:
    """
    构建数据库连接字符串（SQLAlchemy URL）。

    Returns:
        str: 数据库连接 URL（postgresql+psycopg://...）。

    Raises:
        ValueError: 当数据库连接环境变量不完整时抛出。
    """
    user = DockerPostgreSQL.user
    password = DockerPostgreSQL.password
    host = DockerPostgreSQL.host
    database = DockerPostgreSQL.database

    if not user or not password or not host or not database:
        raise ValueError("数据库连接环境变量不完整")

    hostname = host
    port = None
    if ":" in host:
        hostname, port_str = host.rsplit(":", 1)
        if port_str:
            port = int(port_str)

    auth = f"{quote_plus(user)}:{quote_plus(password)}"
    if port is None:
        return f"postgresql+psycopg://{auth}@{hostname}/{database}"
    return f"postgresql+psycopg://{auth}@{hostname}:{port}/{database}"


def init_db() -> None:
    """
    初始化 SQLAlchemy Engine 与 Session 工厂。

    Returns:
        None: 无返回值。
    """
    global _engine, _SessionLocal
    db_url = build_db_url()
    _engine = create_engine(db_url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_engine() -> Engine:
    """
    获取已初始化的 SQLAlchemy Engine。

    Returns:
        Engine: SQLAlchemy Engine。

    Raises:
        RuntimeError: 当数据库未初始化时抛出。
    """
    if _engine is None:
        raise RuntimeError("数据库未初始化")
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    提供一个自动提交/回滚/关闭的 Session 上下文。

    用法：
        with session_scope() as session:
            ...

    Yields:
        Session: SQLAlchemy Session。

    Raises:
        RuntimeError: 当数据库未初始化时抛出。
        BaseException: 在上下文内发生异常时回滚并继续抛出。
    """
    if _SessionLocal is None:
        raise RuntimeError("数据库未初始化")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
