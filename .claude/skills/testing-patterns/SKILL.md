---
name: testing-patterns
description: Universal testing principles — test pyramid, AAA pattern, mocking strategies, and coverage targets
---

## Test Pyramid

```
        /  E2E  \        — Few, slow, high confidence
       / Integration \   — Some, medium speed
      /    Unit Tests   \— Many, fast, focused
```

- **Unit tests** (70%): Test individual functions in isolation. Fast, many.
- **Integration tests** (20%): Test modules working together (API + DB, component + hook).
- **E2E tests** (10%): Test full user journeys through the real app. Slow, few.

## Arrange-Act-Assert (AAA)

Every test follows this structure:

```
test('should calculate total with tax', () => {
  // Arrange — set up test data
  const items = [{ price: 10 }, { price: 20 }];
  const taxRate = 0.1;

  // Act — execute the function
  const total = calculateTotal(items, taxRate);

  // Assert — verify the result
  expect(total).toBe(33);
});
```

## What to Test

**Always test:**
- Happy path (normal inputs → expected output)
- Edge cases (empty, null, undefined, zero, max values)
- Error cases (invalid input, missing data, network failure)
- Boundary values (off-by-one, exactly at limits)
- Security-critical paths (auth, permissions, input validation)

**Don't test:**
- Implementation details (private methods, internal state)
- Third-party library internals
- Trivial getters/setters with no logic
- CSS styling or pixel-perfect layouts

## Mocking Strategy

| What | When to Mock |
|------|-------------|
| External APIs | Always — they're slow and unreliable |
| Database | Integration tests use real DB, unit tests mock |
| Time/Date | When testing time-dependent logic |
| File system | When testing file operations |
| Environment | When testing env-dependent behavior |

Rules:
- Mock at the boundary, not deep inside
- Prefer dependency injection over global mocks
- Reset mocks between tests (`beforeEach` / `afterEach`)
- Never mock what you're testing

## Test Naming

Use descriptive names that explain the scenario:

```
// Good
"should return 404 when user does not exist"
"should hash password before saving to database"
"should retry failed request up to 3 times"

// Bad
"test1"
"works correctly"
"handles error"
```

## Coverage Targets

- **80% minimum** for all code
- **100% required** for: auth logic, financial calculations, security-critical code
- Coverage measures lines hit, not correctness — high coverage with weak assertions is useless
- Focus on meaningful assertions, not just line coverage

## Common Anti-Patterns

- Testing implementation instead of behavior
- Tests that pass regardless of the implementation
- Shared mutable state between tests (tests must be independent)
- Over-mocking (prefer integration tests when possible)
- Ignoring flaky tests (fix the root cause immediately)
- Testing only the happy path
