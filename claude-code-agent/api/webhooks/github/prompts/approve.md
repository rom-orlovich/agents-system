# Process Approval

Approval received for {{event_type}} in {{repository.full_name}}.

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

Remember: Approval is trust - proceed responsibly.
