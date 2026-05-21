from __future__ import annotations

from typing import Optional

from api.medical_info import get_drug_update_info


async def fetch_drug_update_page(
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
    抓取“药品更新信息”单页数据（HTTP 接口封装）。

    Args:
        version (str): 版本号（batchNumber）。
        page (int): 页码。
        rows (int): 每页条数。
        goodsCode (str | None): 药品代码筛选（可选）。
        registeredProductName (str | None): 注册产品名称筛选（可选）。
        approvalCode (str | None): 批准文号筛选（可选）。
        companyNameSc (str | None): 企业名称筛选（可选）。

    Returns:
        dict: 接口返回 JSON 数据。

    Raises:
        ValueError: 当接口返回非 200 状态码时抛出。
    """
    data = await get_drug_update_info(
        batchNumber=version,
        goodsCode=goodsCode,
        registeredProductName=registeredProductName,
        approvalCode=approvalCode,
        companyNameSc=companyNameSc,
        page=page,
        rows=rows,
    )
    if isinstance(data, int):
        raise ValueError(f"接口返回状态码 {data}")
    return data
