from backend.app.routers.auth import router as auth_router
from backend.app.routers.files import router as files_router
from backend.app.routers.audit import router as audit_router
from backend.app.routers.users import router as users_router
from backend.app.routers.ssh_keys import router as ssh_keys_router

__all__ = [
    "auth_router",
    "files_router",
    "audit_router",
    "users_router",
    "ssh_keys_router",
]
