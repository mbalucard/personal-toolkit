from __future__ import annotations

from datetime import date, datetime, timezone
from functools import wraps
from math import ceil

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from webapp.config import Settings
from webapp.db import session_scope
from webapp.models import User, UserLoginLog


bp = Blueprint("user_mgmt", __name__, url_prefix="/users")


def _get_str(form, name: str) -> str:
    return (form.get(name) or "").strip()


def _get_bool(form, name: str) -> bool:
    """
    从表单/查询参数中解析布尔值。

    兼容 HTML checkbox 常见取值：1/true/on/yes（不区分大小写）。

    Args:
        form: request.form 或 request.args（支持 .get）。
        name (str): 字段名。

    Returns:
        bool: 解析后的布尔值。
    """
    value = (form.get(name) or "").strip().lower()
    return value in {"1", "true", "on", "yes"}


def admin_required(func_):
    """
    管理员权限校验装饰器。

    仅允许 current_user.is_admin 为真时访问，否则返回 403。
    """
    @wraps(func_)
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return func_(*args, **kwargs)

    return wrapped


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.get("/login-logs")
@login_required
@admin_required
def login_logs():
    settings = Settings()

    start_date_raw = _get_str(request.args, "start_date")
    end_date_raw = _get_str(request.args, "end_date")
    username = _get_str(request.args, "username") or None

    page = int(request.args.get("page") or 1)
    if page < 1:
        page = 1

    page_size = int(request.args.get("page_size") or settings.default_page_size)
    if page_size not in settings.allowed_page_sizes:
        page_size = settings.default_page_size

    start_date = _parse_date(start_date_raw)
    end_date = _parse_date(end_date_raw)

    error = ""
    if start_date_raw and start_date is None:
        error = "开始日期格式错误"
    elif end_date_raw and end_date is None:
        error = "结束日期格式错误"

    with session_scope() as session:
        query = session.query(UserLoginLog)
        if username:
            query = query.filter(UserLoginLog.username.ilike(f"%{username}%"))
        if start_date is not None:
            query = query.filter(func.date(UserLoginLog.login_at) >= start_date)
        if end_date is not None:
            query = query.filter(func.date(UserLoginLog.login_at) <= end_date)

        total = query.count()
        items = (
            query.order_by(UserLoginLog.login_at.desc(), UserLoginLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    total_pages = max(1, int(ceil(total / page_size))) if page_size else 1

    return render_template(
        "login_logs.html",
        filters={
            "start_date": start_date_raw,
            "end_date": end_date_raw,
            "username": username or "",
        },
        page=page,
        page_size=page_size,
        allowed_page_sizes=settings.allowed_page_sizes,
        total=total,
        total_pages=total_pages,
        items=items,
        error=error,
    )


@bp.get("/settings")
@login_required
@admin_required
def user_settings():
    settings = Settings()
    success = _get_str(request.args, "success")
    error = _get_str(request.args, "error")
    edit_id_raw = _get_str(request.args, "edit_id")
    edit_id = int(edit_id_raw) if edit_id_raw.isdigit() else None
    status_raw = _get_str(request.args, "status") or "1"
    status = 1 if status_raw == "1" else 0
    now = datetime.now(timezone.utc)

    with session_scope() as session:
        users = (
            session.query(User)
            .filter(User.is_active == status)
            .order_by(User.id.asc())
            .all()
        )
        edit_user = None
        if edit_id is not None:
            edit_user = session.query(User).filter(User.id == edit_id).first()

        locked_until_map: dict[int, datetime | None] = {}
        locked_user_ids: set[int] = set()
        for u in users:
            locked_until = u.locked_until
            if locked_until is not None and locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            locked_until_map[u.id] = locked_until
            if locked_until is not None and locked_until > now:
                locked_user_ids.add(u.id)

        return render_template(
            "user_settings.html",
            users=users,
            edit_user=edit_user,
            success=success,
            error=error,
            status=status,
            locked_user_ids=locked_user_ids,
            locked_until_map=locked_until_map,
            admin_username=settings.admin_username,
        )


@bp.post("/create")
@login_required
@admin_required
def create_user():
    status = _get_str(request.form, "status") or "1"
    username = _get_str(request.form, "username")
    name = _get_str(request.form, "name") or None
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    is_admin = _get_bool(request.form, "is_admin")

    if not username:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                open="create",
                error="用户名不能为空",
            )
        )
    if not password:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                open="create",
                error="密码不能为空",
            )
        )
    if password != password_confirm:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                open="create",
                error="两次输入的密码不一致",
            )
        )

    try:
        with session_scope() as session:
            session.add(
                User(
                    username=username,
                    name=name,
                    password_hash=generate_password_hash(password),
                    is_admin=is_admin,
                    is_active=1,
                )
            )
    except IntegrityError:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                open="create",
                error="用户名已存在",
            )
        )

    return redirect(url_for("user_mgmt.user_settings", status=status, success="用户已创建"))


@bp.post("/update/<int:user_id>")
@login_required
@admin_required
def update_user(user_id: int):
    status = _get_str(request.form, "status") or "1"
    username = _get_str(request.form, "username")
    name = _get_str(request.form, "name") or None
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    is_admin = _get_bool(request.form, "is_admin")

    if not username:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                edit_id=user_id,
                error="用户名不能为空",
            )
        )

    if password and password != password_confirm:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                edit_id=user_id,
                error="两次输入的密码不一致",
            )
        )

    try:
        with session_scope() as session:
            settings = Settings()
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return redirect(
                    url_for("user_mgmt.user_settings", status=status, error="用户不存在")
                )

            if user.username == settings.admin_username and not is_admin:
                return redirect(
                    url_for(
                        "user_mgmt.user_settings",
                        status=status,
                        edit_id=user_id,
                        error="admin 账号不允许取消管理员权限",
                    )
                )

            user.username = username
            user.name = name
            if user.username == settings.admin_username:
                user.is_admin = True
                user.is_active = 1
            else:
                user.is_admin = is_admin
            if password:
                user.password_hash = generate_password_hash(password)
    except IntegrityError:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                status=status,
                edit_id=user_id,
                error="用户名已存在",
            )
        )

    return redirect(url_for("user_mgmt.user_settings", status=status, success="用户已更新"))


@bp.post("/delete/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id: int):
    status = _get_str(request.form, "status") or "1"
    if current_user.get_id() and int(current_user.get_id()) == user_id:
        return redirect(
            url_for("user_mgmt.user_settings", status=status, error="不能删除当前登录用户")
        )

    with session_scope() as session:
        settings = Settings()
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return redirect(
                url_for("user_mgmt.user_settings", status=status, error="用户不存在")
            )
        if user.username == settings.admin_username:
            return redirect(
                url_for("user_mgmt.user_settings", status=status, error="admin 账号不允许删除")
            )
        if user.is_admin:
            return redirect(
                url_for(
                    "user_mgmt.user_settings",
                    status=status,
                    error="管理员账号不允许删除，请先取消管理员权限",
                )
            )
        user.is_active = 0

    return redirect(url_for("user_mgmt.user_settings", status=status, success="用户已删除"))


@bp.post("/restore/<int:user_id>")
@login_required
@admin_required
def restore_user(user_id: int):
    """
    将用户从“不可用”恢复为“可用”。

    Args:
        user_id (int): 用户 ID。

    Returns:
        Response: 重定向回用户设置页。
    """
    status = _get_str(request.form, "status") or "1"
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return redirect(
                url_for("user_mgmt.user_settings", status=status, error="用户不存在")
            )
        user.is_active = 1

    return redirect(url_for("user_mgmt.user_settings", status=status, success="用户已恢复"))


@bp.post("/unlock/<int:user_id>")
@login_required
@admin_required
def unlock_user(user_id: int):
    """
    手动解锁用户账号。

    将 failed_login_attempts 清零，并清空 locked_until，使账号可立即重试登录。

    Args:
        user_id (int): 用户 ID。

    Returns:
        Response: 重定向回用户设置页。
    """
    status = _get_str(request.form, "status") or "1"
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return redirect(
                url_for("user_mgmt.user_settings", status=status, error="用户不存在")
            )
        user.failed_login_attempts = 0
        user.locked_until = None

    return redirect(url_for("user_mgmt.user_settings", status=status, success="用户已解锁"))
