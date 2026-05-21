from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any, Callable, Optional, TypeVar

from webapp.clients.medical_api import fetch_drug_update_page
from webapp.db import session_scope
from webapp.models import DrugUpdateInfo
from webapp.repositories.drug_update_repo import delete_by_version, insert_batch_do_nothing

T = TypeVar("T")
EMPTY_STRING_FIELDS = ("goodsCodeHistory", "oldApprovalCode")


class IngestCancelled(Exception):
    pass


@dataclass(frozen=True)
class IngestPageDetail:
    page: int
    fetched_rows: int
    inserted_rows: int
    page_elapsed_seconds: float
    page_elapsed_text: str
    cumulative_elapsed_text: str


@dataclass(frozen=True)
class IngestResult:
    version: str
    deleted_rows: int
    inserted_rows: int
    total_records: int
    rows_per_page: int
    total_pages: int
    start_page: int
    end_page: int
    total_elapsed_seconds: float
    total_elapsed_text: str
    page_details: list[IngestPageDetail]


def _retry(name: str, fn: Callable[[], T], *, max_retries: int, retry_delay_seconds: float) -> T:
    """
    通用重试执行器。

    Args:
        name (str): 任务名称（用于定位日志/异常场景）。
        fn (Callable[[], T]): 需要执行的函数。
        max_retries (int): 最大重试次数（含首次执行）。
        retry_delay_seconds (float): 重试间隔（秒）。

    Returns:
        T: 执行成功返回 fn 的结果。

    Raises:
        BaseException: 达到最大重试次数仍失败时抛出最后一次异常。
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except BaseException as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            sleep(retry_delay_seconds)
    raise AssertionError("unreachable") from last_exc


def _cancellable_sleep(
    seconds: float,
    *,
    should_cancel: Callable[[], bool] | None,
) -> None:
    remaining = max(0.0, float(seconds or 0.0))
    if remaining <= 0:
        return
    step = 0.2
    while remaining > 0:
        if should_cancel is not None and should_cancel():
            raise IngestCancelled("抓取已终止")
        chunk = step if remaining > step else remaining
        sleep(chunk)
        remaining -= chunk


def _retry_cancelable(
    name: str,
    fn: Callable[[], T],
    *,
    max_retries: int,
    retry_delay_seconds: float,
    should_cancel: Callable[[], bool] | None,
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(1, max_retries + 1):
        if should_cancel is not None and should_cancel():
            raise IngestCancelled("抓取已终止")
        try:
            return fn()
        except BaseException as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            _cancellable_sleep(retry_delay_seconds, should_cancel=should_cancel)
    raise AssertionError("unreachable") from last_exc


def _get_total_pages(records: int, rows: int) -> int:
    """
    根据总记录数与每页条数计算总页数。

    Args:
        records (int): 总记录数。
        rows (int): 每页条数。

    Returns:
        int: 总页数。
    """
    if records <= 0:
        return 0
    if records % rows == 0:
        return records // rows
    return records // rows + 1


def _format_duration(seconds: float) -> str:
    """
    将秒数格式化为可读的中文耗时文本。

    Args:
        seconds (float): 秒数。

    Returns:
        str: 格式化后的耗时文本（例如 3秒、1分05秒）。
    """
    total_seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(total_seconds, 60)
    if minutes > 0:
        return f"{minutes}分{sec:02d}秒"
    return f"{sec}秒"


def _fetch_page_sync(
    *,
    version: str,
    page: int,
    rows: int,
    goodsCode: Optional[str] = None,
    registeredProductName: Optional[str] = None,
    approvalCode: Optional[str] = None,
    companyNameSc: Optional[str] = None,
) -> dict:
    """
    同步方式抓取单页数据（内部封装 asyncio.run）。

    Args:
        version (str): 版本号（batchNumber）。
        page (int): 页码。
        rows (int): 每页条数。
        goodsCode (str | None): 药品代码筛选。
        registeredProductName (str | None): 注册产品名称筛选。
        approvalCode (str | None): 批准文号筛选。
        companyNameSc (str | None): 企业名称筛选。

    Returns:
        dict: 接口返回 JSON 数据。
    """
    return asyncio.run(
        fetch_drug_update_page(
            version=version,
            page=page,
            rows=rows,
            goodsCode=goodsCode,
            registeredProductName=registeredProductName,
            approvalCode=approvalCode,
            companyNameSc=companyNameSc,
        )
    )


def ingest_drug_update(
    *,
    version: str,
    rows: int = 1000,
    start_page: int = 1,
    end_page: Optional[int] = None,
    clear_existing: bool = True,
    waiting_time: int = 5,
    max_retries: int = 3,
    retry_delay_seconds: float = 2.0,
    goodsCode: Optional[str] = None,
    registeredProductName: Optional[str] = None,
    approvalCode: Optional[str] = None,
    companyNameSc: Optional[str] = None,
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    should_cancel: Callable[[], bool] | None = None,
) -> IngestResult:
    """
    按页抓取“药品更新信息”并写入数据库。

    抓取策略：
    1) 先按 version 清空历史数据（DELETE）。
    2) 计算总页数后，从 start_page 到 end_page（不传则到最后一页）逐页抓取。
    3) 每页数据使用 INSERT ON CONFLICT DO NOTHING 写入，避免重复。
    4) 自动控制接口调用间隔（waiting_time 最小按 6 秒执行）。

    Args:
        version (str): 版本号（更新日期，格式 yyyyMMdd）。
        rows (int): 每页抓取条数。
        start_page (int): 起始页（从 1 开始）。
        end_page (int | None): 结束页（包含）。不传表示抓取到最后一页。
        clear_existing (bool): 是否先清空该版本号历史数据。
        waiting_time (int): 两次接口调用间隔（秒），最小 6 秒。
        max_retries (int): 最大重试次数（含首次）。
        retry_delay_seconds (float): 重试间隔（秒）。
        goodsCode (str | None): 药品代码筛选（可选）。
        registeredProductName (str | None): 注册产品名称筛选（可选）。
        approvalCode (str | None): 批准文号筛选（可选）。
        companyNameSc (str | None): 企业名称筛选（可选）。
        progress_callback (Callable[[dict[str, Any]], None] | None): 进度回调（用于前端实时展示）。

    Returns:
        IngestResult: 抓取与入库汇总结果（含总页数、写入行数、耗时等）。
    """
    if waiting_time < 6:
        waiting_time = 6
    if should_cancel is not None and should_cancel():
        raise IngestCancelled("抓取已终止")

    overall_started_at = monotonic()

    deleted = 0
    if clear_existing:
        if should_cancel is not None and should_cancel():
            raise IngestCancelled("抓取已终止")
        with session_scope() as session:
            deleted = delete_by_version(session, version)

    last_fetch_at = 0.0

    def fetch_page(page: int) -> dict:
        """
        带节流控制的分页抓取函数。

        Args:
            page (int): 页码。

        Returns:
            dict: 接口返回 JSON 数据。
        """
        nonlocal last_fetch_at
        now = monotonic()
        if last_fetch_at > 0:
            diff = now - last_fetch_at
            if diff < waiting_time:
                _cancellable_sleep(waiting_time - diff, should_cancel=should_cancel)
        if should_cancel is not None and should_cancel():
            raise IngestCancelled("抓取已终止")
        data = _fetch_page_sync(
            version=version,
            page=page,
            rows=rows,
            goodsCode=goodsCode,
            registeredProductName=registeredProductName,
            approvalCode=approvalCode,
            companyNameSc=companyNameSc,
        )
        last_fetch_at = monotonic()
        return data

    first = _retry_cancelable(
        "fetch-first-page",
        lambda: fetch_page(1),
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
        should_cancel=should_cancel,
    )
    records = int(first.get("records") or 0)
    total_pages = _get_total_pages(records, rows)

    start_page = max(1, int(start_page or 1))
    effective_end = total_pages
    if end_page is not None:
        effective_end = min(effective_end, int(end_page))

    if progress_callback is not None:
        progress_callback(
            {
                "event": "meta",
                "total_records": records,
                "total_pages": total_pages,
                "rows_per_page": rows,
                "start_page": start_page,
                "end_page": effective_end,
                "deleted_rows": deleted,
                "message": (
                    f"已获取任务信息：共 {records} 条数据，总页数 {total_pages}，"
                    f"每页 {rows} 条，处理页范围 {start_page}-{effective_end}"
                ),
            }
        )

    allowed_cols = set(DrugUpdateInfo.__table__.columns.keys())
    inserted_total = 0
    page_details: list[IngestPageDetail] = []

    for page in range(start_page, effective_end + 1):
        if should_cancel is not None and should_cancel():
            raise IngestCancelled("抓取已终止")
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "page_started",
                    "page": page,
                    "processed_pages": len(page_details),
                    "inserted_rows": inserted_total,
                    "message": f"开始抓取第 {page} 页",
                }
            )
        page_started_at = monotonic()
        if page == 1 and start_page == 1:
            data = first
        else:
            data = _retry_cancelable(
                f"fetch-page-{page}",
                lambda: fetch_page(page),
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                should_cancel=should_cancel,
            )
        raw_rows: list[dict[str, Any]] = list(data.get("rows") or [])
        batch: list[dict[str, Any]] = []
        for r in raw_rows:
            goodscode = r.get("goodscode") or r.get("goodsCode")
            if not goodscode:
                continue
            row = {k: v for k, v in r.items() if k in allowed_cols}
            for key in allowed_cols:
                row.setdefault(key, None)
            for field in EMPTY_STRING_FIELDS:
                row[field] = row.get(field) or ""
            row["traceCodeFlag"] = row.get("traceCodeFlag") or "0"
            row["version"] = version
            row["goodscode"] = goodscode
            batch.append(row)

        if should_cancel is not None and should_cancel():
            raise IngestCancelled("抓取已终止")
        with session_scope() as session:
            inserted = _retry_cancelable(
                f"insert-page-{page}",
                lambda: insert_batch_do_nothing(session, batch),
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                should_cancel=should_cancel,
            )
        inserted_total += inserted
        page_elapsed_seconds = monotonic() - page_started_at
        cumulative_elapsed_seconds = monotonic() - overall_started_at
        page_details.append(
            IngestPageDetail(
                page=page,
                fetched_rows=len(raw_rows),
                inserted_rows=inserted,
                page_elapsed_seconds=page_elapsed_seconds,
                page_elapsed_text=_format_duration(page_elapsed_seconds),
                cumulative_elapsed_text=_format_duration(cumulative_elapsed_seconds),
            )
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "page_finished",
                    "page": page,
                    "fetched_rows": len(raw_rows),
                    "inserted_rows_current_page": inserted,
                    "inserted_rows_total": inserted_total,
                    "processed_pages": len(page_details),
                    "page_elapsed_seconds": page_elapsed_seconds,
                    "page_elapsed_text": _format_duration(page_elapsed_seconds),
                    "cumulative_elapsed_seconds": cumulative_elapsed_seconds,
                    "cumulative_elapsed_text": _format_duration(cumulative_elapsed_seconds),
                    "message": (
                        f"第 {page} 页已存库：抓取 {len(raw_rows)} 行，"
                        f"写入 {inserted} 行，本页耗时 {_format_duration(page_elapsed_seconds)}，"
                        f"累计耗时 {_format_duration(cumulative_elapsed_seconds)}"
                    ),
                }
            )

    total_elapsed_seconds = monotonic() - overall_started_at
    if progress_callback is not None:
        progress_callback(
            {
                "event": "finished",
                "total_elapsed_seconds": total_elapsed_seconds,
                "total_elapsed_text": _format_duration(total_elapsed_seconds),
                "inserted_rows_total": inserted_total,
                "message": f"抓取完成，总耗时 {_format_duration(total_elapsed_seconds)}",
            }
        )
    return IngestResult(
        version=version,
        deleted_rows=deleted,
        inserted_rows=inserted_total,
        total_records=records,
        rows_per_page=rows,
        total_pages=total_pages,
        start_page=start_page,
        end_page=effective_end,
        total_elapsed_seconds=total_elapsed_seconds,
        total_elapsed_text=_format_duration(total_elapsed_seconds),
        page_details=page_details,
    )
