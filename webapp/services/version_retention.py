from __future__ import annotations

"""
版本保留策略（按 version 清理历史数据）。

用于控制 drug_update_info 表的数据量：仅保留最近 N 个版本号（默认 5）。
版本号格式为 yyyyMMdd（例如 20260515），可直接按字符串倒序排序表示“由新到旧”。
"""

import os
from dataclasses import dataclass

from webapp.db import session_scope
from webapp.repositories.drug_update_repo import delete_by_versions, list_versions


DEFAULT_KEEP_VERSION_NUMBER = 5


def get_keep_version_number() -> int:
    """
    获取版本保留数量（KEEP_VERSION_NUMBER）。

    配置来源：环境变量（通常由项目根目录 .env 加载）。
    当未配置/为空/非整数/<=0 时，返回兜底值 5。

    Returns:
        int: 需要保留的版本数量。
    """
    v = (os.getenv("KEEP_VERSION_NUMBER") or "").strip()
    if not v:
        return DEFAULT_KEEP_VERSION_NUMBER
    try:
        n = int(v)
    except ValueError:
        return DEFAULT_KEEP_VERSION_NUMBER
    if n <= 0:
        return DEFAULT_KEEP_VERSION_NUMBER
    return n


@dataclass(frozen=True)
class VersionCleanupResult:
    """
    版本清理结果。

    Attributes:
        keep (int): 保留的版本数量。
        total_versions (int): 清理前版本总数。
        kept_versions (list[str]): 实际保留的版本列表（倒序）。
        deleted_versions (list[str]): 实际删除的版本列表（倒序）。
        deleted_rows (int): 删除的行数。
    """
    keep: int
    total_versions: int
    kept_versions: list[str]
    deleted_versions: list[str]
    deleted_rows: int


def cleanup_old_versions(*, keep: int | None = None) -> VersionCleanupResult:
    """
    清理 drug_update_info 的旧版本数据，仅保留最近 N 个版本。

    Args:
        keep (int | None): 指定保留数量；为空则读取 KEEP_VERSION_NUMBER。

    Returns:
        VersionCleanupResult: 清理结果（含删除版本列表与删除行数）。
    """
    effective_keep = keep if keep is not None else get_keep_version_number()
    if effective_keep <= 0:
        effective_keep = DEFAULT_KEEP_VERSION_NUMBER

    with session_scope() as session:
        versions = list_versions(session)
        total = len(versions)
        if total <= effective_keep:
            return VersionCleanupResult(
                keep=effective_keep,
                total_versions=total,
                kept_versions=versions,
                deleted_versions=[],
                deleted_rows=0,
            )

        kept = versions[:effective_keep]
        to_delete = versions[effective_keep:]
        deleted_rows = delete_by_versions(session, to_delete)
        return VersionCleanupResult(
            keep=effective_keep,
            total_versions=total,
            kept_versions=kept,
            deleted_versions=to_delete,
            deleted_rows=deleted_rows,
        )
