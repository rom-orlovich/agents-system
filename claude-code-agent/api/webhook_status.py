"""Webhook status and monitoring API."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import structlog

from core.config import settings
from core.database import get_session as get_db_session
from core.database.models import WebhookConfigDB, WebhookEventDB

logger = structlog.get_logger()

router = APIRouter()


@router.get("/webhooks-status")
async def get_webhooks_status(db: AsyncSession = Depends(get_db_session)):
    """
    Get status of all webhooks including URLs, event counts, and last activity.
    """
    try:
        # Get all webhooks with event counts
        result = await db.execute(
            select(WebhookConfigDB).order_by(WebhookConfigDB.created_at.desc())
        )
        webhooks = result.scalars().all()
        
        webhook_statuses = []
        
        for webhook in webhooks:
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
                "event_count": event_count,
                "last_event_at": last_event.isoformat() if last_event else None,
                "created_at": webhook.created_at.isoformat(),
                "has_secret": bool(webhook.secret),
            })
        
        # Count static endpoints (always 3: GitHub, Jira, Slack)
        static_count = 3
        
        return {
            "success": True,
            "data": {
                "webhooks": webhook_statuses,
                "total_count": len(webhook_statuses) + static_count,
                "active_count": sum(1 for w in webhook_statuses if w["enabled"]) + static_count,
                "public_domain": settings.webhook_public_domain,
                "static_endpoints": [
                    {
                        "name": "GitHub Static",
                        "endpoint": "/webhooks/github",
                        "public_url": f"https://{settings.webhook_public_domain}/webhooks/github" if settings.webhook_public_domain else None,
                        "provider": "github",
                        "type": "static",
                        "enabled": True
                    },
                    {
                        "name": "Jira Static",
                        "endpoint": "/webhooks/jira",
                        "public_url": f"https://{settings.webhook_public_domain}/webhooks/jira" if settings.webhook_public_domain else None,
                        "provider": "jira",
                        "type": "static",
                        "enabled": True
                    },
                    {
                        "name": "Slack Static",
                        "endpoint": "/webhooks/slack",
                        "public_url": f"https://{settings.webhook_public_domain}/webhooks/slack" if settings.webhook_public_domain else None,
                        "provider": "slack",
                        "type": "static",
                        "enabled": True
                    }
                ]
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
