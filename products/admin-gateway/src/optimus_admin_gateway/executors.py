from __future__ import annotations

import uuid
from dataclasses import dataclass

from .models import ExecutionResult, JobState, OperationDefinition, OperationPlan, Principal


@dataclass(frozen=True)
class ExecutorContext:
    principal: Principal
    definition: OperationDefinition
    plan: OperationPlan
    idempotency_key: str


class ExecutorUnavailable(RuntimeError):
    pass


class OperationExecutor:
    def __init__(self, mode: str):
        self._mode = mode

    async def execute(self, context: ExecutorContext) -> ExecutionResult:
        if context.plan.dry_run:
            return ExecutionResult(
                job_id=f"dryrun-{uuid.uuid4()}",
                operation_id=context.definition.operation_id,
                state=JobState.planned,
                dry_run=True,
                plan_hash=context.plan.plan_hash,
                message="DryRun completed; no external action was executed",
                output={"validated_parameters": context.plan.parameters},
            )
        if self._mode == "disabled":
            raise ExecutorUnavailable("No tenant execution adapter is configured")
        raise ExecutorUnavailable(f"Unsupported executor mode: {self._mode}")
