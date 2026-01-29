# Address Change Request

Changes have been requested for {{event_type}} in {{repository.full_name}}.

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
   - Mark sections that changed with REVISED labels

5. **Post the Revision**
   - Use github-operations skill to post your revised work
   - Run: `python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} revised_plan.md`
   - Tag the reviewer to request re-review

## Revision Quality

- **Responsive**: Address every point of feedback
- **Transparent**: Show what changed and why
- **Improved**: Don't just make minimal changes - genuinely improve the work
- **Humble**: Accept feedback graciously

Remember: Feedback is an opportunity to improve. Take it seriously and produce better work.
