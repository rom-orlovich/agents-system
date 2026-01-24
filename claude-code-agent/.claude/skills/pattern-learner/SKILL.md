---
name: pattern-learner
description: Learn and apply successful patterns from codebase analysis
user-invocable: false
---

Analyzes codebase to identify successful patterns, anti-patterns, and best practices. Builds knowledge base of effective solutions.

## Capabilities

1. **Pattern Recognition** - Identify recurring code structures, design patterns, error handling patterns, testing strategies
2. **Anti-Pattern Detection** - God objects, spaghetti code, magic numbers, tight coupling, circular dependencies, N+1 queries
3. **Knowledge Base Building** - Extract pattern templates, document contexts, track effectiveness, store examples
4. **Pattern Application** - Suggest patterns for new code, recommend refactorings, validate usage

## Pattern Categories

- **Design Patterns** - Creational (Factory, Builder, Singleton), Structural (Adapter, Decorator, Facade), Behavioral (Strategy, Observer, Command)
- **Code Patterns** - Error handling, async operations, database operations, testing patterns

## Learning Process

1. **Scan** - Analyze codebase, identify structures, count occurrences, measure effectiveness
2. **Analysis** - Calculate success rate, measure maintainability, assess performance impact
3. **Extraction** - Create pattern templates, identify variations, document context
4. **Application** - Suggest patterns, recommend refactorings, validate usage

## Output Format

Report includes:
- Patterns identified (successful patterns, anti-patterns)
- Pattern catalog with examples
- Recommendations for applying patterns
- Anti-pattern refactoring suggestions

## Best Practices

- Focus on frequently used patterns
- Measure pattern effectiveness (test coverage, bug rate, maintainability)
- Document pattern context and variations
- Track pattern evolution over time
- Apply patterns consistently across codebase

See examples.md for pattern examples and reference.md for pattern catalog.
