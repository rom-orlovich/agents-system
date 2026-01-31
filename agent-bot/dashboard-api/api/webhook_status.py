"""Webhook status and monitoring API."""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import structlog
import uuid
import json
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from core.config import settings
from core.database import get_session as get_db_session
from core.database.models import WebhookConfigDB, WebhookEventDB, WebhookCommandDB
from core.webhook_configs import WEBHOOK_CONFIGS

logger = structlog.get_logger()

router = APIRouter()


@router.get("/webhooks-status")
async def get_webhooks_status(db: AsyncSession = Depends(get_db_session)):
    """
    Get status of all webhooks including static and dynamic webhooks.
    Static webhooks are considered active if their secret is configured.
    """
    try:
        webhook_statuses = []

        # Log static webhook configs for debugging
        logger.debug("loading_static_webhooks", count=len(WEBHOOK_CONFIGS))

        # Get event counts by provider (for static webhooks) - successful only
        events_by_provider_query = (
            select(
                WebhookEventDB.provider,
                func.count(WebhookEventDB.event_id).label("count"),
                func.max(WebhookEventDB.created_at).label("last_event"),
            )
            .where(WebhookEventDB.response_sent.is_(True))
            .group_by(WebhookEventDB.provider)
        )
        events_by_provider_result = await db.execute(events_by_provider_query)
        events_by_provider = {
            row[0]: {"count": row[1], "last_event": row[2]}
            for row in events_by_provider_result
        }

        # Add static webhooks first
        if not WEBHOOK_CONFIGS:
            logger.warning("no_static_webhook_configs_found")
        else:
            logger.debug("processing_static_webhooks", count=len(WEBHOOK_CONFIGS))

        for config in WEBHOOK_CONFIGS:
            # Check if webhook secret is configured
            has_secret = False
            if config.requires_signature and config.secret_env_var:
                secret_value = os.getenv(config.secret_env_var)
                has_secret = bool(secret_value)
                logger.debug(
                    "static_webhook_secret_check",
                    name=config.name,
                    secret_env_var=config.secret_env_var,
                    has_secret=has_secret,
                )

            # Static webhooks are always considered active/enabled if they are in the config
            # (regardless of secret presence, matching user requirement)
            is_active = True

            # Get event stats for this provider
            provider_stats = events_by_provider.get(
                config.source, {"count": 0, "last_event": None}
            )

            # Build public URL
            public_url = None
            if settings.webhook_public_domain:
                public_url = (
                    f"https://{settings.webhook_public_domain}{config.endpoint}"
                )

            webhook_statuses.append(
                {
                    "webhook_id": f"static-{config.name}",  # Unique ID for static webhooks
                    "name": config.name,
                    "provider": config.source,
                    "endpoint": config.endpoint,
                    "public_url": public_url,
                    "enabled": is_active,
                    "is_builtin": True,
                    "event_count": provider_stats["count"],
                    "last_event_at": provider_stats["last_event"].isoformat()
                    if provider_stats["last_event"]
                    else None,
                    "created_at": config.created_at.isoformat()
                    if hasattr(config, "created_at")
                    else None,
                    "has_secret": has_secret,
                }
            )

        # Get dynamic webhooks from database
        result = await db.execute(
            select(WebhookConfigDB).order_by(WebhookConfigDB.created_at.desc())
        )
        db_webhooks = result.scalars().all()

        for webhook in db_webhooks:
            # Count events for this webhook - successful only
            event_count_result = await db.execute(
                select(func.count(WebhookEventDB.event_id))
                .where(WebhookEventDB.webhook_id == webhook.webhook_id)
                .where(WebhookEventDB.response_sent.is_(True))
            )
            event_count = event_count_result.scalar() or 0

            # Get last event time
            last_event_result = await db.execute(
                select(WebhookEventDB.created_at)
                .where(WebhookEventDB.webhook_id == webhook.webhook_id)
                .order_by(WebhookEventDB.created_at.desc())
                .limit(1)
            )
            last_event = last_event_result.scalar()

            # Build public URL
            public_url = None
            if settings.webhook_public_domain:
                public_url = (
                    f"https://{settings.webhook_public_domain}{webhook.endpoint}"
                )

            webhook_statuses.append(
                {
                    "webhook_id": webhook.webhook_id,
                    "name": webhook.name,
                    "provider": webhook.provider,
                    "endpoint": webhook.endpoint,
                    "public_url": public_url,
                    "enabled": webhook.enabled,
                    "is_builtin": False,
                    "event_count": event_count,
                    "last_event_at": last_event.isoformat() if last_event else None,
                    "created_at": webhook.created_at.isoformat(),
                    "has_secret": bool(webhook.secret),
                }
            )

        return {
            "success": True,
            "data": {
                "webhooks": webhook_statuses,
                "total_count": len(webhook_statuses),
                "active_count": sum(1 for w in webhook_statuses if w["enabled"]),
                "public_domain": settings.webhook_public_domain,
            },
        }

    except Exception as e:
        logger.error("get_webhooks_status_error", error=str(e))
        return {"success": False, "error": str(e)}


class WebhookCreate(BaseModel):
    name: str
    provider: str
    enabled: bool = True
    secret: Optional[str] = None
    commands: List[Dict[str, Any]] = []


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    secret: Optional[str] = None


class CommandCreate(BaseModel):
    trigger: str
    action: str
    agent: Optional[str] = None
    template: str
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0


class CommandUpdate(BaseModel):
    trigger: Optional[str] = None
    action: Optional[str] = None
    agent: Optional[str] = None
    template: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None


@router.get("/webhooks")
async def list_webhooks(db: AsyncSession = Depends(get_db_session)):
    """List all dynamic webhooks (returns list directly, not wrapped)."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).order_by(WebhookConfigDB.created_at.desc())
        )
        webhooks = result.scalars().all()

        webhook_list = []
        for webhook in webhooks:
            # Load commands
            commands_result = await db.execute(
                select(WebhookCommandDB).where(
                    WebhookCommandDB.webhook_id == webhook.webhook_id
                )
            )
            commands = commands_result.scalars().all()

            webhook_list.append(
                {
                    "webhook_id": webhook.webhook_id,
                    "name": webhook.name,
                    "provider": webhook.provider,
                    "endpoint": webhook.endpoint,
                    "enabled": webhook.enabled,
                    "commands": [
                        {
                            "command_id": cmd.command_id,
                            "trigger": cmd.trigger,
                            "action": cmd.action,
                            "agent": cmd.agent,
                            "template": cmd.template,
                            "conditions": json.loads(cmd.conditions_json)
                            if cmd.conditions_json
                            else None,
                            "priority": cmd.priority,
                        }
                        for cmd in commands
                    ],
                }
            )

        return webhook_list
    except Exception as e:
        logger.error("list_webhooks_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get webhook details by ID."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Load commands
        commands_result = await db.execute(
            select(WebhookCommandDB).where(WebhookCommandDB.webhook_id == webhook_id)
        )
        commands = commands_result.scalars().all()

        return {
            "webhook_id": webhook.webhook_id,
            "name": webhook.name,
            "provider": webhook.provider,
            "endpoint": webhook.endpoint,
            "enabled": webhook.enabled,
            "commands": [
                {
                    "command_id": cmd.command_id,
                    "trigger": cmd.trigger,
                    "action": cmd.action,
                    "agent": cmd.agent,
                    "template": cmd.template,
                    "conditions": json.loads(cmd.conditions_json)
                    if cmd.conditions_json
                    else None,
                    "priority": cmd.priority,
                }
                for cmd in commands
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_webhook_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook: WebhookCreate, db: AsyncSession = Depends(get_db_session)
):
    """Create a new dynamic webhook."""
    try:
        # Validate provider
        valid_providers = ["github", "jira", "slack", "sentry"]
        if webhook.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}",
            )

        # Check if name exists
        existing = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.name == webhook.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Webhook with this name already exists"
            )

        # Create webhook
        webhook_id = f"wh-{uuid.uuid4().hex[:12]}"
        endpoint = f"/webhooks/{webhook.provider}/{webhook_id}"

        db_webhook = WebhookConfigDB(
            webhook_id=webhook_id,
            name=webhook.name,
            provider=webhook.provider,
            endpoint=endpoint,
            enabled=webhook.enabled,
            secret=webhook.secret,
            config_json=json.dumps({}),  # Required field
            created_by="system",  # Required field
            created_at=datetime.now(timezone.utc),
        )
        db.add(db_webhook)
        await db.flush()  # Flush to get webhook_id for commands

        # Create commands
        for cmd_data in webhook.commands:
            command_id = f"cmd-{uuid.uuid4().hex[:12]}"
            db_command = WebhookCommandDB(
                command_id=command_id,
                webhook_id=webhook_id,
                trigger=cmd_data.get("trigger", ""),
                action=cmd_data.get("action", "create_task"),
                agent=cmd_data.get("agent"),
                template=cmd_data.get("template", ""),
                conditions_json=json.dumps(cmd_data.get("conditions"))
                if cmd_data.get("conditions")
                else None,
                priority=cmd_data.get("priority", 0),
            )
            db.add(db_command)

        await db.commit()

        return {
            "success": True,
            "data": {
                "webhook_id": webhook_id,
                "name": db_webhook.name,
                "provider": db_webhook.provider,
                "endpoint": endpoint,
                "enabled": db_webhook.enabled,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/{webhook_id}/events")
async def get_webhook_events(
    webhook_id: str, limit: int = 50, db: AsyncSession = Depends(get_db_session)
):
    """
    Get recent events for a specific webhook.
    """
    try:
        result = await db.execute(
            select(WebhookEventDB)
            .where(WebhookEventDB.webhook_id == webhook_id)
            .order_by(WebhookEventDB.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "matched_command": event.matched_command,
                    "task_id": event.task_id,
                    "response_sent": event.response_sent,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
        }

    except Exception as e:
        logger.error("get_webhook_events_error", error=str(e), webhook_id=webhook_id)
        return {"success": False, "error": str(e)}


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    webhook_update: WebhookUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update webhook configuration."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Update fields
        if webhook_update.name is not None:
            webhook.name = webhook_update.name
        if webhook_update.enabled is not None:
            webhook.enabled = webhook_update.enabled
        if webhook_update.secret is not None:
            webhook.secret = webhook_update.secret

        await db.commit()

        return {
            "success": True,
            "data": {
                "webhook_id": webhook.webhook_id,
                "name": webhook.name,
                "provider": webhook.provider,
                "endpoint": webhook.endpoint,
                "enabled": webhook.enabled,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_webhook_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        await db.delete(webhook)
        await db.commit()

        return {"success": True, "data": {"webhook_id": webhook_id}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_webhook_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/enable")
async def enable_webhook(webhook_id: str, db: AsyncSession = Depends(get_db_session)):
    """Enable a webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        webhook.enabled = True
        await db.commit()

        return {"success": True, "data": {"webhook_id": webhook_id, "enabled": True}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("enable_webhook_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/disable")
async def disable_webhook(webhook_id: str, db: AsyncSession = Depends(get_db_session)):
    """Disable a webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        webhook.enabled = False
        await db.commit()

        return {"success": True, "data": {"webhook_id": webhook_id, "enabled": False}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("disable_webhook_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/commands", status_code=status.HTTP_201_CREATED)
async def add_command_to_webhook(
    webhook_id: str, command: CommandCreate, db: AsyncSession = Depends(get_db_session)
):
    """Add command to existing webhook."""
    try:
        # Verify webhook exists
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Create command
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        db_command = WebhookCommandDB(
            command_id=command_id,
            webhook_id=webhook_id,
            trigger=command.trigger,
            action=command.action,
            agent=command.agent,
            template=command.template,
            conditions_json=json.dumps(command.conditions)
            if command.conditions
            else None,
            priority=command.priority,
        )
        db.add(db_command)
        await db.commit()

        return {
            "success": True,
            "data": {
                "command_id": command_id,
                "trigger": command.trigger,
                "action": command.action,
                "agent": command.agent,
                "template": command.template,
                "conditions": command.conditions,
                "priority": command.priority,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("add_command_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/{webhook_id}/commands")
async def list_commands(webhook_id: str, db: AsyncSession = Depends(get_db_session)):
    """List all commands for a webhook."""
    try:
        # Verify webhook exists
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Get commands
        commands_result = await db.execute(
            select(WebhookCommandDB).where(WebhookCommandDB.webhook_id == webhook_id)
        )
        commands = commands_result.scalars().all()

        return [
            {
                "command_id": cmd.command_id,
                "trigger": cmd.trigger,
                "action": cmd.action,
                "agent": cmd.agent,
                "template": cmd.template,
                "conditions": json.loads(cmd.conditions_json)
                if cmd.conditions_json
                else None,
                "priority": cmd.priority,
            }
            for cmd in commands
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_commands_error", error=str(e), webhook_id=webhook_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/webhooks/{webhook_id}/commands/{command_id}")
async def update_command(
    webhook_id: str,
    command_id: str,
    command_update: CommandUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update existing command."""
    try:
        # Verify webhook exists
        webhook_result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = webhook_result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Get command
        command_result = await db.execute(
            select(WebhookCommandDB).where(
                WebhookCommandDB.command_id == command_id,
                WebhookCommandDB.webhook_id == webhook_id,
            )
        )
        command = command_result.scalar_one_or_none()

        if not command:
            raise HTTPException(status_code=404, detail="Command not found")

        # Update fields
        if command_update.trigger is not None:
            command.trigger = command_update.trigger
        if command_update.action is not None:
            command.action = command_update.action
        if command_update.agent is not None:
            command.agent = command_update.agent
        if command_update.template is not None:
            command.template = command_update.template
        if command_update.conditions is not None:
            command.conditions_json = json.dumps(command_update.conditions)
        if command_update.priority is not None:
            command.priority = command_update.priority

        await db.commit()

        return {
            "success": True,
            "data": {
                "command_id": command.command_id,
                "trigger": command.trigger,
                "action": command.action,
                "agent": command.agent,
                "template": command.template,
                "conditions": json.loads(command.conditions_json)
                if command.conditions_json
                else None,
                "priority": command.priority,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_command_error",
            error=str(e),
            webhook_id=webhook_id,
            command_id=command_id,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}/commands/{command_id}")
async def delete_command(
    webhook_id: str, command_id: str, db: AsyncSession = Depends(get_db_session)
):
    """Delete command from webhook."""
    try:
        # Verify webhook exists
        webhook_result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = webhook_result.scalar_one_or_none()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Get command
        command_result = await db.execute(
            select(WebhookCommandDB).where(
                WebhookCommandDB.command_id == command_id,
                WebhookCommandDB.webhook_id == webhook_id,
            )
        )
        command = command_result.scalar_one_or_none()

        if not command:
            raise HTTPException(status_code=404, detail="Command not found")

        await db.delete(command)
        await db.commit()

        return {"success": True, "data": {"command_id": command_id}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_command_error",
            error=str(e),
            webhook_id=webhook_id,
            command_id=command_id,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/events/recent")
async def get_recent_webhook_events(
    limit: int = 100, db: AsyncSession = Depends(get_db_session)
):
    """
    Get recent webhook events across all webhooks.
    """
    try:
        result = await db.execute(
            select(WebhookEventDB)
            .order_by(WebhookEventDB.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "event_id": event.event_id,
                    "webhook_id": event.webhook_id,
                    "provider": event.provider,
                    "event_type": event.event_type,
                    "matched_command": event.matched_command,
                    "task_id": event.task_id,
                    "response_sent": event.response_sent,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
        }

    except Exception as e:
        logger.error("get_recent_webhook_events_error", error=str(e))
        return {"success": False, "error": str(e)}
