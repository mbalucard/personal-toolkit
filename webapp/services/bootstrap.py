from __future__ import annotations

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from webapp.config import Settings
from webapp.db import session_scope
from webapp.models import User


def ensure_drug_update_unique_index() -> None:
    """
    确保 drug_update_info 表存在唯一索引 (version, goodscode)。

    Returns:
        None: 无返回值。
    """
    with session_scope() as session:
        session.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_drug_update_info_version_goodscode "
                "ON drug_update_info (version, goodscode)"
            )
        )


def ensure_user_columns() -> None:
    """
    确保 users 表包含系统所需的增量字段。

    当前项目未使用 Alembic，采用“启动时自动补列”的方式兼容存量数据库。

    Returns:
        None: 无返回值。
    """
    with session_scope() as session:
        session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(64)"))
        session.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        session.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active SMALLINT NOT NULL DEFAULT 1"
            )
        )
        session.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts SMALLINT NOT NULL DEFAULT 0"
            )
        )
        session.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ")
        )


def ensure_user_login_log_indexes() -> None:
    with session_scope() as session:
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_login_logs_login_at "
                "ON user_login_logs (login_at DESC)"
            )
        )
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_login_logs_username "
                "ON user_login_logs (username)"
            )
        )


def ensure_admin_user(settings: Settings) -> None:
    """
    确保管理员账号存在。

    若管理员账号不存在则创建；当 ADMIN_PASSWORD 未配置时会抛错，避免生成无密码账号。

    Args:
        settings (Settings): 应用配置（包含管理员用户名与密码）。

    Returns:
        None: 无返回值。

    Raises:
        ValueError: 当 ADMIN_PASSWORD 未配置且需要创建管理员账号时抛出。
    """
    with session_scope() as session:
        existing = (
            session.query(User).filter(User.username == settings.admin_username).first()
        )
        if existing is not None:
            existing.is_admin = True
            existing.is_active = 1
            return
        if not settings.admin_password:
            raise ValueError("ADMIN_PASSWORD 未配置，无法初始化管理员账号")

        user = User(
            username=settings.admin_username,
            password_hash=generate_password_hash(settings.admin_password),
            is_admin=True,
            is_active=1,
        )
        session.add(user)
