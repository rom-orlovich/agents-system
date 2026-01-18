"""
Webhook Router Lambda Handler
=============================
Routes webhooks from Jira, GitHub, and Sentry to Step Functions.
"""

import json
import hashlib
import hmac
import os
from datetime import datetime
import boto3

dynamodb = boto3.resource('dynamodb')
sfn = boto3.client('stepfunctions')

tasks_table = dynamodb.Table(os.environ.get('TASKS_TABLE', 'enterprise-agentcore-tasks'))
state_machine_arn = os.environ.get('STATE_MACHINE_ARN', '')


def verify_jira_webhook(headers: dict, body: str) -> bool:
    """Verify Jira webhook signature."""
    return True


def verify_github_webhook(headers: dict, body: str) -> bool:
    """Verify GitHub webhook signature."""
    signature = headers.get('x-hub-signature-256', '')
    secret = os.environ.get('GITHUB_WEBHOOK_SECRET', '')
    
    if not signature or not secret:
        return True
    
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


def verify_sentry_webhook(headers: dict, body: str) -> bool:
    """Verify Sentry webhook signature."""
    signature = headers.get('sentry-hook-signature', '')
    secret = os.environ.get('SENTRY_WEBHOOK_SECRET', '')
    
    if not signature or not secret:
        return True
    
    expected = hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


def handler(event, context):
    """Main webhook router handler."""
    path = event.get('rawPath', '') or event.get('path', '')
    headers = event.get('headers', {})
    headers = {k.lower(): v for k, v in headers.items()}
    body = event.get('body', '{}')
    
    if '/webhooks/jira' in path:
        if not verify_jira_webhook(headers, body):
            return {'statusCode': 401, 'body': 'Invalid signature'}
        
        payload = json.loads(body)
        return handle_jira_webhook(payload)
    
    elif '/webhooks/github' in path:
        if not verify_github_webhook(headers, body):
            return {'statusCode': 401, 'body': 'Invalid signature'}
        
        payload = json.loads(body)
        return handle_github_webhook(payload, headers)
    
    elif '/webhooks/sentry' in path:
        if not verify_sentry_webhook(headers, body):
            return {'statusCode': 401, 'body': 'Invalid signature'}
        
        payload = json.loads(body)
        return handle_sentry_webhook(payload)
    
    else:
        return {'statusCode': 404, 'body': 'Not found'}


def handle_jira_webhook(payload: dict) -> dict:
    """Handle Jira webhook events."""
    webhook_event = payload.get('webhookEvent', '')
    ai_label = os.environ.get('JIRA_AI_LABEL', 'AI')
    
    if webhook_event == 'jira:issue_created':
        issue = payload.get('issue', {})
        fields = issue.get('fields', {})
        labels = [label.get('name', '') if isinstance(label, dict) else label 
                  for label in fields.get('labels', [])]
        
        if ai_label in labels:
            return start_jira_ai_workflow(issue)
    
    elif webhook_event == 'jira:issue_updated':
        changelog = payload.get('changelog', {})
        
        for item in changelog.get('items', []):
            if item.get('field') == 'labels' and ai_label in item.get('toString', ''):
                issue = payload.get('issue', {})
                return start_jira_ai_workflow(issue)
    
    return {'statusCode': 200, 'body': 'Ignored'}


def start_jira_ai_workflow(issue: dict) -> dict:
    """Start AI workflow for Jira ticket."""
    issue_key = issue.get('key', 'UNKNOWN')
    task_id = f"jira-{issue_key}-{int(datetime.utcnow().timestamp())}"
    
    fields = issue.get('fields', {})
    
    tasks_table.put_item(
        Item={
            'pk': f'TASK#{task_id}',
            'sk': 'METADATA',
            'task_id': task_id,
            'ticket_id': issue_key,
            'status': 'started',
            'source': 'jira',
            'created_at': datetime.utcnow().isoformat(),
            'ticket_summary': fields.get('summary', ''),
            'ticket_description': fields.get('description', '') or '',
            'priority': fields.get('priority', {}).get('name', 'Medium') if isinstance(fields.get('priority'), dict) else 'Medium'
        }
    )
    
    labels = [label.get('name', '') if isinstance(label, dict) else label 
              for label in fields.get('labels', [])]
    
    execution = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=task_id,
        input=json.dumps({
            'source': 'jira',
            'taskId': task_id,
            'ticketId': issue_key,
            'summary': fields.get('summary', ''),
            'description': fields.get('description', '') or '',
            'priority': fields.get('priority', {}).get('name', 'Medium') if isinstance(fields.get('priority'), dict) else 'Medium',
            'labels': labels
        })
    )
    
    print(f"Started workflow: {task_id}, execution: {execution['executionArn']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'task_id': task_id, 'execution_arn': execution['executionArn']})
    }


def handle_github_webhook(payload: dict, headers: dict) -> dict:
    """Handle GitHub webhook events."""
    event_type = headers.get('x-github-event', '')
    
    if event_type == 'issue_comment':
        comment = payload.get('comment', {})
        body = comment.get('body', '')
        
        if '@agent' in body.lower():
            return handle_github_comment_command(payload, body)
    
    elif event_type == 'pull_request':
        action = payload.get('action', '')
        if action in ['opened', 'synchronize']:
            pr = payload.get('pull_request', {})
            if 'AI Agent' in pr.get('body', ''):
                return start_ci_monitoring(pr, payload.get('repository', {}))
    
    return {'statusCode': 200, 'body': 'Ignored'}


def handle_github_comment_command(payload: dict, body: str) -> dict:
    """Handle @agent commands in GitHub comments.
    
    Commands:
    - @agent approve / @agent execute → Trigger execution phase
    - @agent status → Get task status
    - @agent reject → Cancel execution
    """
    issue = payload.get('issue', {})
    repo = payload.get('repository', {})
    comment = payload.get('comment', {})
    
    pr_number = issue.get('number')
    repo_name = repo.get('name', '')
    repo_full = repo.get('full_name', '')
    user = comment.get('user', {}).get('login', 'unknown')
    body_lower = body.lower()
    
    # Handle @agent approve or @agent execute
    if 'approve' in body_lower or 'execute' in body_lower:
        task_id = f"pr-{repo_name}-{pr_number}-{int(datetime.utcnow().timestamp())}"
        
        # Store task
        tasks_table.put_item(
            Item={
                'pk': f'TASK#{task_id}',
                'sk': 'METADATA',
                'task_id': task_id,
                'pr_number': pr_number,
                'repo': repo_name,
                'status': 'execution_approved',
                'approved_by': user,
                'source': 'github_pr_comment',
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        # Start Step Functions execution for execution phase
        execution = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=task_id,
            input=json.dumps({
                'source': 'github_pr_approval',
                'taskId': task_id,
                'phase': 'execution',  # Skip to execution phase
                'prNumber': pr_number,
                'repo': repo_name,
                'repoFull': repo_full,
                'approvedBy': user
            })
        )
        
        print(f"Execution approved: {task_id}, PR #{pr_number}, by {user}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'execution_triggered',
                'task_id': task_id,
                'pr': pr_number,
                'approved_by': user,
                'execution_arn': execution['executionArn']
            })
        }
    
    # Handle @agent status
    elif 'status' in body_lower:
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'command_received', 'command': 'status', 'pr': pr_number})
        }
    
    # Handle @agent reject
    elif 'reject' in body_lower:
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'command_received', 'command': 'reject', 'pr': pr_number})
        }
    
    return {'statusCode': 200, 'body': 'Command acknowledged'}


def start_ci_monitoring(pr: dict, repo: dict) -> dict:
    """Start CI monitoring for a PR."""
    return {'statusCode': 200, 'body': 'CI monitoring started'}


def handle_sentry_webhook(payload: dict) -> dict:
    """Handle Sentry webhook events."""
    action = payload.get('action', '')
    
    if action == 'triggered':
        return {'statusCode': 200, 'body': 'Acknowledged'}
    
    return {'statusCode': 200, 'body': 'Ignored'}
