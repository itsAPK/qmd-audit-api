from fastapi import APIRouter
from app.users.api import router as users_router
from app.settings.api import router as settings_router
from app.auth.api import router as auth_router
from app.audit.api import router as audit_router
from app.audit_info.api import router as audit_info_router
from app.ncr.api import router as ncr_router
from app.files.api import router as files_router
from app.followup.api import router as followup_router
from app.edc_request.api import router as edc_request_router
from app.documents.api import router as documents_router
from app.dashboard.api import router as dashboard_router
from app.checklist.api import router as checklist_router

api_router = APIRouter(prefix="/api")

routers_config = {
    "auth_router": {
        "router": auth_router,
        "prefix": "auth",
        "tags": ["auth"],
    },
    "users_router": {
        "router": users_router,
        "prefix": "users",
        "tags": ["users"],
    },
    
    "dashboard_router": {
        "router": dashboard_router,
        "prefix": "dashboard",
        "tags": ["dashboard"],
    },
    "audit_router": {
        "router": audit_router,
        "prefix": "audit",
        "tags": ["audit"],
    },
    "audit_info_router": {
        "router": audit_info_router,
        "prefix": "audit_info",
        "tags": ["audit-info"],
    },
    "ncr_router": {
        "router": ncr_router,
        "prefix": "ncr",
        "tags": ["NCR"],
        
    },
    "followup_router": {
        "router": followup_router,
        "prefix": "followup",
        "tags": ["followup"],
    },
    "edc_request_router": {
        "router": edc_request_router,
        "prefix": "edc_request",
        "tags": ["EDC request"],
    },
    "checklist_router": {
        "router": checklist_router,
        "prefix": "checklist",
        "tags": ["checklist"],
    },
    "settings_router": {
        "router": settings_router,
        "prefix": "settings",
        "tags": ["settings"],
    },
    "documents_router": {
        "router": documents_router,
        "prefix": "documents",
        "tags": ["documents"],
    },
    "files_router": {
        "router": files_router,
        "prefix": "files",
        "tags": ["files"],
    },
}

for config in routers_config.values():
    api_router.include_router(config["router"], prefix=f"/{config['prefix']}", tags=config["tags"])