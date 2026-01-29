# Type Safety Rule

## Enforcement Level
CRITICAL - Must never be violated

## Rule
Never use `any` types or force unwrapping (`!!`) in any code.

## Rationale
Type safety prevents runtime errors and makes code more maintainable. Using `any` defeats the purpose of static typing.

## Requirements
1. All function parameters must have explicit types
2. All return types must be explicit
3. Optional values must be handled explicitly
4. Use type guards for narrowing types
5. Use union types instead of `any`

## Examples

### ❌ WRONG
```python
def process_data(data: Any) -> Any:
    return data.get("value")
```

### ✅ CORRECT
```python
def process_data(data: dict[str, str | int]) -> str | int | None:
    if "value" not in data:
        return None
    return data["value"]
```

## Enforcement
Code review must reject any code containing `any` types or force unwrapping.
