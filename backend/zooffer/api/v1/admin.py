from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from zooffer.api.deps import DbSession, permission_required
from zooffer.schemas.billing import (
    AdminEntitlementGrantRequest,
    AdminEntitlementView,
    AdminPaymentDetailView,
    AdminReconcileView,
    AdminRefundRequest,
)
from zooffer.schemas.admin import (
    AdminAuditList,
    AdminDashboardView,
    AdminListingList,
    AdminListingView,
    AdminPaymentList,
    AdminReportList,
    AdminReportView,
    AdminSettingsView,
    AdminSettingUpdateRequest,
    AdminSettingView,
    AdminSupportList,
    AdminSupportReplyRequest,
    AdminSupportTicketView,
    AdminUserList,
    AdminUserUpdateRequest,
    AdminUserView,
    ModerationDecisionRequest,
    ReportResolveRequest,
)
from zooffer.services import admin_service, billing_service
from zooffer.services.auth_service import AuthContext

router = APIRouter(prefix="/admin", tags=["admin"])

DashboardAuth = Annotated[AuthContext, Depends(permission_required("admin:dashboard"))]
ModerationReadAuth = Annotated[AuthContext, Depends(permission_required("moderation:read"))]
ModerationWriteAuth = Annotated[AuthContext, Depends(permission_required("moderation:write"))]
UsersReadAuth = Annotated[AuthContext, Depends(permission_required("users:read"))]
UsersWriteAuth = Annotated[AuthContext, Depends(permission_required("users:write"))]
PaymentsReadAuth = Annotated[AuthContext, Depends(permission_required("payments:read"))]
PaymentsWriteAuth = Annotated[AuthContext, Depends(permission_required("payments:write"))]
SettingsWriteAuth = Annotated[AuthContext, Depends(permission_required("settings:write"))]


@router.get("/dashboard", response_model=AdminDashboardView)
async def dashboard(auth: DashboardAuth, db: DbSession) -> AdminDashboardView:
    return await admin_service.dashboard(db)


@router.get("/listings", response_model=AdminListingList)
async def list_listings(
    auth: ModerationReadAuth,
    db: DbSession,
    status: str | None = Query(default=None, max_length=24),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
) -> AdminListingList:
    items, total = await admin_service.list_listings(db, status=status, query=q, limit=limit)
    return AdminListingList(items=items, total=total)


@router.post("/moderation/listings/{public_id}", response_model=AdminListingView)
async def moderate_listing(
    public_id: UUID,
    payload: ModerationDecisionRequest,
    auth: ModerationWriteAuth,
    db: DbSession,
) -> AdminListingView:
    return await admin_service.moderate_listing(
        db, auth.user, public_id, action=payload.action, reason=payload.reason
    )


@router.get("/reports", response_model=AdminReportList)
async def list_reports(
    auth: ModerationReadAuth,
    db: DbSession,
    status: str | None = Query(default=None, max_length=24),
) -> AdminReportList:
    return AdminReportList(items=await admin_service.list_reports(db, status=status))


@router.patch("/reports/{report_id}", response_model=AdminReportView)
async def resolve_report(
    report_id: UUID,
    payload: ReportResolveRequest,
    auth: ModerationWriteAuth,
    db: DbSession,
) -> AdminReportView:
    return await admin_service.resolve_report(
        db, auth.user, report_id, status=payload.status, resolution=payload.resolution
    )


@router.get("/users", response_model=AdminUserList)
async def list_users(
    auth: UsersReadAuth,
    db: DbSession,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
) -> AdminUserList:
    items, total = await admin_service.list_users(db, query=q, limit=limit)
    return AdminUserList(items=items, total=total)


@router.patch("/users/{public_id}", response_model=AdminUserView)
async def update_user(
    public_id: UUID,
    payload: AdminUserUpdateRequest,
    auth: UsersWriteAuth,
    db: DbSession,
) -> AdminUserView:
    return await admin_service.update_user(
        db, auth.user, public_id, role=payload.role, status=payload.status
    )


@router.get("/support", response_model=AdminSupportList)
async def list_support(auth: DashboardAuth, db: DbSession) -> AdminSupportList:
    return AdminSupportList(items=await admin_service.list_support(db))


@router.post("/support/{ticket_public_id}/reply", response_model=AdminSupportTicketView)
async def reply_support(
    ticket_public_id: UUID,
    payload: AdminSupportReplyRequest,
    auth: ModerationWriteAuth,
    db: DbSession,
) -> AdminSupportTicketView:
    return await admin_service.reply_support(
        db,
        auth.user,
        ticket_public_id,
        message=payload.message,
        status=payload.status,
    )


@router.get("/settings", response_model=AdminSettingsView)
async def get_settings(auth: DashboardAuth, db: DbSession) -> AdminSettingsView:
    return AdminSettingsView(items=await admin_service.get_settings(db))


@router.put("/settings/{key}", response_model=AdminSettingView)
async def set_setting(
    key: str,
    payload: AdminSettingUpdateRequest,
    auth: SettingsWriteAuth,
    db: DbSession,
) -> AdminSettingView:
    return await admin_service.set_setting(db, auth.user, key, payload.value)


@router.get("/audit", response_model=AdminAuditList)
async def audit_log(
    auth: DashboardAuth,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=200),
) -> AdminAuditList:
    return AdminAuditList(items=await admin_service.audit_log(db, limit=limit))


@router.get("/payments", response_model=AdminPaymentList)
async def list_payments(auth: PaymentsReadAuth, db: DbSession) -> AdminPaymentList:
    return AdminPaymentList(items=await admin_service.list_payments(db))


@router.get("/payments/{order_id}", response_model=AdminPaymentDetailView)
async def payment_detail(
    order_id: UUID, auth: PaymentsReadAuth, db: DbSession
) -> AdminPaymentDetailView:
    return await billing_service.admin_payment_detail(db, order_id)


@router.post("/payments/{order_id}/refund", response_model=AdminPaymentDetailView)
async def refund_payment(
    order_id: UUID,
    payload: AdminRefundRequest,
    auth: PaymentsWriteAuth,
    db: DbSession,
) -> AdminPaymentDetailView:
    await billing_service.admin_refund(db, auth.user, order_id, reason=payload.reason)
    return await billing_service.admin_payment_detail(db, order_id)


@router.post("/users/{user_public_id}/entitlements", response_model=AdminEntitlementView)
async def grant_entitlement(
    user_public_id: UUID,
    payload: AdminEntitlementGrantRequest,
    auth: PaymentsWriteAuth,
    db: DbSession,
) -> AdminEntitlementView:
    data = await billing_service.admin_grant_entitlement(
        db, auth.user, user_public_id, code=payload.code, days=payload.days
    )
    return AdminEntitlementView(**data)


@router.delete("/users/{user_public_id}/entitlements/{code}", response_model=dict)
async def revoke_entitlement(
    user_public_id: UUID,
    code: str,
    auth: PaymentsWriteAuth,
    db: DbSession,
) -> dict[str, bool]:
    await billing_service.admin_revoke_entitlement(db, auth.user, user_public_id, code)
    return {"ok": True}


@router.get("/payments-reconcile", response_model=AdminReconcileView)
async def reconcile_payments(
    auth: PaymentsReadAuth, db: DbSession
) -> AdminReconcileView:
    return AdminReconcileView(**await billing_service.reconcile(db))
