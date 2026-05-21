import os
from tools.other import random_user_agent, timestamp
from httpx import AsyncClient
from typing import Optional
from dotenv import load_dotenv
load_dotenv()


base_url = os.getenv('MedicalInsuranceBaseURL')
time_out = int(os.getenv('MedicalInsuranceTimeOut'))


async def get_drug_info(
        registeredProductName: Optional[str] = None,
        goodsCode: Optional[str] = None,
        companyNameSc: Optional[str] = None,
        approvalCode: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",) -> dict | int:
    """
    西药中成药信息

    Args:
        registeredProductName (str, None): 注册产品名称. Defaults to None.
        goodsCode (str, None): 药品代码. Defaults to None.
        companyNameSc (str, None): 药品注册企业. Defaults to None.
        approvalCode (str, None): 批准文号. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序

    Returns:
        dict | int: 药品信息或状态码
    """

    url = f"{base_url}/yp/stdGoodsPublic/getStdGoodsPublicData.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "registeredProductName": registeredProductName,
        "goodsCode": goodsCode,
        "companyNameSc": companyNameSc,
        "approvalCode": approvalCode,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def drug_classification_and_name_inquity(
        classifyCode4: Optional[str] = None,
        commonnamecode: Optional[str] = None,
        commonname: Optional[str] = None,
        matrialcode: Optional[str] = None,
        matrial: Optional[str] = None,
        productAttribute: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",
        versionId: Optional[str] = None,
) -> dict | int:
    """
    药品分类和通用名查询

    Args:
        classifyCode4 (str, None): 药品类别代码. Defaults to None.
        commonnamecode (str, None): 通用名代码. Defaults to None.
        commonname (str, None): 通用名. Defaults to None.
        matrialcode (str, None): 剂型代码. Defaults to None.
        matrial (str, None): 剂型. Defaults to None.
        productAttribute (str, None): 药品大类
            - X-西药
            - Z-中成药
            - None-全部
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
        versionId (str, None): 版本号. Defaults to None.

    Returns:
        dict | int: 药品分类和通用名查询结果或状态码
    """
    url = f"{base_url}/yp/stdGoods/getCensusDataNew.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "classifyCode4": classifyCode4,
        "commonnamecode": commonnamecode,
        "commonname": commonname,
        "matrialcode": matrialcode,
        "matrial": matrial,
        "productAttribute": productAttribute,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "versionId": versionId,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def get_drug_update_info(
        batchNumber: str,
        goodsCode: Optional[str] = None,
        registeredProductName: Optional[str] = None,
        approvalCode: Optional[str] = None,
        companyNameSc: Optional[str] = None,
        _search: str = 'false',
        rows: int = 50,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",) -> dict | int:
    """
    获取药品更新信息

    Args:
        batchNumber (str): 更新日期,
            - 格式: yyyyMMdd
        goodsCode (str, None): 药品代码. Defaults to None.
        registeredProductName (str, None): 注册产品名称. Defaults to None.
        approvalCode (str, None): 批准文号. Defaults to None.
        companyNameSc (str, None): 药品注册企业. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 50.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序

    Returns:
        dict | int: 药品更新信息或状态码
    """
    url = f"{base_url}/yp/getPublishGoodsDataInfo.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "batchNumber": batchNumber,
        "goodsCode": goodsCode,
        "registeredProductName": registeredProductName,
        "approvalCode": approvalCode,
        "companyNameSc": companyNameSc,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def decoction_pieces_info(
        piecesCode: Optional[str] = None,
        piecesName: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",) -> dict | int:
    """
    中药饮片信息

    Args:
        piecesCode (str, None): 中药饮片代码. Defaults to None.
        piecesName (str, None): 中药饮片名称. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 中药饮片信息或状态码
    """
    url = f"{base_url}/yp/stdChineseMedicinalDecoctionPieces/getPiecesRkData.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "piecesCode": piecesCode,
        "piecesName": piecesName,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def formula_granules_info(
        particleCode: Optional[str] = None,
        particleName: Optional[str] = None,
        parRegcardNumber: Optional[str] = None,
        companyNameSc: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",) -> dict | int:
    """
    中药配方颗粒信息

    Args:
        particleCode (str, None): 中药配方颗粒代码. Defaults to None.
        particleName (str, None): 中药配方颗粒名称. Defaults to None.
        parRegcardNumber (str, None): 上市备案号. Defaults to None.
        companyNameSc (str, None): 生产企业. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 中药配方颗粒信息或状态码
    """
    url = f"{base_url}/yp/stdCnMedDecParAllRk/getStdCnMedDecParPublishFromRkList.html"

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "particleCode": particleCode,
        "particleName": particleName,
        "parRegcardNumber": parRegcardNumber,
        "companyNameSc": companyNameSc,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def institutional_preparation_info(
        preparationCode: Optional[str] = None,
        preparationName: Optional[str] = None,
        preparationPrename: Optional[str] = None,
        preparationApprovalcode: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",
) -> dict | int:
    """
    医疗机构制剂信息

    Args:
        preparationCode (str, None): 制剂代码. Defaults to None.
        preparationName (str, None): 医疗机构名称. Defaults to None.
        preparationPrename (str, None): 制剂名称. Defaults to None.
        preparationApprovalcode (str, None): 批准文号. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 医疗机构制剂信息或状态码
    """
    url = f"{base_url}/yp/stdChineseMedicinalDecoctionPieces/getYnzjHospreparationRkData.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "preparationCode": preparationCode,
        "preparationName": preparationName,
        "preparationPrename": preparationPrename,
        "preparationApprovalcode": preparationApprovalcode,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def medical_consumables_class_info(
        catalogname1: Optional[str] = None,
        catalogname2: Optional[str] = None,
        catalogname3: Optional[str] = None,
        commonname: Optional[str] = None,
        matrial: Optional[str] = None,
        characteristic: Optional[str] = None,
        genericname: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",
) -> dict | int:
    """
    医用耗材分类目录

    Args:
        catalogname1 (str, None): 一级分类. Defaults to None.
        catalogname2 (str, None): 二级分类. Defaults to None.
        catalogname3 (str, None): 三级分类. Defaults to None.
        commonname (str, None): 医保通用名分类. Defaults to None.
        matrial (str, None): 耗材材质. Defaults to None.
        characteristic (str, None): 规格(特征、参数). Defaults to None.
        genericname (str, None): 医保通用名. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 医用耗材分类目录或状态码
    """
    url = f"{base_url}/hc/stdSpecification/getStdSpecificationListDataCompanyReport.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "catalogname1": catalogname1,
        "catalogname2": catalogname2,
        "catalogname3": catalogname3,
        "commonname": commonname,
        "matrial": matrial,
        "characteristic": characteristic,
        "genericname": genericname,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def medical_consumables_info(
        specificationCode: Optional[str] = None,
        commonname: Optional[str] = None,
        companyName: Optional[str] = None,
        catalogname1: Optional[str] = None,
        catalogname2: Optional[str] = None,
        catalogname3: Optional[str] = None,
        regcardNm: Optional[str] = None,
        genericname: Optional[str] = r"%%",
        releaseVersion: Optional[str] = None,
        _search: str = 'false',
        rows: int = 15,
        page: int = 1,
        sidx: Optional[str] = None,
        sord: str = "asc",
) -> dict | int:
    """
    医用耗材信息

    Args:
        specificationCode (str, None): 规格编码. Defaults to None.
        commonname (str, None): 医保通用名分类. Defaults to None.
        companyName (str, None): 耗材企业. Defaults to None.
        catalogname1 (str, None): 一级分类. Defaults to None.
        catalogname2 (str, None): 二级分类. Defaults to None.
        catalogname3 (str, None): 三级分类. Defaults to None.
        regcardNm (str, None): 注册名称. Defaults to None.
        genericname (str, None): 医保通用名. Defaults to None.
        releaseVersion (str, None): 发布版本. Defaults to None.  
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 医用耗材信息或状态码
    """
    url = f"{base_url}/hc/stdPublishData/getNewPublishRelationDataList.html"

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "specificationCode": specificationCode,
        "commonname": commonname,
        "companyName": companyName,
        "catalogname1": catalogname1,
        "catalogname2": catalogname2,
        "catalogname3": catalogname3,
        "regcardNm": regcardNm,
        "genericname": genericname,
        "releaseVersion": releaseVersion,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def medical_consumables_details(
    specificationCode: str,
    regcardnm: Optional[str] = None,
    productName: Optional[str] = None,
    specification: Optional[str] = None,
    model: Optional[str] = None,
    productid: Optional[str] = None,
    regcardid: Optional[str] = None,
    releaseVersion: Optional[str] = None,
    productNameHide: Optional[str] = None,
    _search: str = "false",
    rows: int = 15,
    page: int = 1,
    sidx: Optional[str] = None,
    sord: str = "asc",

) -> dict | int:
    """
    医用耗材信息-详情

    Args:
        specificationCode (str): 规格编码. Defaults to None.
        regcardnm (str, None): 注册备案号. Defaults to None.
        productName (str, None): 单件产品名称. Defaults to None.
        specification (str, None): 规格. Defaults to None.
        model (str, None): 型号. Defaults to None.
        productid (str, None): 未知. Defaults to None.
        regcardid (str, None): 未知. Defaults to None.
        releaseVersion (str, None): 未知. Defaults to None.
        productNameHide (str, None): 未知. Defaults to None.
        _search (str): 是否搜索. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 医用耗材详情或状态码
    """
    url = f"{base_url}/hc/stdYgbData/getPublicHcDataList.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "specificationCode": specificationCode,
        "regcardnm": regcardnm,
        "productName": productName,
        "specification": specification,
        "model": model,
        "productid": productid,
        "regcardid": regcardid,
        "releaseVersion": releaseVersion,
        "productNameHide": productNameHide,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def vitro_diagnostic_reagent_info(
    code: Optional[str] = None,
    catalogName1: Optional[str] = None,
    catalogName2: Optional[str] = None,
    catalogName3: Optional[str] = None,
    testingFullDesc: Optional[str] = None,
    reagentUseType: Optional[int] = None,
    reagentCheckType: Optional[int] = None,
    productName: Optional[str] = None,
    regcardNm: Optional[str] = None,
    companyName: Optional[str] = None,
    _search: str = "false",
    rows: int = 15,
    page: int = 1,
    sidx: Optional[str] = None,
    sord: str = "asc",
) -> dict | int:
    """
    体外诊断试剂信息
    Args:
        code (str, None): 体外诊断试剂代码 type:str
        catalogName1 (str, None): 一级分类 type:str
        catalogName2 (str, None): 二级分类 type:str
        catalogName3 (str, None): 三级分类 type:str
        testingFullDesc (str, None): 测试指标 type:str
        reagentUseType (int, None): 应用方式 type:int
            - 0-通用型
            - 1-专用型
            - None-全部
        reagentCheckType (int, None): 检测类型 type:int
            - 1-单检测
            - 2-联检
            - None-全部
        productName (str, None): 单件产品名称 type:str
        regcardNm (str, None): 注册备案证号 type:str
        companyName (str, None): 企业名称 type:str
        _search (str): 未知. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 体外诊断试剂信息或状态码
    """
    url = f"{base_url}/sj/publish/cms_sj/product.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "code": code,
        "catalogName1": catalogName1,
        "catalogName2": catalogName2,
        "catalogName3": catalogName3,
        "testingFullDesc": testingFullDesc,
        "reagentUseType": reagentUseType,
        "reagentCheckType": reagentCheckType,
        "productName": productName,
        "regcardNm": regcardNm,
        "companyName": companyName,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def vitro_diagnostic_reagent_test_indicators_catalogue(
    testingZbCode: Optional[str] = None,
    testingClassName: Optional[str] = None,
    testingZbName: Optional[str] = None,
    _search: str = "false",
    rows: int = 15,
    page: int = 1,
    sidx: Optional[str] = None,
    sord: str = "asc",
) -> dict | int:
    """
    体外诊断试剂检测指标目录
    Args:
        testingZbCode (str, None): 检测指标代码 type:str
        testingClassName (str, None): 检测类别名称 type:str
        testingZbName (str, None): 检测指标名称 type:str
        _search (str): 未知. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 15.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 体外诊断试剂检测指标目录或状态码
    """
    url = f"{base_url}/sj/publish/cms_sj/testing_index.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(), }
    payload = {
        "testingZbCode": testingZbCode,
        "testingClassName": testingClassName,
        "testingZbName": testingZbName,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def vitro_diagnostic_reagent_class_catalogue(
    specificationCode: Optional[str] = None,
    catalogName1: Optional[str] = None,
    catalogName2: Optional[str] = None,
    catalogName3: Optional[str] = None,
    _search: str = "false",
    rows: int = 25,
    page: int = 1,
    sidx: Optional[str] = None,
    sord: str = "asc",
) -> dict | int:
    """
    体外诊断试剂分类目录
    Args:
        specificationCode (str, None): 体外诊断试剂分类代码 type:str default:None
        catalogName1 (str, None): 一级分类 type:str default:None
        catalogName2 (str, None): 二级分类 type:str default:None
        catalogName3 (str, None): 三级分类 type:str default:None
        _search (str): 未知. Defaults to 'false'.
        rows (int): 每页显示记录数. Defaults to 25.
        page (int): 当前页码. Defaults to 1.
        sidx (str, None): 排序字段. Defaults to None.
        sord (str): 排序顺序. Defaults to "asc".
            - "asc": 升序
            - "desc": 降序
    Returns:
        dict | int: 体外诊断试剂分类目录或状态码
    """
    url = f"{base_url}/sj/publish/cms_sj/specification.html"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": random_user_agent(),
    }
    payload = {
        "specificationCode": specificationCode,
        "catalogName1": catalogName1,
        "catalogName2": catalogName2,
        "catalogName3": catalogName3,
        "_search": _search,
        "rows": rows,
        "page": page,
        "sidx": sidx,
        "sord": sord,
        "nd": timestamp(),
    }
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, data=payload, timeout=time_out)
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


if __name__ == "__main__":
    import asyncio
    goods_name = "地喹氯铵含片"
    company_name = "华润三九现代中药制药有限公司"
    specificationCode = "C0101010011303807555"
    # data = asyncio.run(get_drug_info(registeredProductName=goods_name, companyNameSc=company_name))
    # data = asyncio.run(decoction_pieces_info())
    # data = asyncio.run(formula_granules_info(companyNameSc=company_name))
    # data = asyncio.run(institutional_preparation_info())
    # data = asyncio.run(medical_consumables_info())
    # data = asyncio.run(drug_classification_and_name_inquity())
    # data = asyncio.run(medical_consumables_info())
    # data = asyncio.run(medical_consumables_details(
    #     specificationCode=specificationCode
    # ))
    # data = asyncio.run(vitro_diagnostic_reagent_info())
    # data = asyncio.run(vitro_diagnostic_reagent_test_indicators_catalogue())
    data = asyncio.run(get_drug_update_info(
        batchNumber="20260306"
    ))
    print(data)
