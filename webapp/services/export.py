from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from sqlalchemy import text

from openpyxl import Workbook

from config.address import root_dir
from tools.other import read_sql_language
from webapp.db import session_scope
from webapp.repositories.drug_update_repo import iter_export_sql


ExportStyle = Literal["standard", "new"]
TEMP_EXPORT_MAX_AGE_SECONDS = 24 * 60 * 60


STANDARD_COLUMNS = [
    "药品代码",
    "注册名称",
    "注册剂型",
    "注册规格",
    "商品名称",
    "剂型",
    "规格",
    "包装材质",
    "最小包装数量",
    "最小制剂单位",
    "最小包装单位",
    "有无追溯码",
    "药品企业",
    "批准文号",
    "药品本位码",
    "甲乙类",
    "编号",
    "药品名称",
    "剂型",
    "备注",
]


NEW_COLUMNS = [
    "药品代码",
    "历史商品代码",
    "注册名称",
    "注册剂型",
    "注册规格",
    "商品名称",
    "剂型",
    "规格",
    "包装材质",
    "最小包装数量",
    "最小制剂单位",
    "最小包装单位",
    "有无追溯码",
    "药品企业",
    "生产企业或持有人名称",
    "分包装企业",
    "批准文号",
    "旧批准文号",
    "药品本位码",
    "甲乙类",
    "编号",
    "药品名称",
    "剂型",
    "备注",
    "营业执照统一社会信用代码",
    "药品有效期 (月)",
    "儿童用药标志",
    "是否OTC标志",
]


@dataclass(frozen=True)
class ExportFile:
    filename: str
    path: Path


class ExportCancelled(Exception):
    pass


def _temporary_dir() -> Path:
    return Path(root_dir) / "webapp" / "temporary_data"


def _cleanup_old_exports(dir_path: Path, *, max_age_seconds: int) -> None:
    now = time.time()
    if not dir_path.exists():
        return
    for p in dir_path.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() != ".xlsx":
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if now - mtime > max_age_seconds:
            try:
                p.unlink()
            except OSError:
                pass


def _safe_fragment(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", value)
    return value.strip("_") or "unknown"


def _build_export_file(style: ExportStyle, version: str) -> ExportFile:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{ts}_{_safe_fragment(version)}_{style}.xlsx"
    path = _temporary_dir() / filename
    return ExportFile(filename=filename, path=path)


def _load_sql(style: ExportStyle) -> str:
    """
    读取并转换导出 SQL。

    将备忘 SQL 中的硬编码 version 条件替换为 SQLAlchemy 可绑定参数 :version。

    Args:
        style (ExportStyle): 导出样式（standard/new）。

    Returns:
        str: 处理后的 SQL 文本。
    """
    if style == "standard":
        path = f"{root_dir}/webapp/sql_data/select_table.sql"
    else:
        path = f"{root_dir}/webapp/sql_data/select_new.sql"
    sql = read_sql_language(path)
    sql = sql.replace("{table_name}", "drug_update_info")
    sql = re.sub(
        r"where\s+version\s*=\s*'\{batch_number\}'",
        "where version = :version",
        sql,
        flags=re.IGNORECASE,
    )
    return sql


def _safe_progress(
    progress_callback: Callable[[dict], None] | None,
    event: dict,
) -> None:
    if progress_callback is None:
        return
    try:
        progress_callback(event)
    except BaseException:
        return


def _normalize_sql_for_subquery(sql: str) -> str:
    s = (sql or "").strip()
    if s.endswith(";"):
        s = s[:-1].strip()
    return s


def _count_sql_rows(session, sql: str, *, version: str) -> int:
    normalized = _normalize_sql_for_subquery(sql)
    stmt = text(f"SELECT COUNT(*) FROM ({normalized}) AS export_rows")
    value = session.execute(stmt, {"version": version}).scalar()
    return int(value or 0)


def export_xlsx(
    *,
    style: ExportStyle,
    version: str,
    progress_callback: Callable[[dict], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> ExportFile:
    """
    导出指定版本号的数据为 Excel 文件。

    Args:
        style (ExportStyle): 导出样式（standard/new）。
        version (str): 版本号（必填）。

    Returns:
        ExportFile: 导出文件信息（文件名与二进制内容）。
    """
    temp_dir = _temporary_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_old_exports(temp_dir, max_age_seconds=TEMP_EXPORT_MAX_AGE_SECONDS)

    sql = _load_sql(style)
    if style == "standard":
        columns = STANDARD_COLUMNS
    else:
        columns = NEW_COLUMNS

    file = _build_export_file(style, version)

    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    ws.append(columns)

    with session_scope() as session:
        total_rows = None
        if progress_callback is not None:
            total_rows = _count_sql_rows(session, sql, version=version)
            _safe_progress(
                progress_callback,
                {"event": "meta", "total_rows": total_rows, "written_rows": 0},
            )

        written_rows = 0
        last_reported = 0
        last_reported_at = time.monotonic()
        last_cancel_checked = 0
        last_cancel_checked_at = time.monotonic()

        for row in iter_export_sql(session, sql, version=version):
            if should_cancel is not None:
                now = time.monotonic()
                if written_rows - last_cancel_checked >= 2000 or now - last_cancel_checked_at >= 1.0:
                    last_cancel_checked = written_rows
                    last_cancel_checked_at = now
                    if should_cancel():
                        raise ExportCancelled("导出已终止")
            ws.append(list(row))
            written_rows += 1
            if progress_callback is None:
                continue
            now = time.monotonic()
            if written_rows - last_reported >= 2000 or now - last_reported_at >= 1.0:
                last_reported = written_rows
                last_reported_at = now
                _safe_progress(
                    progress_callback,
                    {
                        "event": "progress",
                        "written_rows": written_rows,
                        "total_rows": total_rows,
                    },
                )

        if should_cancel is not None and should_cancel():
            raise ExportCancelled("导出已终止")

    wb.save(file.path)
    if progress_callback is not None:
        _safe_progress(
            progress_callback,
            {
                "event": "finished",
                "written_rows": written_rows,
                "total_rows": total_rows,
                "filename": file.filename,
            },
        )
    return file


def list_cached_exports() -> list[dict[str, object]]:
    temp_dir = _temporary_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_old_exports(temp_dir, max_age_seconds=TEMP_EXPORT_MAX_AGE_SECONDS)

    entries: list[dict[str, object]] = []
    for p in temp_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() != ".xlsx":
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        entries.append(
            {
                "filename": p.name,
                "size_bytes": int(stat.st_size),
                "mtime": float(stat.st_mtime),
                "mtime_text": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    entries.sort(key=lambda x: float(x.get("mtime") or 0), reverse=True)
    return entries


def resolve_cached_export_file(filename: str) -> Path | None:
    name = Path(filename or "").name
    if not name.endswith(".xlsx"):
        return None
    temp_dir = _temporary_dir()
    path = temp_dir / name
    if not path.exists() or not path.is_file():
        return None
    return path
