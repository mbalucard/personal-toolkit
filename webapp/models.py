from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(UserMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserLoginLog(Base):
    __tablename__ = "user_login_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DrugUpdateInfo(Base):
    __tablename__ = "drug_update_info"

    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    goodscode: Mapped[str] = mapped_column(String(255), primary_key=True)

    businessLicense: Mapped[Optional[str]] = mapped_column("businessLicense", String(128))
    productcode: Mapped[Optional[str]] = mapped_column("productcode", String(255))
    materialname: Mapped[Optional[str]] = mapped_column("materialname", String(255))
    usageDosage: Mapped[Optional[str]] = mapped_column("usageDosage", Text)
    drugValidityDate: Mapped[Optional[str]] = mapped_column("drugValidityDate", String(255))
    goodsname: Mapped[Optional[str]] = mapped_column("goodsname", String(255))
    baseId: Mapped[Optional[str]] = mapped_column("baseId", String(255))
    goodsstandardcode: Mapped[Optional[str]] = mapped_column("goodsstandardcode", String(128))
    nameOrLhoder: Mapped[Optional[str]] = mapped_column("nameOrLhoder", String(255))
    productmedicinemodel: Mapped[Optional[str]] = mapped_column("productmedicinemodel", String(255))
    approvalcode: Mapped[Optional[str]] = mapped_column("approvalcode", String(255))
    isChildDrugs: Mapped[Optional[int]] = mapped_column("isChildDrugs", SmallInteger)
    registeredmedicinemodel: Mapped[Optional[str]] = mapped_column(
        "registeredmedicinemodel", String(255)
    )
    productname: Mapped[Optional[str]] = mapped_column("productname", String(255))
    factor: Mapped[Optional[int]] = mapped_column("factor", Integer)
    productinsurancetype: Mapped[Optional[str]] = mapped_column("productinsurancetype", String(255))
    isOtc: Mapped[Optional[int]] = mapped_column("isOtc", SmallInteger)
    registeredoutlook: Mapped[Optional[str]] = mapped_column("registeredoutlook", String(255))
    companynamesc: Mapped[Optional[str]] = mapped_column("companynamesc", String(255))
    subpackager: Mapped[Optional[str]] = mapped_column("subpackager", String(255))
    realitymedicinemodel: Mapped[Optional[str]] = mapped_column("realitymedicinemodel", String(255))
    minunit: Mapped[Optional[str]] = mapped_column("minunit", String(255))
    productremark: Mapped[Optional[str]] = mapped_column("productremark", Text)
    marketState: Mapped[Optional[str]] = mapped_column("marketState", String(255))
    unit: Mapped[Optional[str]] = mapped_column("unit", String(255))
    registeredproductname: Mapped[Optional[str]] = mapped_column(
        "registeredproductname", String(255)
    )
    indication: Mapped[Optional[str]] = mapped_column("indication", Text)
    realityoutlook: Mapped[Optional[str]] = mapped_column("realityoutlook", String(255))
    traceCodeFlag: Mapped[Optional[str]] = mapped_column(
        "traceCodeFlag", String(64), server_default=text("'0'")
    )
    goodsCodeHistory: Mapped[Optional[str]] = mapped_column(
        "goodsCodeHistory", String(255), server_default=text("''")
    )
    oldApprovalCode: Mapped[Optional[str]] = mapped_column(
        "oldApprovalCode", String(255), server_default=text("''")
    )
