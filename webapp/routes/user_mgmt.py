from __future__ import annotations

from datetime import date, datetime
from math import ceil

from flask import Blueprint, redirect, render_template, request, url_for
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


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.get("/login-logs")
@login_required
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
def user_settings():
    success = _get_str(request.args, "success")
    error = _get_str(request.args, "error")
    edit_id_raw = _get_str(request.args, "edit_id")
    edit_id = int(edit_id_raw) if edit_id_raw.isdigit() else None

    with session_scope() as session:
        users = session.query(User).order_by(User.id.asc()).all()
        edit_user = None
        if edit_id is not None:
            edit_user = session.query(User).filter(User.id == edit_id).first()

        return render_template(
            "user_settings.html",
            users=users,
            edit_user=edit_user,
            success=success,
            error=error,
        )


@bp.post("/create")
@login_required
def create_user():
    username = _get_str(request.form, "username")
    name = _get_str(request.form, "name") or None
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if not username:
        return redirect(
            url_for("user_mgmt.user_settings", open="create", error="用户名不能为空")
        )
    if not password:
        return redirect(url_for("user_mgmt.user_settings", open="create", error="密码不能为空"))
    if password != password_confirm:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
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
                )
            )
    except IntegrityError:
        return redirect(url_for("user_mgmt.user_settings", open="create", error="用户名已存在"))

    return redirect(url_for("user_mgmt.user_settings", success="用户已创建"))


@bp.post("/update/<int:user_id>")
@login_required
def update_user(user_id: int):
    username = _get_str(request.form, "username")
    name = _get_str(request.form, "name") or None
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if not username:
        return redirect(
            url_for("user_mgmt.user_settings", edit_id=user_id, error="用户名不能为空")
        )

    if password and password != password_confirm:
        return redirect(
            url_for(
                "user_mgmt.user_settings",
                edit_id=user_id,
                error="两次输入的密码不一致",
            )
        )

    try:
        with session_scope() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return redirect(url_for("user_mgmt.user_settings", error="用户不存在"))

            user.username = username
            user.name = name
            if password:
                user.password_hash = generate_password_hash(password)
    except IntegrityError:
        return redirect(
            url_for("user_mgmt.user_settings", edit_id=user_id, error="用户名已存在")
        )

    return redirect(url_for("user_mgmt.user_settings", success="用户已更新"))


@bp.post("/delete/<int:user_id>")
@login_required
def delete_user(user_id: int):
    if current_user.get_id() and int(current_user.get_id()) == user_id:
        return redirect(url_for("user_mgmt.user_settings", error="不能删除当前登录用户"))

    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return redirect(url_for("user_mgmt.user_settings", error="用户不存在"))
        session.delete(user)

    return redirect(url_for("user_mgmt.user_settings", success="用户已删除"))
