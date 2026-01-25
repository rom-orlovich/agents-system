#!/bin/bash
# Stack-Agnostic Lint Check
# Exit 0 = PASS, Exit 1 = FAIL

SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/detect-stack.sh"

echo "=== Running Lint Check (Stack: $DETECTED_STACK) ==="

run_lint() {
    case $DETECTED_STACK in
        python)
            if command -v ruff &> /dev/null; then
                ruff check . 2>&1
            elif command -v flake8 &> /dev/null; then
                flake8 . 2>&1
            elif command -v pylint &> /dev/null; then
                pylint **/*.py 2>&1
            else
                echo "No Python linter found"
                return 0
            fi
            ;;
        typescript|node)
            if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f "eslint.config.js" ]; then
                npx eslint . 2>&1
            elif [ -f "biome.json" ]; then
                npx biome check . 2>&1
            else
                echo "No JS/TS linter configured"
                return 0
            fi
            ;;
        go)
            if command -v golangci-lint &> /dev/null; then
                golangci-lint run 2>&1
            else
                go vet ./... 2>&1
            fi
            ;;
        rust)
            cargo clippy -- -D warnings 2>&1
            ;;
        java-maven)
            mvn checkstyle:check -q 2>&1 || echo "No checkstyle configured"
            ;;
        java-gradle)
            ./gradlew checkstyleMain 2>&1 || echo "No checkstyle configured"
            ;;
        ruby)
            if command -v rubocop &> /dev/null; then
                bundle exec rubocop 2>&1
            else
                echo "No Ruby linter found"
                return 0
            fi
            ;;
        dotnet)
            dotnet format --verify-no-changes 2>&1
            ;;
        php)
            if [ -f "phpcs.xml" ]; then
                ./vendor/bin/phpcs 2>&1
            else
                echo "No PHP linter configured"
                return 0
            fi
            ;;
        elixir)
            mix credo 2>&1 || echo "No credo configured"
            ;;
        *)
            if [ -f "Makefile" ] && grep -q "lint:" Makefile; then
                make lint 2>&1
            else
                echo "No linter detected for stack: $DETECTED_STACK"
                return 0
            fi
            ;;
    esac
}

run_lint
EXIT_CODE=$?

[ $EXIT_CODE -eq 0 ] && echo "=== LINT PASSED ===" || echo "=== LINT FAILED ==="
exit $EXIT_CODE
