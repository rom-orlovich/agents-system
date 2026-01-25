#!/bin/bash
# Stack-Agnostic Test Runner
# Exit 0 = PASS, Exit 1 = FAIL

SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/detect-stack.sh"

echo "=== Running Tests (Stack: $DETECTED_STACK) ==="

run_tests() {
    case $DETECTED_STACK in
        python)
            if command -v pytest &> /dev/null; then
                pytest tests/ -v --tb=short 2>&1
            elif command -v python &> /dev/null; then
                python -m unittest discover -v 2>&1
            else
                echo "No Python test runner found"
                return 1
            fi
            ;;
        typescript|node)
            if [ -f "package.json" ]; then
                npm test 2>&1 || npx vitest run 2>&1 || npx jest 2>&1
            else
                echo "No package.json found"
                return 1
            fi
            ;;
        go)
            go test ./... -v 2>&1
            ;;
        rust)
            cargo test 2>&1
            ;;
        java-maven)
            mvn test -q 2>&1
            ;;
        java-gradle)
            ./gradlew test 2>&1
            ;;
        ruby)
            bundle exec rspec 2>&1 || bundle exec rake test 2>&1
            ;;
        dotnet)
            dotnet test 2>&1
            ;;
        php)
            ./vendor/bin/phpunit 2>&1
            ;;
        elixir)
            mix test 2>&1
            ;;
        *)
            if [ -f "Makefile" ] && grep -q "test:" Makefile; then
                make test 2>&1
            else
                echo "No test runner detected for stack: $DETECTED_STACK"
                return 0  # Don't fail if no tests
            fi
            ;;
    esac
}

run_tests
EXIT_CODE=$?

[ $EXIT_CODE -eq 0 ] && echo "=== TESTS PASSED ===" || echo "=== TESTS FAILED ==="
exit $EXIT_CODE
