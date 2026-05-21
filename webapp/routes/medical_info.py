from __future__ import annotations

from math import ceil
from threading import Thread

from flask import Blueprint, Response, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from webapp.config import Settings
from webapp.db import session_scope
from webapp.repositories.drug_update_repo import list_versions, query_page
from webapp.services.export import ExportCancelled, export_xlsx, list_cached_exports, resolve_cached_export_file
from webapp.services.export_tasks import create_job, get_job, update_job


bp = Blueprint("medical_info", __name__)


@bp.get("/")
def index():
    """
    根路径入口。

    已登录用户跳转到数据查询页，未登录用户跳转到登录页。

    Returns:
        Response: 重定向响应。
    """
    if current_user.is_authenticated:
        return redirect(url_for("medical_info.list_page"))
    return redirect(url_for("auth.login"))


@bp.get("/medical-info")
@login_required
def list_page():
    """
    数据查询与分页页面。

    version 为必填筛选条件；其余筛选条件可选。分页参数 page/page_size 用于数据库层面分页。

    Returns:
        str: 渲染后的 HTML。
    """
    settings = Settings()

    version = (request.args.get("version") or "").strip()
    goodscode = (request.args.get("goodscode") or "").strip() or None
    registeredproductname = (request.args.get("registeredproductname") or "").strip() or None
    goodsstandardcode = (request.args.get("goodsstandardcode") or "").strip() or None
    approvalcode = (request.args.get("approvalcode") or "").strip() or None

    page = int(request.args.get("page") or 1)
    page_size = int(request.args.get("page_size") or settings.default_page_size)
    if page_size not in settings.allowed_page_sizes:
        page_size = settings.default_page_size

    with session_scope() as session:
        versions = list_versions(session)
        result = None
        if version:
            result = query_page(
                session,
                version=version,
                page=page,
                page_size=page_size,
                goodscode=goodscode,
                registeredproductname=registeredproductname,
                goodsstandardcode=goodsstandardcode,
                approvalcode=approvalcode,
            )

    total_pages = None
    if result is not None:
        total_pages = max(1, int(ceil(result.total / page_size))) if page_size else 1

    return render_template(
        "medical_info.html",
        versions=versions,
        selected_version=version,
        filters={
            "goodscode": goodscode or "",
            "registeredproductname": registeredproductname or "",
            "goodsstandardcode": goodsstandardcode or "",
            "approvalcode": approvalcode or "",
        },
        page=page,
        page_size=page_size,
        allowed_page_sizes=settings.allowed_page_sizes,
        result=result,
        total_pages=total_pages,
    )


@bp.get("/export")
@login_required
def export():
    """
    导出 Excel 文件（两种样式：standard/new）。

    Args:
        style (str): 导出样式，取值为 "standard" 或 "new"。
        version (str): 版本号（必填）。

    Returns:
        Response: Excel 文件下载响应。
    """
    style = (request.args.get("style") or "").strip()
    version = (request.args.get("version") or "").strip()
    if style not in {"standard", "new"}:
        return Response("style 参数错误", status=400)
    if not version:
        return Response("version 不能为空", status=400)

    file = export_xlsx(style=style, version=version)
    return send_file(
        file.path,
        as_attachment=True,
        download_name=file.filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _run_export_job(job_id: str, payload: dict) -> None:
    try:
        update_job(job_id, {"status": "running", "message": "正在生成导出文件..."})

        def should_cancel() -> bool:
            job = get_job(job_id) or {}
            return bool(job.get("cancel_requested"))

        def on_progress(event: dict) -> None:
            event_type = event.get("event")
            if event_type == "meta":
                update_job(
                    job_id,
                    {
                        "total_rows": event.get("total_rows"),
                        "written_rows": int(event.get("written_rows") or 0),
                    },
                )
            elif event_type == "progress":
                update_job(
                    job_id,
                    {
                        "total_rows": event.get("total_rows"),
                        "written_rows": int(event.get("written_rows") or 0),
                    },
                )
            elif event_type == "finished":
                update_job(
                    job_id,
                    {
                        "total_rows": event.get("total_rows"),
                        "written_rows": int(event.get("written_rows") or 0),
                        "filename": event.get("filename"),
                    },
                )

        file = export_xlsx(
            style=payload["style"],
            version=payload["version"],
            progress_callback=on_progress,
            should_cancel=should_cancel,
        )
        update_job(
            job_id,
            {
                "status": "success",
                "filename": file.filename,
                "message": "导出已完成",
            },
        )
    except ExportCancelled as exc:
        update_job(
            job_id,
            {
                "status": "cancelled",
                "message": str(exc) or "导出已终止",
            },
        )
    except BaseException as exc:
        update_job(job_id, {"status": "error", "message": str(exc)})


@bp.post("/export/start")
@login_required
def export_start():
    data = request.get_json(silent=True) or request.form
    style = (data.get("style") or "").strip()
    version = (data.get("version") or "").strip()
    if style not in {"standard", "new"}:
        return jsonify({"ok": False, "error": "style 参数错误"}), 400
    if not version:
        return jsonify({"ok": False, "error": "version 不能为空"}), 400

    job_id = create_job(
        {
            "status": "queued",
            "style": style,
            "version": version,
            "cancel_requested": False,
            "total_rows": None,
            "written_rows": 0,
            "filename": None,
            "message": "任务已创建，等待开始",
        }
    )
    Thread(target=_run_export_job, args=(job_id, {"style": style, "version": version}), daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})


@bp.get("/export/status/<job_id>")
@login_required
def export_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    return jsonify({"ok": True, "job": job})


@bp.post("/export/cancel/<job_id>")
@login_required
def export_cancel(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    status = job.get("status")
    if status in {"success", "error", "cancelled"}:
        return jsonify({"ok": False, "error": "任务已结束，无法终止"}), 400
    update_job(
        job_id,
        {
            "cancel_requested": True,
            "message": "已收到终止请求，正在停止...",
        },
    )
    return jsonify({"ok": True})



@bp.get("/export/files")
@login_required
def export_files():
    return jsonify({"ok": True, "files": list_cached_exports()})

@bp.get("/export/download/<filename>")
@login_required
def export_cached_download(filename: str):
    path = resolve_cached_export_file(filename)
    if path is None:
        return Response("文件不存在", status=404)
    return send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
