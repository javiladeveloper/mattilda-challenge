from fastapi import APIRouter

from src.api.routes.schools import router as schools_router
from src.api.routes.students import router as students_router
from src.api.routes.invoices import router as invoices_router
from src.api.routes.payments import router as payments_router
from src.api.routes.auth import router as auth_router
from src.api.routes.reports import router as reports_router
from src.api.routes.ai import router as ai_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(schools_router, prefix="/schools", tags=["Schools"])
router.include_router(students_router, prefix="/students", tags=["Students"])
router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
router.include_router(payments_router, prefix="/payments", tags=["Payments"])
router.include_router(reports_router, tags=["Reports"])
router.include_router(ai_router, tags=["AI Agent"])
