"""Hard-coded webhook configurations aligned with OLD Claude Code CLI structure."""

from typing import List
from shared.machine_models import WebhookConfig, WebhookCommand

# =============================================================================
# GITHUB WEBHOOK CONFIGURATION
# =============================================================================

GITHUB_WEBHOOK: WebhookConfig = WebhookConfig(
    name="github",
    endpoint="/webhooks/github",
    source="github",
    description="GitHub webhook for issues, PRs, and comments",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="analyze",
            aliases=["analysis", "analyze-issue"],
            description="Analyze an issue or PR",
            target_agent="planning",
            prompt_template="""You are analyzing GitHub {{event_type}} #{{issue.number}} in repository {{repository.full_name}}.

**Issue Title:** {{issue.title}}

**User's Request:** {{_user_content}}

**Full Comment/Description:**
{{comment.body}}

---

## Your Task

Perform a comprehensive analysis of this issue. If the user provided specific guidance in their request, focus on those aspects.

## Steps

1. **Gather Information**
   - Use the `github-operations` skill to fetch full issue details, related PRs, and relevant code context
   - Read any referenced files or code sections mentioned in the issue
   - Check for similar issues or past discussions

2. **Analyze**
   - Identify the root cause or core problem
   - Assess impact and severity
   - Consider potential solutions or approaches
   - Note any dependencies or blockers
   - If the user's request is unclear, identify what additional information is needed

3. **Document Your Analysis**
   - Create a well-structured analysis document (analysis.md)
   - Use clear headings, bullet points, and code examples where relevant
   - Include your findings, recommendations, and next steps
   - If you need clarification, clearly state what questions you have

4. **Post Response**
   - Use the github-operations skill to post your analysis back to the issue
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} analysis.md`

## Output Format

Your analysis should include:
- **Summary**: Brief overview of the issue
- **Root Cause**: What's causing this problem?
- **Impact**: Who/what is affected?
- **Recommendations**: What should be done?
- **Next Steps**: Clear actionable items

Remember: Be thorough but concise. Focus on actionable insights.""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="plan",
            aliases=["plan-fix", "create-plan"],
            description="Create a plan to fix an issue",
            target_agent="planning",
            prompt_template="""You are creating an implementation plan for GitHub issue #{{issue.number}} in {{repository.full_name}}.

**Issue Title:** {{issue.title}}

**User's Specific Request:** {{_user_content}}

**Full Issue Description:**
{{comment.body}}

---

## Your Task

Create a detailed, actionable implementation plan. This plan will guide the executor agent, so be specific and thorough.

## Steps

1. **Understand the Problem**
   - Use `github-operations` skill to fetch issue details, related code, and context
   - Use `Explore` agent (via Task tool) to understand the codebase structure
   - Identify all files that need changes

2. **Design the Solution**
   - Break down the problem into logical steps
   - Consider edge cases and potential issues
   - Identify dependencies between changes
   - Plan for testing and verification
   - If the user gave specific constraints or preferences, incorporate them

3. **Create the Plan Document**
   - Write a clear, structured plan (plan.md) with:
     - **Summary**: What will be implemented
     - **Approach**: High-level strategy
     - **Files to Modify**: List each file with specific changes
     - **Implementation Steps**: Numbered, sequential steps
     - **Testing Strategy**: How to verify the fix works
     - **Risks & Considerations**: Potential issues to watch for

4. **Post the Plan**
   - Use github-operations skill to post the plan for review
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} plan.md`

## Plan Quality Guidelines

- **Specific**: Avoid vague statements like "fix the bug" - explain exactly what needs to change
- **Testable**: Include how to verify each step works
- **Sequenced**: Order steps logically (dependencies first)
- **Scoped**: Stay focused on the issue at hand
- **Clear**: Use code examples where helpful

Remember: The executor agent will follow your plan, so make it detailed and unambiguous.""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix",
            aliases=["implement", "execute"],
            description="Implement a fix for an issue",
            target_agent="executor",
            prompt_template="""You are implementing a fix for GitHub issue #{{issue.number}} in {{repository.full_name}}.

**Issue Title:** {{issue.title}}

**User's Specific Instructions:** {{_user_content}}

**Full Issue Description:**
{{comment.body}}

---

## Your Task

Implement the fix following Test-Driven Development (TDD) principles. Write code that solves the issue reliably.

## Steps

1. **Understand the Requirements**
   - Use `github-operations` skill to fetch issue details and related discussions
   - Read the existing code to understand current behavior
   - If there's a plan (PLAN.md), follow it closely
   - If no plan exists, use `EnterPlanMode` to create one first

2. **Follow TDD Workflow**
   - Write tests FIRST that capture the desired behavior
   - Run tests to confirm they fail (proving they test the issue)
   - Implement the minimal code to make tests pass
   - Refactor for quality while keeping tests green
   - Use the `testing` skill for test creation and execution

3. **Implement the Fix**
   - Make focused changes that address the issue
   - Follow the codebase's existing patterns and style
   - Add proper error handling
   - Update documentation if needed
   - Keep changes minimal and targeted

4. **Verify the Fix**
   - Run all tests (not just new ones)
   - Test manually if appropriate
   - Ensure no regressions
   - Use the `verification` skill for quality checks

5. **Document Your Work**
   - Create a summary document (summary.md) with:
     - **What Was Fixed**: Brief description
     - **Changes Made**: List files modified and why
     - **Testing**: How you verified the fix
     - **Considerations**: Any edge cases or future improvements
   - Include before/after examples if helpful

6. **Post the Summary**
   - Use github-operations skill to post your implementation summary
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} summary.md`

## Code Quality Standards

- **Readable**: Clear variable names, logical flow
- **Tested**: Comprehensive test coverage
- **Safe**: Proper error handling, input validation
- **Maintainable**: Follow existing patterns, add comments for complex logic
- **Minimal**: Only change what's necessary

Remember: This requires approval, so ensure your changes are well-tested and documented.""",
            requires_approval=True,
        ),
        WebhookCommand(
            name="review",
            aliases=["code-review", "review-pr"],
            description="Review a pull request",
            target_agent="planning",
            prompt_template="""You are reviewing pull request #{{pull_request.number}} in {{repository.full_name}}.

**PR Title:** {{pull_request.title}}

**User's Specific Focus:** {{_user_content}}

**Full Comment:**
{{comment.body}}

---

## IMPORTANT: Extract PR Details First

Before running any commands, you MUST extract the PR number and repository info from task metadata:

```python
import json
metadata = json.loads(task.source_metadata)
payload = metadata.get("payload", {})
repo = payload.get("repository", {})
owner = repo.get("owner", {}).get("login")
repo_name = repo.get("name")
pr = payload.get("pull_request", {})
pr_number = pr.get("number")
```

**DO NOT use template variables like {{pull_request.number}} in bash commands - they will not work!**
**You MUST extract the actual values from task.source_metadata first.**

---

## Your Task

Perform a thorough code review. If the user requested specific aspects to check (e.g., "check the scroll button"), prioritize those areas.

## Steps

1. **Extract PR Details from Metadata**
   - Read `task.source_metadata` (JSON string)
   - Parse it to get: owner, repo_name, pr_number
   - Store these in variables for use in commands

2. **Fetch PR Details**
   - Use github-operations skill to get PR details and changed files
   - Run: `python .claude/skills/github-operations/scripts/review_pr.py {owner} {repo_name} {pr_number}`
   - Replace {owner}, {repo_name}, {pr_number} with actual values extracted from metadata
   - This provides: changed files, diff, commit messages, PR description

2. **Review the Code**
   - **Correctness**: Does the code do what it claims?
   - **Quality**: Is it well-structured, readable, maintainable?
   - **Security**: Any vulnerabilities or unsafe patterns?
   - **Performance**: Any obvious performance issues?
   - **Testing**: Are there tests? Do they cover edge cases?
   - **Documentation**: Are changes documented?
   - **User's Focus**: Address any specific concerns they mentioned

3. **Check for Issues**
   - Logic errors or bugs
   - Missing error handling
   - Breaking changes
   - Inconsistent style
   - Unclear variable names
   - Code duplication

4. **Create Review Document**
   - Write a structured review (review.md) with:
     - **Summary**: Overall assessment (approve/request changes/comment)
     - **Strengths**: What's done well
     - **Issues**: Problems found (categorized by severity)
     - **Suggestions**: Improvements (optional but helpful)
     - **Specific Feedback**: Line-by-line comments if needed
   - Be constructive and specific
   - Provide examples for suggested changes

5. **Post the Review**
   - Use github-operations skill to post your review
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {owner} {repo_name} {pr_number} review.md`
   - Use the same variables extracted from metadata in step 1

## Review Tone

- **Constructive**: Focus on improvement, not criticism
- **Specific**: Reference exact files/lines/functions
- **Educational**: Explain *why* something is an issue
- **Appreciative**: Acknowledge good work

Remember: Your goal is to improve code quality while supporting the developer.""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="approve",
            aliases=["lgtm", "approved", "ship-it"],
            description="Approve a pull request or plan",
            target_agent="executor",
            prompt_template="""Approval received for {{event_type}} in {{repository.full_name}}.

**Approver's Comment:** {{_user_content}}

**Full Comment:**
{{comment.body}}

---

## Your Task

Process this approval and proceed with execution if appropriate.

## Steps

1. **Verify Approval Context**
   - Check what is being approved (plan, PR, implementation)
   - Review any conditions or notes in the approval comment
   - Ensure all required approvals are present

2. **Check Readiness**
   - If this is a plan approval: Proceed with implementation
   - If this is a PR approval: Check if merge is possible (tests passing, no conflicts)
   - If this is a partial approval with conditions: Address those conditions first

3. **Execute or Acknowledge**
   - **For Plan Approval**: Begin implementation using the `fix` command workflow
   - **For PR Approval**: If all checks pass, you may merge (check repo permissions)
   - **For Conditional Approval**: Note what needs to be addressed before proceeding

4. **Document Action Taken**
   - Create a confirmation document (confirmation.md) stating:
     - What was approved
     - What action you're taking
     - Next steps or timeline
     - Any blockers or dependencies

5. **Post Confirmation**
   - Use github-operations skill to post your response
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} confirmation.md`

## Important

- Respect the approver's intent - if they added conditions, honor them
- If you're unsure whether to proceed, ask for clarification
- Document your actions clearly for transparency

Remember: Approval is trust - proceed responsibly.""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="reject",
            aliases=["changes-requested", "request-changes", "revise"],
            description="Request changes or reject a plan",
            target_agent="planning",
            prompt_template="""Changes have been requested for {{event_type}} in {{repository.full_name}}.

**Reviewer's Feedback:** {{_user_content}}

**Full Comment:**
{{comment.body}}

---

## Your Task

Address the feedback and revise your previous work (plan or implementation).

## Steps

1. **Understand the Feedback**
   - Carefully read all feedback points
   - Identify what needs to change
   - If feedback is unclear, ask clarifying questions using `AskUserQuestion` tool
   - Prioritize critical issues over minor suggestions

2. **Gather Context**
   - Review the original issue/PR to understand initial requirements
   - Check your previous plan or implementation
   - Use `github-operations` skill to fetch any additional context needed

3. **Revise Your Work**
   - Address each point of feedback systematically
   - For plan revisions: Update the plan with requested changes
   - For implementation revisions: Modify code to meet the new requirements
   - Explain *what* you changed and *why* in your revision

4. **Create Revision Document**
   - Write a clear revision document (revised_plan.md or revised_implementation.md) with:
     - **Summary of Changes**: What you revised
     - **Feedback Addressed**: Show how each point was handled
     - **Reasoning**: Explain your approach to the changes
     - **Questions**: Any clarifications still needed
   - Mark sections that changed with ✏️ or **REVISED** labels

5. **Post the Revision**
   - Use github-operations skill to post your revised work
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} revised_plan.md`
   - Tag the reviewer to request re-review

## Revision Quality

- **Responsive**: Address every point of feedback
- **Transparent**: Show what changed and why
- **Improved**: Don't just make minimal changes - genuinely improve the work
- **Humble**: Accept feedback graciously

Remember: Feedback is an opportunity to improve. Take it seriously and produce better work.""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="improve",
            aliases=["enhance", "refactor", "optimize"],
            description="Improve or refactor code",
            target_agent="executor",
            prompt_template="""Code improvement requested in {{repository.full_name}}.

**User's Improvement Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

---

## Your Task

Improve the codebase while maintaining functionality. This could be refactoring, optimization, or enhancement.

## Steps

1. **Understand the Improvement Request**
   - What specifically should be improved? (performance, readability, architecture, etc.)
   - What's the current state that needs improvement?
   - What are the success criteria?
   - If unclear, ask using `AskUserQuestion` tool

2. **Analyze Current Code**
   - Use `Explore` agent to understand the code structure
   - Identify areas that match the improvement criteria
   - Look for patterns that need refactoring
   - Check for performance bottlenecks if optimization is the goal

3. **Plan the Improvement**
   - Use `EnterPlanMode` to create an improvement plan
   - Consider impact on other parts of the codebase
   - Plan for backward compatibility if needed
   - Identify tests that need updating

4. **Implement Improvements**
   - **Preserve Behavior**: Don't change what the code does, only how it does it
   - **Write Tests First**: Ensure existing tests pass, add new ones if needed
   - **Refactor Incrementally**: Make small, safe changes
   - **Maintain Style**: Follow existing code conventions
   - **Measure Impact**: For performance improvements, show before/after metrics

5. **Types of Improvements**
   - **Refactoring**: Simplify logic, extract functions, reduce duplication
   - **Performance**: Optimize algorithms, reduce memory usage, improve speed
   - **Readability**: Better names, clearer structure, helpful comments
   - **Architecture**: Better separation of concerns, improved modularity
   - **Security**: Fix vulnerabilities, improve input validation
   - **Maintainability**: Reduce complexity, improve error handling

6. **Document Improvements**
   - Create an improvement summary (improvement_summary.md) with:
     - **What Was Improved**: Specific areas changed
     - **Why**: Justification for each improvement
     - **Impact**: Benefits gained (faster, clearer, safer, etc.)
     - **Trade-offs**: Any drawbacks or considerations
     - **Before/After**: Examples showing the improvement
     - **Testing**: How you verified nothing broke

7. **Post the Summary**
   - Use github-operations skill to post your improvement summary
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} improvement_summary.md`

## Improvement Principles

- **Safety First**: Don't break existing functionality
- **Test Coverage**: Ensure tests prove behavior is preserved
- **Measurable**: Show concrete improvements (numbers, examples)
- **Justified**: Explain why each change makes things better
- **Incremental**: Make focused improvements, not massive rewrites

Remember: Good improvements make code better without changing what it does.""",
            requires_approval=True,
        ),
    ],
    default_command="analyze",
    requires_signature=True,
    signature_header="X-Hub-Signature-256",
    secret_env_var="GITHUB_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# JIRA WEBHOOK CONFIGURATION
# =============================================================================

JIRA_WEBHOOK: WebhookConfig = WebhookConfig(
    name="jira",
    endpoint="/webhooks/jira",
    source="jira",
    description="Jira webhook for issue updates and comments",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="analyze",
            aliases=["analysis", "analyze-ticket"],
            description="Analyze a Jira ticket",
            target_agent="planning",
            prompt_template="""Analyze this Jira ticket:

Key: {{issue.key}}
Summary: {{issue.fields.summary}}
Description: {{issue.fields.description}}

Project: {{issue.fields.project.name}}

**User Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

1. Perform analysis addressing the user request.
2. Save to file (e.g., analysis.md).
3. If analysis indicates code changes are needed OR if user requests implementation:
   - Create a Draft PR with the analysis/plan
   - Use github-operations skill to create PR:
     .claude/skills/github-operations/scripts/create_draft_pr.sh owner/repo "[{{issue.key}}] Analysis" "$(cat analysis.md)"
   - Extract PR URL from output
   - Post analysis back to Jira with PR link:
     python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} analysis.md
   - Include PR URL in the Jira comment
4. If no code changes needed (test error, documentation only, etc.):
   - Post analysis back to Jira:
     python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} analysis.md
   - Clearly state "No PR created - no code changes required"

Always create a PR if:
- Code changes are needed
- User explicitly requests implementation
- Analysis identifies bugs or improvements requiring code changes

Do NOT create PR if:
- Analysis confirms it's a test error (no production bug)
- Only documentation updates needed
- Issue is already resolved
- User only requested analysis, not implementation""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="plan",
            aliases=["plan-fix", "create-plan"],
            description="Create a plan to resolve a Jira ticket",
            target_agent="planning",
            prompt_template="""Create a detailed plan to resolve this Jira ticket:

{{issue.key}}: {{issue.fields.summary}}

{{issue.fields.description}}

Project: {{issue.fields.project.name}}

**User Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

1. Create plan addressing the user request.
2. Save to file (e.g., plan.md).
3. Post plan back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} plan.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix",
            aliases=["implement", "execute"],
            description="Implement a fix for a Jira ticket",
            target_agent="executor",
            prompt_template="""Implement a fix for this Jira ticket:

{{issue.key}}: {{issue.fields.summary}}

{{issue.fields.description}}

Project: {{issue.fields.project.name}}

**User Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

1. Implement fix addressing the user request.
2. Save summary to file.
3. Post summary back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} summary.md""",
            requires_approval=True,
        ),
        WebhookCommand(
            name="approve",
            aliases=["lgtm", "approved", "ship-it"],
            description="Approve a plan or implementation",
            target_agent="executor",
            prompt_template="""Approval received for Jira ticket {{issue.key}}.

**User Comment:** {{_user_content}}

**Original Comment:**
{{comment.body}}

1. Process the approval
2. Proceed with execution if all approvals received
3. Post confirmation back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} confirmation.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="reject",
            aliases=["changes-requested", "request-changes", "revise"],
            description="Request changes or reject a plan",
            target_agent="planning",
            prompt_template="""Changes requested for Jira ticket {{issue.key}}.

**User Feedback:** {{_user_content}}

**Original Comment:**
{{comment.body}}

1. Analyze the feedback
2. Revise the plan/implementation
3. Post updated plan back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} revised_plan.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="improve",
            aliases=["enhance", "refactor", "optimize"],
            description="Improve or refactor code",
            target_agent="executor",
            prompt_template="""Improvement requested for Jira ticket {{issue.key}}.

**User Request:** {{_user_content}}

**Original Comment:**
{{comment.body}}

## Parse External Sources

If the user request mentions external sources (e.g., "by github/confluence code from xyz"), extract:
- Source type: github, confluence, or other
- Source reference: repository path, page URL, or identifier
- Code location: file path, function name, or section

Examples:
- "@agent improve jira ticket by github code from owner/repo path/to/file.py"
- "@agent improve jira ticket by confluence code from space:page:section"

## Steps

1. Parse user request to identify external source references if present
2. If external source specified:
   - Fetch code/content from GitHub (using github-operations skill) or Confluence
   - Analyze the external code/content
   - Understand how it relates to the Jira ticket
3. Analyze what needs improvement in the current codebase
4. Implement improvements based on external reference if provided
5. Post summary back to Jira with source references:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} improvement_summary.md

Include in summary:
- External sources referenced (if any)
- Improvements made
- Files modified""",
            requires_approval=True,
        ),
        WebhookCommand(
            name="discover",
            aliases=["code", "explore", "find-code", "code-insights"],
            description="Discover code and provide insights from GitHub/Confluence",
            target_agent="jira-code-plan",
            prompt_template="""Discover code and provide insights for Jira ticket {{issue.key}}.

**User Request:** {{_user_content}}

**Original Comment:**
{{comment.body}}

## Parse Discovery Sources

Extract source information from user request:
- Source type: github, confluence, or codebase
- Source reference: repository path, page URL, file path, or search terms
- What to discover: functions, classes, patterns, relationships

Examples:
- "@agent discover from github owner/repo path/to/file.py"
- "@agent discover from confluence space:page"
- "@agent discover authentication flow"

## Steps

1. Parse user request to identify discovery sources
2. Use discovery skill to search codebase or fetch from external sources:
   - If GitHub: Use github-operations skill to fetch code
   - If Confluence: Fetch content from Confluence
   - If codebase: Use discovery skill to search locally
3. Analyze discovered code/content:
   - Understand functionality and relationships
   - Identify patterns and dependencies
   - Extract key insights
4. Format findings with code snippets, file paths, and explanations
5. Post results back to Jira ticket:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} discovery_results.md

Include in results:
- Source references (GitHub URLs, Confluence links, file paths)
- Key findings and insights
- Code snippets with explanations
- Related files and dependencies""",
            requires_approval=False,
        ),
    ],
    default_command="analyze",
    requires_signature=True,
    signature_header="X-Jira-Signature",
    secret_env_var="JIRA_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# SLACK WEBHOOK CONFIGURATION
# =============================================================================

SLACK_WEBHOOK: WebhookConfig = WebhookConfig(
    name="slack",
    endpoint="/webhooks/slack",
    source="slack",
    description="Slack webhook for commands and mentions",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="help",
            aliases=["commands", "what-can-you-do"],
            description="Show available commands",
            target_agent="brain",
            prompt_template="""User asked for help in Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Generate help message with available commands.
2. Save to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} help.md {{event.ts}}""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="analyze",
            aliases=["analysis"],
            description="Analyze a request from Slack",
            target_agent="brain",
            prompt_template="""Analyze this Slack message:

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Perform analysis.
2. Save to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} analysis.md {{event.ts}}""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="execute",
            aliases=["do", "run"],
            description="Execute a command from Slack",
            target_agent="executor",
            prompt_template="""Execute this request from Slack:

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Execute request.
2. Save result/summary to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} result.md {{event.ts}}""",
            requires_approval=True,
        ),
        WebhookCommand(
            name="jira",
            aliases=["ticket", "jira-ticket", "query-jira"],
            description="Query Jira ticket context, status, and details",
            target_agent="slack-inquiry",
            prompt_template="""Query Jira ticket information from Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Extract ticket key(s) from the user's message (e.g., PROJ-123, TASK-456).
2. Use jira-operations skill to fetch ticket details:
   - Status, assignee, summary, description
   - Comments, attachments, linked issues
   - Sprint/board information if available
3. Format response with ticket information.
4. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} jira_query.md {{event.ts}}""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="discover",
            aliases=["code", "explore", "find-code", "code-insights"],
            description="Discover GitHub code, get insights about codebase",
            target_agent="slack-inquiry",
            prompt_template="""Discover code and provide insights from Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Parse the user's query to understand what code they want to discover:
   - Function/class names
   - File paths or patterns
   - Feature/functionality descriptions
   - Code relationships or dependencies
2. Use discovery skill to search and analyze codebase:
   - Find relevant files and functions
   - Understand code flow and relationships
   - Extract code snippets and examples
   - Identify dependencies and usage patterns
3. Format insights with code snippets, file paths, and explanations.
4. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} code_discovery.md {{event.ts}}""",
            requires_approval=False,
        ),
    ],
    default_command="analyze",
    requires_signature=True,
    signature_header="X-Slack-Signature",
    secret_env_var="SLACK_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# COLLECT ALL CONFIGS
# =============================================================================

WEBHOOK_CONFIGS: List[WebhookConfig] = [
    GITHUB_WEBHOOK,
    JIRA_WEBHOOK,
    SLACK_WEBHOOK,
]


# =============================================================================
# VALIDATION
# =============================================================================

def validate_webhook_configs() -> None:
    """Validate all webhook configurations at startup."""
    import structlog
    
    logger = structlog.get_logger()
    
    # Check for duplicate endpoints
    endpoints = [config.endpoint for config in WEBHOOK_CONFIGS]
    if len(endpoints) != len(set(endpoints)):
        duplicates = [ep for ep in endpoints if endpoints.count(ep) > 1]
        raise ValueError(f"Duplicate endpoints found: {duplicates}")
    
    # Check for duplicate names
    names = [config.name for config in WEBHOOK_CONFIGS]
    if len(names) != len(set(names)):
        duplicates = [n for n in names if names.count(n) > 1]
        raise ValueError(f"Duplicate names found: {duplicates}")
    
    # Validate each config (Pydantic will raise if invalid)
    for config in WEBHOOK_CONFIGS:
        # Validate endpoint pattern
        import re
        if not re.match(r"^/webhooks/[a-z0-9-]+$", config.endpoint):
            raise ValueError(f"Invalid endpoint pattern: {config.endpoint}")
        
        # Validate commands
        for cmd in config.commands:
            if not cmd.name:
                raise ValueError(f"Command in {config.name} has empty name")
            if not cmd.target_agent:
                raise ValueError(f"Command {cmd.name} in {config.name} has no target_agent")
            if not cmd.prompt_template:
                raise ValueError(f"Command {cmd.name} in {config.name} has no prompt_template")
    
    logger.info("webhook_configs_validated", count=len(WEBHOOK_CONFIGS))


def get_webhook_by_endpoint(endpoint: str) -> WebhookConfig:
    """Get webhook config by endpoint."""
    for config in WEBHOOK_CONFIGS:
        if config.endpoint == endpoint:
            return config
    raise ValueError(f"Webhook not found for endpoint: {endpoint}")
