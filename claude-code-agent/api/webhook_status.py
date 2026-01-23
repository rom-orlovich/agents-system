"""Webhook status and monitoring API."""

import os
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import structlog

from core.config import settings
from core.database import get_session as get_db_session
from core.database.models import WebhookConfigDB, WebhookEventDB
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
        
        # Get event counts by provider (for static webhooks)
        events_by_provider_query = select(
            WebhookEventDB.provider,
            func.count(WebhookEventDB.event_id).label("count"),
            func.max(WebhookEventDB.created_at).label("last_event")
        ).group_by(WebhookEventDB.provider)
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
            # Check if webhook is active (has secret configured if required)
            is_active = True
            has_secret = False
            if config.requires_signature and config.secret_env_var:
                secret_value = os.getenv(config.secret_env_var)
                has_secret = bool(secret_value)
                is_active = has_secret  # Only active if secret is configured
                logger.debug(
                    "static_webhook_secret_check",
                    name=config.name,
                    secret_env_var=config.secret_env_var,
                    has_secret=has_secret,
                    is_active=is_active
                )
            
            # Get event stats for this provider
            provider_stats = events_by_provider.get(config.source, {"count": 0, "last_event": None})
            
            # Build public URL
            public_url = None
            if settings.webhook_public_domain:
                public_url = f"https://{settings.webhook_public_domain}{config.endpoint}"
            
            webhook_statuses.append({
                "webhook_id": f"static-{config.name}",  # Unique ID for static webhooks
                "name": config.name,
                "provider": config.source,
                "endpoint": config.endpoint,
                "public_url": public_url,
                "enabled": is_active,
                "is_builtin": True,
                "event_count": provider_stats["count"],
                "last_event_at": provider_stats["last_event"].isoformat() if provider_stats["last_event"] else None,
                "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
                "has_secret": has_secret,
            })
        
        # Get dynamic webhooks from database
        result = await db.execute(
            select(WebhookConfigDB).order_by(WebhookConfigDB.created_at.desc())
        )
        db_webhooks = result.scalars().all()
        
        for webhook in db_webhooks:
            # Count events for this webhook
            event_count_result = await db.execute(
                select(func.count(WebhookEventDB.event_id))
                .where(WebhookEventDB.webhook_id == webhook.webhook_id)
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
                public_url = f"https://{settings.webhook_public_domain}{webhook.endpoint}"
            
            webhook_statuses.append({
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
            })
        
        return {
            "success": True,
            "data": {
                "webhooks": webhook_statuses,
                "total_count": len(webhook_statuses),
                "active_count": sum(1 for w in webhook_statuses if w["enabled"]),
                "public_domain": settings.webhook_public_domain,
            }
        }
    
    except Exception as e:
        logger.error("get_webhooks_status_error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/webhooks/{webhook_id}/events")
async def get_webhook_events(
    webhook_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
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
            ]
        }
    
    except Exception as e:
        logger.error("get_webhook_events_error", error=str(e), webhook_id=webhook_id)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/webhooks/events/recent")
async def get_recent_webhook_events(
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
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
            ]
        }
    
    except Exception as e:
        logger.error("get_recent_webhook_events_error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }
