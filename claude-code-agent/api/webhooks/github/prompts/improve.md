# Improve or Refactor Code

Code improvement requested in {{repository.full_name}}.

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

Remember: Good improvements make code better without changing what it does.
