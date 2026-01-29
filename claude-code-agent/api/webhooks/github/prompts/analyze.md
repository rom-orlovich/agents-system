# Analyze GitHub Issue/PR

You are analyzing GitHub {{event_type}} #{{issue.number}} in repository {{repository.full_name}}.

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

Remember: Be thorough but concise. Focus on actionable insights.
