from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from . import db
from .config import VALID_MODES
from .execution.executor import Executor
from .models import AuditEntry
from .scanner import scan_once
from .valuation import build_valuation

router = APIRouter(prefix="/api")

ALLOWED_SETTING_KEYS = {
    "mode",
    "allowed_venues",
    "kill_switch",
    "tos_ack",
    "max_spend_per_trade",
    "max_spend_per_day",
    "scan_interval_seconds",
    "min_net_profit",
    "min_roi_pct",
    "min_confidence",
    "payment_spread_pct",
}


class ModeRequest(BaseModel):
    mode: str


class SettingsRequest(BaseModel):
    values: dict[str, str]


def _audit(request: Request, event: str, detail: str, mode: str, allowed: bool = True) -> None:
    db.append_audit(
        request.app.state.settings.db_path,
        AuditEntry(event=event, detail=detail, mode=mode, allowed=allowed),
    )


def _executor(request: Request) -> Executor:
    state = request.app.state
    venues = {venue.id: venue for venue in state.venues}

    def log(event: str, detail: str, mode: str, allowed: bool) -> None:
        db.append_audit(
            state.settings.db_path,
            AuditEntry(event=event, detail=detail, mode=mode, allowed=allowed),
        )

    return Executor(state.settings, venues, log)


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    state = request.app.state
    last_scan = state.last_scan.model_dump(mode="json") if state.last_scan else None
    return {
        "settings": state.settings.snapshot(),
        "browser": {
            "available": state.browser.available,
            "error": state.browser.error,
        },
        "venue_count": len(state.venues),
        "item_count": len(state.items),
        "last_scan": last_scan,
    }


@router.get("/mode")
def get_mode(request: Request) -> dict[str, str]:
    return {"mode": request.app.state.settings.mode}


@router.put("/mode")
def set_mode(request: Request, payload: ModeRequest) -> dict[str, str]:
    mode = payload.mode.strip().lower()
    if mode not in VALID_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {VALID_MODES}")
    db.set_setting(request.app.state.settings.db_path, "mode", mode)
    request.app.state.settings = request.app.state.settings.apply_overrides({"mode": mode})
    _audit(request, "mode_changed", mode, mode, mode != "full")
    return {"mode": mode}


@router.get("/settings")
def get_settings(request: Request) -> dict[str, Any]:
    return request.app.state.settings.snapshot()


@router.patch("/settings")
def patch_settings(request: Request, payload: SettingsRequest) -> dict[str, Any]:
    updates = {key: str(value) for key, value in payload.values.items() if key in ALLOWED_SETTING_KEYS}
    if not updates:
        raise HTTPException(status_code=400, detail="no recognised settings supplied")
    path = request.app.state.settings.db_path
    for key, value in updates.items():
        db.set_setting(path, key, value)
    request.app.state.settings = request.app.state.settings.apply_overrides(updates)
    _audit(request, "settings_updated", ", ".join(sorted(updates)), request.app.state.settings.mode)
    return request.app.state.settings.snapshot()


@router.get("/items")
def get_items(request: Request) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in request.app.state.items]


@router.get("/venues")
def get_venues(request: Request) -> list[dict[str, Any]]:
    return [
        {
            "id": venue.id,
            "label": venue.label,
            "kind": venue.kind,
            "permits_automation": venue.permits_automation,
            "simulated": venue.simulated,
            "allowlisted": venue.id in request.app.state.settings.allowed_venues,
        }
        for venue in request.app.state.venues
    ]


@router.post("/scan")
async def run_scan(request: Request) -> dict[str, Any]:
    state = request.app.state
    summary = await scan_once(state.settings, state.venues, state.items, state.http, state.browser)
    state.last_scan = summary
    _audit(
        request,
        "scan_completed",
        f"quotes={summary.quote_count} opportunities={summary.opportunity_count}",
        state.settings.mode,
    )
    return summary.model_dump(mode="json")


@router.get("/opportunities")
def get_opportunities(request: Request, limit: int = 100, profitable_only: bool = True) -> list[dict[str, Any]]:
    return [
        opp.model_dump(mode="json")
        for opp in db.list_opportunities(
            request.app.state.settings.db_path, limit=limit, profitable_only=profitable_only
        )
    ]


@router.get("/quotes")
def get_quotes(request: Request, item_key: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    return [
        quote.model_dump(mode="json")
        for quote in db.get_quotes(request.app.state.settings.db_path, item_key, limit)
    ]


@router.get("/valuation/{item_key:path}")
def get_valuation(request: Request, item_key: str) -> dict[str, Any]:
    history = db.get_quotes(request.app.state.settings.db_path, item_key, request.app.state.settings.history_limit)
    return build_valuation(item_key, history).model_dump(mode="json")


@router.post("/opportunities/{opportunity_id}/plan")
def create_plan(request: Request, opportunity_id: str) -> dict[str, Any]:
    opportunity = db.get_opportunity(request.app.state.settings.db_path, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="opportunity not found")
    return _executor(request).create_plan(opportunity).model_dump(mode="json")


@router.get("/plans")
def get_plans(request: Request, limit: int = 100) -> list[dict[str, Any]]:
    return [plan.model_dump(mode="json") for plan in db.list_plans(request.app.state.settings.db_path, limit)]


@router.post("/plans/{plan_id}/approve")
def approve_plan(request: Request, plan_id: str) -> dict[str, Any]:
    plan = _executor(request).approve(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return plan.model_dump(mode="json")


@router.post("/plans/{plan_id}/execute")
async def execute_plan(request: Request, plan_id: str) -> dict[str, Any]:
    state = request.app.state
    return await _executor(request).execute(plan_id, state.http, state.browser)


@router.get("/audit")
def get_audit(request: Request, limit: int = 100) -> list[dict[str, Any]]:
    return [
        entry.model_dump(mode="json")
        for entry in db.list_audit(request.app.state.settings.db_path, limit)
    ]
