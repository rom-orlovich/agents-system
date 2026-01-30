# Dependency Analysis Skill

## Purpose
Analyze package dependencies, detect vulnerabilities, and manage dependency health.

## Capabilities
- Parse dependency files (requirements.txt, pyproject.toml)
- Check for known vulnerabilities (CVE database)
- Identify outdated packages
- Detect dependency conflicts
- Analyze transitive dependencies
- Generate security reports

## Available Operations

### Parse Dependencies
```python
parse_requirements(file_path: str) -> list[Dependency]
```
Parse requirements.txt or pyproject.toml.

### Check Vulnerabilities
```python
check_vulnerabilities(dependencies: list[Dependency]) -> list[Vulnerability]
```
Check dependencies against CVE database.

### Find Outdated Packages
```python
find_outdated(dependencies: list[Dependency]) -> list[OutdatedPackage]
```
Identify packages with available updates.

### Detect Conflicts
```python
detect_conflicts(dependencies: list[Dependency]) -> list[Conflict]
```
Find version conflicts in dependency tree.

### Get Dependency Tree
```python
get_dependency_tree(package: str) -> DependencyTree
```
Build transitive dependency tree.

### Get License Info
```python
get_licenses(dependencies: list[Dependency]) -> dict[str, License]
```
Retrieve license information for packages.

### Suggest Updates
```python
suggest_safe_updates(dependencies: list[Dependency]) -> list[Update]
```
Recommend safe version upgrades.

## Data Models

### Dependency
```python
@dataclass
class Dependency:
    name: str
    version: str
    constraints: str  # e.g., ">=1.0.0,<2.0.0"
    extras: list[str]
```

### Vulnerability
```python
@dataclass
class Vulnerability:
    cve_id: str
    package: str
    affected_versions: str
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    fixed_in: str | None
    published_date: str
```

### OutdatedPackage
```python
@dataclass
class OutdatedPackage:
    name: str
    current_version: str
    latest_version: str
    latest_stable: str
    update_type: Literal["major", "minor", "patch"]
```

## Vulnerability Severity Levels
- **Critical**: Immediate action required, block deployment
- **High**: Fix within 7 days
- **Medium**: Fix within 30 days
- **Low**: Fix in next maintenance cycle

## When to Use
- Pull requests adding/updating dependencies
- Regular security audits (weekly/monthly)
- Before major releases
- After security advisories
- Dependency conflict resolution

## Example Workflows

### Security Audit
```python
deps = parse_requirements("requirements.txt")
vulns = check_vulnerabilities(deps)

critical = [v for v in vulns if v.severity == "critical"]
if critical:
    block_merge()
    notify_security_team(critical)

for vuln in vulns:
    create_security_report(vuln)
```

### Update Check
```python
deps = parse_requirements("requirements.txt")
outdated = find_outdated(deps)

for pkg in outdated:
    if pkg.update_type == "patch":
        suggest_immediate_update(pkg)
    elif pkg.update_type == "minor":
        suggest_planned_update(pkg)
    else:  # major
        require_review(pkg)
```

### Conflict Resolution
```python
deps = parse_requirements("requirements.txt")
conflicts = detect_conflicts(deps)

for conflict in conflicts:
    tree = get_dependency_tree(conflict.package)
    analyze_conflict_source(tree)
    suggest_resolution(conflict)
```

## Output Format

### Security Report
```markdown
## Dependency Security Report

**Total Packages:** X
**Vulnerabilities Found:** Y

### 🔴 Critical Vulnerabilities
- **CVE-2024-XXXX** in `package==1.2.3`
  - **Severity:** Critical (CVSS 9.8)
  - **Description:** [Description]
  - **Fixed in:** 1.2.4
  - **Action:** Upgrade immediately

### 🟡 High Vulnerabilities
[Same format]

### Outdated Packages
- `package` 1.0.0 → 2.0.0 (major update)
- `another` 1.5.0 → 1.5.2 (patch update)

### Recommendations
1. Upgrade critical packages immediately
2. Schedule high-priority updates within 7 days
3. Review major version upgrades for breaking changes
```

## Safe Update Strategy
1. **Patch updates** (1.0.0 → 1.0.1): Safe, auto-apply
2. **Minor updates** (1.0.0 → 1.1.0): Review changelog, test
3. **Major updates** (1.0.0 → 2.0.0): Full review, migration plan

## License Compliance
### Acceptable Licenses
- MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause
- Python Software Foundation
- ISC

### Restricted Licenses (Require Review)
- GPL, LGPL, AGPL
- Copyleft licenses

### Prohibited Licenses
- Proprietary licenses
- Commercial licenses without approval

## Integration with Other Skills
- **code-analysis**: Find unused dependencies
- **test-execution**: Verify updates don't break tests
- **git-operations**: Create update branches/PRs
