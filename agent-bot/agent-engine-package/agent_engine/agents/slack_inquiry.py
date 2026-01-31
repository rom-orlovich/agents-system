from .base import AgentContext, AgentResult, AgentType, BaseAgent, TaskSource

SLACK_INQUIRY_PROMPT = """You are a Slack inquiry agent. Respond to questions and requests from Slack.

Task ID: {task_id}
Channel: {channel}
Thread: {thread_ts}

## Message
User: {user}
Text: {text}

## Instructions
1. Analyze the question or request
2. If it's a code question, search the codebase
3. If it's a task request, determine if it needs implementation
4. If it's a status inquiry, check task status
5. Provide a helpful, concise response

## Response Guidelines
- Use Slack formatting (bold, code blocks, etc.)
- Be conversational but professional
- If you need clarification, ask specific questions
- If it requires code changes, indicate next steps
"""


class SlackInquiryAgent(BaseAgent):
    agent_type = AgentType.SLACK_INQUIRY

    def can_handle(self, context: AgentContext) -> bool:
        return (
            context.source == TaskSource.SLACK
            and context.event_type in ("app_mention", "message")
        )

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("slack_processing", task_id=context.task_id)

        event = context.payload.get("event", context.payload)
        channel = event.get("channel", "unknown")
        thread_ts = event.get("thread_ts", event.get("ts", ""))
        user = event.get("user", "unknown")
        text = event.get("text", "")

        prompt = SLACK_INQUIRY_PROMPT.format(
            task_id=context.task_id,
            channel=channel,
            thread_ts=thread_ts,
            user=user,
            text=text,
        )

        result = await self._execute_cli(prompt, "/app/repos/default")

        needs_implementation = self._check_needs_implementation(text)

        return AgentResult(
            success=result.get("success", False),
            output=result.get("output", ""),
            agent_type=self.agent_type,
            next_agent=AgentType.PLANNING if needs_implementation else None,
            artifacts={
                "channel": channel,
                "thread_ts": thread_ts,
                "user": user,
            },
            should_respond=True,
            response_channel=f"slack:{channel}:{thread_ts}",
        )

    def _check_needs_implementation(self, text: str) -> bool:
        text_lower = text.lower()
        implementation_keywords = [
            "implement",
            "create",
            "build",
            "add feature",
            "fix bug",
            "can you code",
        ]
        return any(keyword in text_lower for keyword in implementation_keywords)
