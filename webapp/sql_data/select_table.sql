select goodscode,
    registeredproductname,
    registeredmedicinemodel,
    registeredoutlook,
    goodsname,
    realitymedicinemodel,
    realityoutlook,
    materialname,
    factor,
    minunit,
    unit,
    "traceCodeFlag",
    companynamesc,
    approvalcode,
    goodsstandardcode,
    productinsurancetype,
    productcode,
    productname,
    productmedicinemodel,
    productremark
from {table_name}
where version = '{batch_number}'
order by goodscode
;
