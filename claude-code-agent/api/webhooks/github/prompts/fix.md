# Implement Fix for GitHub Issue

You are implementing a fix for GitHub issue #{{issue.number}} in {{repository.full_name}}.

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

Remember: This requires approval, so ensure your changes are well-tested and documented.
