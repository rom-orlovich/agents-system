# Discovery Agent Examples

## Example 1: Authentication Feature

### Input
```json
{
  "ticketId": "PROJ-123",
  "summary": "Implement two-factor authentication (2FA)",
  "description": "Add 2FA support using TOTP (Time-based One-Time Password) for user accounts. Should support authenticator apps like Google Authenticator.",
  "labels": ["AI", "security", "authentication"],
  "priority": "High"
}
```

### Expected Output
```json
{
  "relevantRepos": [
    {
      "name": "auth-service",
      "relevance": 1.0,
      "reason": "Core authentication service - will handle TOTP generation and verification",
      "files": [
        {"path": "src/auth/mfa.py", "type": "source", "relevance": 1.0},
        {"path": "src/auth/models/user.py", "type": "source", "relevance": 0.9},
        {"path": "src/auth/routes/auth_routes.py", "type": "source", "relevance": 0.8},
        {"path": "tests/auth/test_mfa.py", "type": "test", "relevance": 1.0}
      ]
    },
    {
      "name": "user-service",
      "relevance": 0.8,
      "reason": "Manages user profiles - needs to store 2FA preferences",
      "files": [
        {"path": "src/models/user_preferences.py", "type": "source", "relevance": 0.9},
        {"path": "src/services/user_service.py", "type": "source", "relevance": 0.7}
      ]
    },
    {
      "name": "frontend",
      "relevance": 0.85,
      "reason": "UI for 2FA setup and verification flows",
      "files": [
        {"path": "src/pages/settings/Security.tsx", "type": "source", "relevance": 1.0},
        {"path": "src/components/auth/TwoFactorSetup.tsx", "type": "source", "relevance": 1.0},
        {"path": "src/components/auth/TwoFactorVerify.tsx", "type": "source", "relevance": 1.0}
      ]
    }
  ],
  "crossRepoDependencies": [
    {
      "from": "frontend",
      "to": "auth-service",
      "type": "API",
      "description": "POST /api/v1/auth/2fa/setup, POST /api/v1/auth/2fa/verify"
    },
    {
      "from": "auth-service",
      "to": "user-service",
      "type": "API",
      "description": "GET/PUT /api/v1/users/{id}/preferences"
    }
  ],
  "estimatedComplexity": "High",
  "recommendedApproach": "Implement TOTP library integration in auth-service, add user preferences storage, create frontend UI for setup flow with QR code generation"
}
```

---

## Example 2: Bug Fix - Database Query Optimization

### Input
```json
{
  "ticketId": "PROJ-456",
  "summary": "Fix slow loading of user dashboard",
  "description": "Users are reporting 10+ second load times on the dashboard. Stack trace shows timeout in UserActivityService.getRecentActivity()",
  "labels": ["AI", "bug", "performance"],
  "priority": "Critical"
}
```

### Expected Output
```json
{
  "relevantRepos": [
    {
      "name": "activity-service",
      "relevance": 1.0,
      "reason": "Contains UserActivityService with the reported slow method",
      "files": [
        {"path": "src/services/user_activity_service.py", "type": "source", "relevance": 1.0},
        {"path": "src/repositories/activity_repository.py", "type": "source", "relevance": 0.95},
        {"path": "src/models/activity.py", "type": "source", "relevance": 0.7},
        {"path": "tests/services/test_user_activity_service.py", "type": "test", "relevance": 1.0}
      ]
    },
    {
      "name": "database-migrations",
      "relevance": 0.7,
      "reason": "May need index additions for query optimization",
      "files": [
        {"path": "migrations/activity_tables.sql", "type": "config", "relevance": 0.8}
      ]
    }
  ],
  "crossRepoDependencies": [],
  "estimatedComplexity": "Low",
  "recommendedApproach": "Analyze query execution plan, add database indexes, implement pagination or caching for getRecentActivity()"
}
```

---

## Example 3: New Integration

### Input
```json
{
  "ticketId": "PROJ-789",
  "summary": "Add Stripe payment integration",
  "description": "Implement Stripe payment processing for subscription plans. Should support credit cards and support recurring billing.",
  "labels": ["AI", "feature", "payments"],
  "priority": "High"
}
```

### Expected Output
```json
{
  "relevantRepos": [
    {
      "name": "payments-service",
      "relevance": 1.0,
      "reason": "Core payments service - new or extended for Stripe integration",
      "files": [
        {"path": "src/providers/stripe_provider.py", "type": "source", "relevance": 1.0},
        {"path": "src/services/payment_service.py", "type": "source", "relevance": 0.9},
        {"path": "src/models/subscription.py", "type": "source", "relevance": 0.85},
        {"path": "src/webhooks/stripe_webhooks.py", "type": "source", "relevance": 0.95}
      ]
    },
    {
      "name": "user-service",
      "relevance": 0.75,
      "reason": "Needs to store subscription status per user",
      "files": [
        {"path": "src/models/user.py", "type": "source", "relevance": 0.8}
      ]
    },
    {
      "name": "frontend",
      "relevance": 0.9,
      "reason": "Payment UI, checkout flow, subscription management",
      "files": [
        {"path": "src/pages/Checkout.tsx", "type": "source", "relevance": 1.0},
        {"path": "src/components/payments/", "type": "source", "relevance": 0.95},
        {"path": "src/pages/settings/Subscription.tsx", "type": "source", "relevance": 0.8}
      ]
    },
    {
      "name": "api-gateway",
      "relevance": 0.6,
      "reason": "Needs Stripe webhook endpoint configuration",
      "files": [
        {"path": "config/routes.yaml", "type": "config", "relevance": 0.7}
      ]
    }
  ],
  "crossRepoDependencies": [
    {
      "from": "frontend",
      "to": "payments-service",
      "type": "API",
      "description": "POST /api/v1/payments/checkout, POST /api/v1/subscriptions"
    },
    {
      "from": "api-gateway",
      "to": "payments-service",
      "type": "API",
      "description": "Webhook route: POST /webhooks/stripe"
    },
    {
      "from": "payments-service",
      "to": "user-service",
      "type": "API",
      "description": "PUT /api/v1/users/{id}/subscription"
    }
  ],
  "estimatedComplexity": "High",
  "recommendedApproach": "Create Stripe provider in payments-service, implement webhook handlers for subscription events, add checkout UI with Stripe Elements"
}
```

---

## Example 4: Microservices Communication Issue

### Input
```json
{
  "ticketId": "PROJ-234",
  "summary": "Implement event-driven order notifications",
  "description": "When an order status changes, we need to notify the notifications service via event bus instead of direct API call to improve reliability.",
  "labels": ["AI", "architecture", "messaging"],
  "priority": "Medium"
}
```

### Expected Output
```json
{
  "relevantRepos": [
    {
      "name": "order-service",
      "relevance": 1.0,
      "reason": "Publishes order status change events",
      "files": [
        {"path": "src/services/order_service.py", "type": "source", "relevance": 1.0},
        {"path": "src/events/order_events.py", "type": "source", "relevance": 1.0},
        {"path": "src/publishers/event_publisher.py", "type": "source", "relevance": 0.9}
      ]
    },
    {
      "name": "notification-service",
      "relevance": 1.0,
      "reason": "Consumes order events and sends notifications",
      "files": [
        {"path": "src/consumers/order_consumer.py", "type": "source", "relevance": 1.0},
        {"path": "src/handlers/order_notification_handler.py", "type": "source", "relevance": 0.95}
      ]
    },
    {
      "name": "shared-events",
      "relevance": 0.85,
      "reason": "Shared event schema definitions",
      "files": [
        {"path": "schemas/order_events.json", "type": "config", "relevance": 1.0},
        {"path": "src/events/base.py", "type": "source", "relevance": 0.7}
      ]
    },
    {
      "name": "infrastructure",
      "relevance": 0.7,
      "reason": "Event bus configuration (SQS/SNS/EventBridge)",
      "files": [
        {"path": "terraform/eventbridge.tf", "type": "config", "relevance": 0.9},
        {"path": "terraform/sqs.tf", "type": "config", "relevance": 0.8}
      ]
    }
  ],
  "crossRepoDependencies": [
    {
      "from": "order-service",
      "to": "shared-events",
      "type": "shared-lib",
      "description": "Imports OrderStatusChanged event schema"
    },
    {
      "from": "notification-service",
      "to": "shared-events",
      "type": "shared-lib",
      "description": "Imports OrderStatusChanged event schema for consumption"
    },
    {
      "from": "order-service",
      "to": "notification-service",
      "type": "event",
      "description": "OrderStatusChanged event via EventBridge"
    }
  ],
  "estimatedComplexity": "Medium",
  "recommendedApproach": "Define event schema in shared-events, implement publisher in order-service, add consumer in notification-service with idempotency handling"
}
```
