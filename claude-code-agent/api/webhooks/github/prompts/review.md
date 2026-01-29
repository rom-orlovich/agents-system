# Review GitHub Pull Request

You are reviewing pull request #{{pull_request.number}} in {{repository.full_name}}.

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

Remember: Your goal is to improve code quality while supporting the developer.
