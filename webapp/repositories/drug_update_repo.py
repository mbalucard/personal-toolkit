from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Optional

from sqlalchemy import Select, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from webapp.models import DrugUpdateInfo


@dataclass(frozen=True)
class PageResult:
    items: list[DrugUpdateInfo]
    total: int


def delete_by_version(session: Session, version: str) -> int:
    """
    按版本号删除 drug_update_info 数据。

    Args:
        session (Session): SQLAlchemy Session。
        version (str): 版本号。

    Returns:
        int: 删除的行数。
    """
    result = session.query(DrugUpdateInfo).filter(DrugUpdateInfo.version == version).delete()
    return int(result)


def insert_batch_do_nothing(session: Session, rows: list[dict[str, Any]]) -> int:
    """
    批量写入 drug_update_info，遇到冲突则忽略（ON CONFLICT DO NOTHING）。

    Args:
        session (Session): SQLAlchemy Session。
        rows (list[dict[str, Any]]): 待写入的行数据。

    Returns:
        int: 实际写入的行数。
    """
    if not rows:
        return 0
    stmt = insert(DrugUpdateInfo).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["version", "goodscode"])
    stmt = stmt.returning(DrugUpdateInfo.goodscode)
    result = session.execute(stmt)
    return len(result.scalars().all())


def list_versions(session: Session) -> list[str]:
    """
    列出已入库的版本号列表（去重、按版本号倒序）。

    Args:
        session (Session): SQLAlchemy Session。

    Returns:
        list[str]: 版本号列表。
    """
    stmt: Select[Any] = select(DrugUpdateInfo.version).distinct().order_by(DrugUpdateInfo.version.desc())
    return [row[0] for row in session.execute(stmt).all()]


def query_page(
    session: Session,
    *,
    version: str,
    page: int,
    page_size: int,
    goodscode: Optional[str] = None,
    registeredproductname: Optional[str] = None,
    goodsstandardcode: Optional[str] = None,
    approvalcode: Optional[str] = None,
) -> PageResult:
    """
    查询指定版本号的数据并分页返回。

    Args:
        session (Session): SQLAlchemy Session。
        version (str): 版本号（必填）。
        page (int): 当前页（从 1 开始）。
        page_size (int): 每页条数。
        goodscode (str | None): 药品代码筛选（可选）。
        registeredproductname (str | None): 注册产品名称筛选（可选）。
        goodsstandardcode (str | None): 药品本位码筛选（可选）。
        approvalcode (str | None): 批准文号筛选（可选）。

    Returns:
        PageResult: 分页结果（items 与 total）。
    """
    q = session.query(DrugUpdateInfo).filter(DrugUpdateInfo.version == version)

    if goodscode:
        q = q.filter(DrugUpdateInfo.goodscode.ilike(f"%{goodscode}%"))
    if registeredproductname:
        q = q.filter(DrugUpdateInfo.registeredproductname.ilike(f"%{registeredproductname}%"))
    if goodsstandardcode:
        q = q.filter(DrugUpdateInfo.goodsstandardcode.ilike(f"%{goodsstandardcode}%"))
    if approvalcode:
        q = q.filter(DrugUpdateInfo.approvalcode.ilike(f"%{approvalcode}%"))

    total = int(q.with_entities(func.count()).scalar() or 0)
    items = (
        q.order_by(DrugUpdateInfo.goodscode.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResult(items=items, total=total)


def execute_export_sql(session: Session, sql: str, *, version: str) -> list[tuple[Any, ...]]:
    """
    执行导出 SQL 并返回结果集。

    Args:
        session (Session): SQLAlchemy Session。
        sql (str): SQL 文本（应包含 :version 参数）。
        version (str): 版本号。

    Returns:
        list[tuple[Any, ...]]: 查询结果行列表。
    """
    result = session.execute(text(sql), {"version": version})
    return list(result.fetchall())


def iter_export_sql(
    session: Session,
    sql: str,
    *,
    version: str,
    batch_size: int = 2000,
) -> Iterator[tuple[Any, ...]]:
    result = session.execute(
        text(sql).execution_options(stream_results=True),
        {"version": version},
    )
    while True:
        batch = result.fetchmany(batch_size)
        if not batch:
            break
        for row in batch:
            yield tuple(row)
