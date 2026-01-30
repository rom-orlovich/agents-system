# Skill Creator - Skill for Creating Skills

## Purpose
This skill enables Claude to create well-structured, reusable skills following Claude Code best practices.

## When to Use
- User requests to create a new skill
- Need to encapsulate a reusable capability
- Building modular functionality for agents

## Skill Structure Template

```markdown
# [Skill Name] - [Brief Description]

## Purpose
[Single sentence describing what this skill does]

## When to Use
- [Specific scenario 1]
- [Specific scenario 2]
- [Specific scenario 3]

## Inputs
- **[input_name]**: [type] - [description]
- **[input_name]**: [type] - [description]

## Outputs
- **[output_name]**: [type] - [description]

## Process
1. [Clear step-by-step instructions]
2. [Each step should be actionable]
3. [Include error handling]

## Examples
\`\`\`[language]
[Code example showing usage]
\`\`\`

## Dependencies
- [Required tool 1]
- [Required skill 2]

## Error Handling
- **[Error Type]**: [How to handle]
- **[Error Type]**: [How to handle]

## Best Practices
- [Practice 1]
- [Practice 2]
```

## Creation Process

### 1. Understand Requirements
- Clarify the skill's purpose with user
- Identify inputs and expected outputs
- Determine when skill should be used

### 2. Design Skill Structure
- Follow single responsibility principle
- Make skill composable and reusable
- Define clear boundaries

### 3. Write Skill Documentation
- Use template above
- Be specific about when to use
- Include concrete examples
- Document all inputs/outputs

### 4. Test Skill Design
- Verify skill is self-contained
- Check all dependencies are listed
- Ensure examples are clear

### 5. Save Skill File
- Place in `.claude/skills/` directory
- Use kebab-case naming (e.g., `data-analysis.md`)
- Ensure file is markdown format

## Best Practices

### Do's
- ✅ Keep skills focused on single capability
- ✅ Make skills composable (can be combined)
- ✅ Provide concrete examples
- ✅ Document all dependencies
- ✅ Include error handling guidance

### Don'ts
- ❌ Create overly broad skills
- ❌ Mix multiple capabilities in one skill
- ❌ Skip documentation
- ❌ Forget to specify when to use
- ❌ Leave out error handling

## Example Usage

User: "Create a skill for analyzing test coverage"

Response:
1. Create file `.claude/skills/test-coverage-analysis.md`
2. Define purpose: "Analyze test coverage and identify gaps"
3. Specify inputs: test files, source files
4. Specify outputs: coverage report, missing tests list
5. Write step-by-step process
6. Add examples with pytest and coverage.py
7. Document dependencies: pytest, coverage
8. Include error handling for missing files

## Validation Checklist
- [ ] Skill has clear, single purpose
- [ ] "When to Use" section lists 3+ scenarios
- [ ] All inputs documented with types
- [ ] All outputs documented
- [ ] Process steps are actionable
- [ ] At least one example provided
- [ ] Dependencies listed
- [ ] Error handling documented
- [ ] File saved in `.claude/skills/`
- [ ] Filename uses kebab-case

## Dependencies
- Write tool (to create skill file)
- Understanding of Claude Code skill system

## Related
- See: `agent-creator.md` for creating agents that use skills
- See: `rule-creator.md` for creating rules that govern skill execution
- See: https://code.claude.com/docs/en/skills
