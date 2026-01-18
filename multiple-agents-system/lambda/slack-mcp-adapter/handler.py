"""
Slack MCP Adapter Lambda Handler
================================
Exposes Slack API as MCP-compatible tools.
"""

import json
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN', ''))


def handler(event, context):
    """Lambda-based MCP adapter for Slack."""
    tool_name = event.get('tool')
    parameters = event.get('parameters', {})
    
    try:
        handlers = {
            'send_message': send_message,
            'send_blocks': send_blocks,
            'get_user_info': get_user_info,
            'list_channels': list_channels,
            'update_message': update_message,
        }
        
        handler_func = handlers.get(tool_name)
        if handler_func:
            return handler_func(parameters)
        else:
            return {'error': f'Unknown tool: {tool_name}'}
    
    except SlackApiError as e:
        return {'error': f'Slack API error: {e.response["error"]}'}
    except Exception as e:
        return {'error': str(e)}


def send_message(params: dict) -> dict:
    """Send a simple text message."""
    response = slack_client.chat_postMessage(
        channel=params['channel'],
        text=params['text']
    )
    return {
        'success': True,
        'ts': response['ts'],
        'channel': response['channel']
    }


def send_blocks(params: dict) -> dict:
    """Send a message with Block Kit blocks."""
    response = slack_client.chat_postMessage(
        channel=params['channel'],
        text=params.get('fallback_text', 'New message'),
        blocks=params['blocks']
    )
    return {
        'success': True,
        'ts': response['ts'],
        'channel': response['channel']
    }


def get_user_info(params: dict) -> dict:
    """Get information about a user."""
    response = slack_client.users_info(user=params['user_id'])
    return response['user']


def list_channels(params: dict) -> dict:
    """List channels."""
    response = slack_client.conversations_list(
        types=params.get('types', 'public_channel,private_channel')
    )
    return {
        'channels': response['channels']
    }


def update_message(params: dict) -> dict:
    """Update an existing message."""
    response = slack_client.chat_update(
        channel=params['channel'],
        ts=params['ts'],
        text=params.get('text'),
        blocks=params.get('blocks')
    )
    return {
        'success': True,
        'ts': response['ts']
    }
