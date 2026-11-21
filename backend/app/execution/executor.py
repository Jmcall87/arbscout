from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from .. import db
from ..config import Settings
from ..models import AuditEntry, Opportunity, Plan, PlanStep
from .policies import ExecutionPolicy


class Executor:
    def __init__(
        self,
        settings: Settings,
        venues: dict[str, Any],
        log: Callable[[str, str, str, bool], None],
    ) -> None:
        self.settings = settings
        self.venues = venues
        self.log = log
        self.policy = ExecutionPolicy(settings)

    def create_plan(self, opportunity: Opportunity) -> Plan:
        amount = opportunity.buy_price
        steps = [
            PlanStep(
                action="buy",
                venue=opportunity.buy_venue,
                item_key=opportunity.item_key,
                amount=amount,
                note=f"Acquire at {opportunity.buy_venue}",
            ),
            PlanStep(
                action="sell",
                venue=opportunity.sell_venue,
                item_key=opportunity.item_key,
                amount=opportunity.sell_price,
                note=f"Sell instantly at {opportunity.sell_venue}",
            ),
        ]
        plan = Plan(
            id=str(uuid.uuid4()),
            opportunity_id=opportunity.id,
            mode=self.settings.mode,
            steps=steps,
            approval_required=self.settings.mode != "full",
            reason=f"net {opportunity.net_profit} / roi {opportunity.roi_pct}%",
        )
        db.save_plan(self.settings.db_path, plan)
        self.log("plan_created", plan.id, self.settings.mode, True)
        return plan

    def approve(self, plan_id: str) -> Plan | None:
        plan = db.get_plan(self.settings.db_path, plan_id)
        if plan is None:
            return None
        plan.approved = True
        db.save_plan(self.settings.db_path, plan)
        self.log("plan_approved", plan_id, self.settings.mode, True)
        return plan

    def spent_today(self) -> Decimal:
        today = datetime.now(timezone.utc).date()
        total = Decimal("0")
        for plan in db.list_plans(self.settings.db_path, limit=500):
            if not plan.executed or plan.created_at.date() != today:
                continue
            for step in plan.steps:
                if step.action == "buy":
                    total += step.amount
        return total

    async def execute(self, plan_id: str, http: Any, browser: Any) -> dict[str, Any]:
        plan = db.get_plan(self.settings.db_path, plan_id)
        if plan is None:
            return {"ok": False, "reason": "plan not found"}

        if plan.approval_required and not plan.approved:
            self.log("execute_blocked", f"{plan_id}: approval required", plan.mode, False)
            return {"ok": False, "reason": "approval required"}

        projected = sum(
            (step.amount for step in plan.steps if step.action == "buy"), Decimal("0")
        )
        if self.spent_today() + projected > self.settings.max_spend_per_day:
            self.log("execute_blocked", f"{plan_id}: daily cap", plan.mode, False)
            return {"ok": False, "reason": "daily spend cap would be exceeded"}

        completed: list[dict[str, Any]] = []
        for step in plan.steps:
            venue = self.venues.get(step.venue)
            if venue is None:
                self.log("execute_blocked", f"{plan_id}: unknown venue", plan.mode, False)
                return {"ok": False, "reason": f"unknown venue '{step.venue}'"}

            decision = self.policy.evaluate(venue, step.amount)
            if not decision.allowed:
                self.log("execute_blocked", f"{plan_id}: {decision.reason}", plan.mode, False)
                return {"ok": False, "reason": decision.reason}

            try:
                if step.action == "buy":
                    reference = await venue.execute_buy(step, http, browser)
                else:
                    reference = await venue.execute_sell(step, http, browser)
            except NotImplementedError as exc:
                self.log("execute_blocked", f"{plan_id}: {exc}", plan.mode, False)
                return {"ok": False, "reason": str(exc)}
            except Exception as exc:  # noqa: BLE001
                detail = f"{plan_id}: {type(exc).__name__}: {exc}"
                self.log("execute_failed", detail, plan.mode, False)
                return {"ok": False, "reason": detail}

            self.log(
                f"execute_{step.action}",
                f"{step.venue} amount={step.amount} ref={reference}",
                plan.mode,
                True,
            )
            completed.append(
                {"action": step.action, "venue": step.venue, "reference": reference}
            )

        plan.executed = True
        db.save_plan(self.settings.db_path, plan)
        return {"ok": True, "steps": completed}
