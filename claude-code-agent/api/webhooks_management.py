"""Webhook management API endpoints."""

import uuid
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookConfigDB, WebhookCommandDB
from api.webhook_templates import list_templates, get_template

logger = structlog.get_logger()

router = APIRouter()


class WebhookCommandCreate(BaseModel):
    """Webhook command creation model."""
    trigger: str
    action: str
    agent: Optional[str] = None
    template: str
    conditions: Optional[dict] = None
    priority: int = 0


class WebhookCommandUpdate(BaseModel):
    """Webhook command update model."""
    trigger: Optional[str] = None
    action: Optional[str] = None
    agent: Optional[str] = None
    template: Optional[str] = None
    conditions: Optional[dict] = None
    priority: Optional[int] = None


class WebhookCreate(BaseModel):
    """Webhook creation model."""
    name: str
    provider: str
    secret: Optional[str] = None
    enabled: bool = True
    commands: List[WebhookCommandCreate] = Field(default_factory=list)


class WebhookUpdate(BaseModel):
    """Webhook update model."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response model."""
    webhook_id: str
    name: str
    provider: str
    endpoint: str
    enabled: bool
    created_at: datetime
    created_by: str
    commands: List[dict]


VALID_PROVIDERS = ["github", "jira", "slack", "sentry", "custom"]
VALID_ACTIONS = [
    "create_task",      # Create agent task
    "comment",          # Post comment to source
    "ask",              # Interactive question
    "respond",          # Immediate response
    "forward",          # Forward to another service
    "github_reaction",  # Add GitHub reaction (eyes, +1, heart, etc.)
    "github_label",     # Add GitHub labels
]


@router.get("/webhooks")
async def list_webhooks(db: AsyncSession = Depends(get_db_session)):
    """List all registered webhooks."""
    try:
        result = await db.execute(
            select(WebhookConfigDB).options(selectinload(WebhookConfigDB.commands))
        )
        webhooks = result.scalars().all()
        
        response = []
        for webhook in webhooks:
            commands = []
            for cmd in webhook.commands:
                commands.append({
                    "command_id": cmd.command_id,
                    "trigger": cmd.trigger,
                    "action": cmd.action,
                    "agent": cmd.agent,
                    "template": cmd.template,
                    "conditions": json.loads(cmd.conditions_json) if cmd.conditions_json else None,
                    "priority": cmd.priority
                })
            
            response.append({
                "webhook_id": webhook.webhook_id,
                "name": webhook.name,
                "provider": webhook.provider,
                "endpoint": webhook.endpoint,
                "enabled": webhook.enabled,
                "created_at": webhook.created_at.isoformat(),
                "created_by": webhook.created_by,
                "commands": commands
            })
        
        return response
    except Exception as e:
        logger.error("list_webhooks_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks", status_code=201)
async def create_webhook(
    webhook: WebhookCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new webhook configuration."""
    try:
        if webhook.provider not in VALID_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}"
            )
        
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.name == webhook.name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Webhook with name '{webhook.name}' already exists"
            )
        
        webhook_id = f"webhook-{uuid.uuid4().hex[:12]}"
        endpoint = f"/webhooks/{webhook.provider}/{webhook_id}"
        
        config_data = {
            "name": webhook.name,
            "provider": webhook.provider,
            "enabled": webhook.enabled,
            "commands": [cmd.model_dump() for cmd in webhook.commands]
        }
        
        webhook_db = WebhookConfigDB(
            webhook_id=webhook_id,
            name=webhook.name,
            provider=webhook.provider,
            endpoint=endpoint,
            secret=webhook.secret,
            enabled=webhook.enabled,
            config_json=json.dumps(config_data),
            created_by="api-user",
            created_at=datetime.utcnow()
        )
        db.add(webhook_db)
        
        for cmd in webhook.commands:
            command_id = f"cmd-{uuid.uuid4().hex[:12]}"
            command_db = WebhookCommandDB(
                command_id=command_id,
                webhook_id=webhook_id,
                trigger=cmd.trigger,
                action=cmd.action,
                agent=cmd.agent,
                template=cmd.template,
                conditions_json=json.dumps(cmd.conditions) if cmd.conditions else None,
                priority=cmd.priority
            )
            db.add(command_db)
        
        await db.commit()
        
        logger.info("webhook_created", webhook_id=webhook_id, name=webhook.name)
        
        return {
            "success": True,
            "data": {
                "webhook_id": webhook_id,
                "endpoint": endpoint,
                "name": webhook.name,
                "provider": webhook.provider
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("create_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get webhook details by ID."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        commands = []
        for cmd in webhook.commands:
            commands.append({
                "command_id": cmd.command_id,
                "trigger": cmd.trigger,
                "action": cmd.action,
                "agent": cmd.agent,
                "template": cmd.template,
                "conditions": json.loads(cmd.conditions_json) if cmd.conditions_json else None,
                "priority": cmd.priority
            })
        
        return {
            "webhook_id": webhook.webhook_id,
            "name": webhook.name,
            "provider": webhook.provider,
            "endpoint": webhook.endpoint,
            "enabled": webhook.enabled,
            "created_at": webhook.created_at.isoformat(),
            "created_by": webhook.created_by,
            "commands": commands
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    webhook_update: WebhookUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update webhook configuration."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        if webhook_update.name is not None:
            webhook.name = webhook_update.name
        if webhook_update.enabled is not None:
            webhook.enabled = webhook_update.enabled
        if webhook_update.secret is not None:
            webhook.secret = webhook_update.secret
        
        webhook.updated_at = datetime.utcnow()
        
        config_data = json.loads(webhook.config_json)
        if webhook_update.name is not None:
            config_data["name"] = webhook_update.name
        if webhook_update.enabled is not None:
            config_data["enabled"] = webhook_update.enabled
        webhook.config_json = json.dumps(config_data)
        
        await db.commit()
        
        logger.info("webhook_updated", webhook_id=webhook_id)
        
        return {"success": True, "webhook_id": webhook_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("update_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        await db.delete(webhook)
        await db.commit()
        
        logger.info("webhook_deleted", webhook_id=webhook_id)
        
        return {"success": True, "webhook_id": webhook_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("delete_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/enable")
async def enable_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Enable webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        webhook.enabled = True
        webhook.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info("webhook_enabled", webhook_id=webhook_id)
        
        return {"success": True, "webhook_id": webhook_id, "enabled": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("enable_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/disable")
async def disable_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Disable webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        webhook.enabled = False
        webhook.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info("webhook_disabled", webhook_id=webhook_id)
        
        return {"success": True, "webhook_id": webhook_id, "enabled": False}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("disable_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/{webhook_id}/commands")
async def list_commands(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """List all commands for a webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        commands = []
        for cmd in webhook.commands:
            commands.append({
                "command_id": cmd.command_id,
                "trigger": cmd.trigger,
                "action": cmd.action,
                "agent": cmd.agent,
                "template": cmd.template,
                "conditions": json.loads(cmd.conditions_json) if cmd.conditions_json else None,
                "priority": cmd.priority
            })
        
        return commands
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_commands_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/commands", status_code=201)
async def add_command(
    webhook_id: str,
    command: WebhookCommandCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Add command to webhook."""
    try:
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        if command.action not in VALID_ACTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action. Must be one of: {', '.join(VALID_ACTIONS)}"
            )
        
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        command_db = WebhookCommandDB(
            command_id=command_id,
            webhook_id=webhook_id,
            trigger=command.trigger,
            action=command.action,
            agent=command.agent,
            template=command.template,
            conditions_json=json.dumps(command.conditions) if command.conditions else None,
            priority=command.priority
        )
        db.add(command_db)
        await db.commit()
        
        logger.info("command_added", webhook_id=webhook_id, command_id=command_id)
        
        return {
            "success": True,
            "data": {
                "command_id": command_id,
                "webhook_id": webhook_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("add_command_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/webhooks/{webhook_id}/commands/{command_id}")
async def update_command(
    webhook_id: str,
    command_id: str,
    command_update: WebhookCommandUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update webhook command."""
    try:
        result = await db.execute(
            select(WebhookCommandDB).where(
                WebhookCommandDB.command_id == command_id,
                WebhookCommandDB.webhook_id == webhook_id
            )
        )
        command = result.scalar_one_or_none()
        
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        
        if command_update.trigger is not None:
            command.trigger = command_update.trigger
        if command_update.action is not None:
            if command_update.action not in VALID_ACTIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action. Must be one of: {', '.join(VALID_ACTIONS)}"
                )
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
        
        logger.info("command_updated", command_id=command_id)
        
        return {"success": True, "command_id": command_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("update_command_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}/commands/{command_id}")
async def delete_command(
    webhook_id: str,
    command_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete webhook command."""
    try:
        result = await db.execute(
            select(WebhookCommandDB).where(
                WebhookCommandDB.command_id == command_id,
                WebhookCommandDB.webhook_id == webhook_id
            )
        )
        command = result.scalar_one_or_none()
        
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        
        await db.delete(command)
        await db.commit()
        
        logger.info("command_deleted", command_id=command_id)
        
        return {"success": True, "command_id": command_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("delete_command_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
