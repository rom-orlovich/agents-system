# Create Implementation Plan

You are creating an implementation plan for GitHub issue #{{issue.number}} in {{repository.full_name}}.

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

Remember: The executor agent will follow your plan, so make it detailed and unambiguous.
