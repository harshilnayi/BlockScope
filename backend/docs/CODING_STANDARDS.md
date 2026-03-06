# BlockScope Coding Standards

## Python Style

- PEP 8 compliance (enforced by black + flake8)
- Type hints on all functions
- Docstrings on all classes + public methods

## Naming

- Classes: PascalCase (Finding, VulnerabilityRule)
- Functions: snake_case (detect_reentrancy)
- Constants: UPPER_SNAKE_CASE (CRITICAL_SEVERITY)

## Testing

- Test files: test\_<module>.py
- Test functions: test\_<feature>
- Minimum 80% coverage

## Commits

- Format: type(scope): description
- Example: feat(analysis): add reentrancy detector
- Types: feat, fix, docs, style, refactor, test, chore
