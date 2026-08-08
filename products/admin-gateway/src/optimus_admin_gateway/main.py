from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import ValidationError

from .approvals import ApprovalVerifier
from .auth import build_principal_dependency
from .catalog import OperationCatalog
from .config import Settings
from .executors import ExecutorContext, ExecutorUnavailable, OperationExecutor
from .models import (
    JobState,
    OperationPlan,
    OperationRequest,
    Principal,
    canonical_plan_hash,
)

settings = Settings.from_env()
catalog = OperationCatalog.load(settings.catalog_path)
approvals = ApprovalVerifier(settings.approval_hmac_secret)
executor = OperationExecutor(settings.executor_mode)
get_principal = build_principal_dependency(settings)

app = FastAPI(
    title="Optimus Admin Gateway",
    version="0.1.0",
    description="Governed allowlisted administration API for HUB_Optimus",
)


def build_plan(operation_id: str, request: OperationRequest) -> tuple[OperationPlan, object]:
    definition = catalog.get(operation_id)
    if definition is None:
        raise HTTPException(status_code=404, detail={"code": "OPERATION_NOT_FOUND"})
    try:
        validated = catalog.validate_parameters(definition, request.parameters)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PARAMETER_VALIDATION_FAILED", "errors": exc.errors()},
        ) from exc
    normalized = validated.model_dump(mode="json")
    payload = {
        "operation_id": definition.operation_id,
        "parameters": normalized,
        "mutation": definition.mutation,
        "risk": definition.risk.value,
        "dry_run": request.dry_run,
        "catalog_version": catalog.version,
    }
    plan_hash = canonical_plan_hash(payload)
    state = JobState.approval_required if definition.mutation and not request.dry_run else JobState.planned
    return (
        OperationPlan(
            operation_id=definition.operation_id,
            title=definition.title,
            mutation=definition.mutation,
            approval_required=definition.approval_required,
            risk=definition.risk,
            dry_run=request.dry_run,
            parameters=normalized,
            plan_hash=plan_hash,
            catalog_version=catalog.version,
            state=state,
        ),
        definition,
    )


@app.get("/healthz", tags=["system"])
async def healthz() -> dict[str, str]:
    return {"status": "ok", "catalog_version": catalog.version, "executor_mode": settings.executor_mode}


@app.get("/api/v1/operations", tags=["operations"])
async def list_operations(principal: Principal = Depends(get_principal)) -> dict:
    return {
        "principal": principal.subject_id,
        "catalog_version": catalog.version,
        "operations": [item.model_dump(mode="json") for item in catalog.list()],
    }


@app.post("/api/v1/operations/{operation_id}:plan", response_model=OperationPlan, tags=["operations"])
async def plan_operation(
    operation_id: str,
    request: OperationRequest,
    principal: Principal = Depends(get_principal),
) -> OperationPlan:
    del principal
    plan, _definition = build_plan(operation_id, request)
    return plan


@app.post("/api/v1/operations/{operation_id}:execute", tags=["operations"])
async def execute_operation(
    operation_id: str,
    request: OperationRequest,
    principal: Principal = Depends(get_principal),
):
    plan, definition = build_plan(operation_id, request)
    if definition.mutation and not request.dry_run:
        if request.approval is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "APPROVAL_REQUIRED", "plan_hash": plan.plan_hash},
            )
        if not approvals.verify(request.approval, plan.plan_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "APPROVAL_INVALID", "plan_hash": plan.plan_hash},
            )
    try:
        result = await executor.execute(
            ExecutorContext(
                principal=principal,
                definition=definition,
                plan=plan,
                idempotency_key=request.idempotency_key,
            )
        )
    except ExecutorUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EXECUTOR_NOT_CONFIGURED", "message": str(exc), "plan_hash": plan.plan_hash},
        ) from exc
    return result
