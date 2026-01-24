---
name: claude-config-updater
description: Updates CLAUDE.md optimally with Claude Code best practices from settings, memory, and best-practices documentation
user-invocable: true
---

Updates `.claude/CLAUDE.md` following Claude Code best practices, incorporating recommendations from official documentation on settings, memory management, and best practices.

## When to Use

Use this skill when:
- Setting up a new Claude Code agent configuration
- Updating existing CLAUDE.md to follow latest best practices
- Optimizing agent configuration for better performance
- Incorporating new Claude Code features and patterns
- Reviewing and improving delegation patterns

## Process

1. **Read current CLAUDE.md** - Understand existing configuration and structure
2. **Review reference documentation** - Check `reference.md` for latest best practices:
   - Settings: Model selection, tool permissions, context modes
   - Memory: Context management strategies, memory optimization
   - Best Practices: Delegation patterns, agent coordination, response styles
3. **Analyze existing configuration** - Identify areas for improvement:
   - Model selection appropriateness
   - Tool permissions optimization
   - Context mode selection
   - Delegation pattern effectiveness
   - Memory usage patterns
4. **Apply targeted updates** - Make incremental improvements:
   - Enhance model selection guidance
   - Optimize tool permissions
   - Improve delegation patterns
   - Add memory management strategies
   - Refine response style guidelines
5. **Preserve existing functionality** - Maintain compatibility with:
   - Existing sub-agents (planning, executor, orchestration)
   - Current workflows and patterns
   - User expectations and behavior
6. **Validate updates** - Ensure:
   - Format follows Claude Code standards
   - All sections are coherent and complete
   - No breaking changes to existing patterns

## Key Principles

- **Incremental Updates**: Make targeted improvements rather than wholesale rewrites
- **Backward Compatibility**: Preserve existing functionality while enhancing
- **Documentation-Driven**: Base updates on official Claude Code documentation
- **Validation**: Verify updates don't break existing agent patterns
- **Modularity**: Reference external documentation rather than duplicating content

## Reference Files

- **Complete documentation**: See [reference.md](reference.md) for settings, memory, and best-practices content
- **Examples**: See [examples.md](examples.md) for before/after examples of optimal configurations

## Output

Updated CLAUDE.md that:
- Follows Claude Code best practices
- Optimizes model selection and tool usage
- Implements effective memory management
- Uses optimal delegation patterns
- Maintains compatibility with existing sub-agents
