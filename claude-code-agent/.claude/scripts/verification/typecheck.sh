#!/bin/bash
# Stack-Agnostic Type Check
# Exit 0 = PASS, Exit 1 = FAIL

SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/detect-stack.sh"

echo "=== Running Type Check (Stack: $DETECTED_STACK) ==="

run_typecheck() {
    case $DETECTED_STACK in
        python)
            if command -v mypy &> /dev/null; then
                # Find source directories
                if [ -d "src" ]; then
                    mypy src/ 2>&1
                elif [ -d "api" ]; then
                    mypy api/ core/ shared/ 2>&1 || mypy . 2>&1
                else
                    mypy . 2>&1
                fi
            elif command -v pyright &> /dev/null; then
                pyright 2>&1
            else
                echo "No Python type checker found"
                return 0
            fi
            ;;
        typescript)
            npx tsc --noEmit 2>&1
            ;;
        node)
            if [ -f "jsconfig.json" ]; then
                echo "JavaScript project - no strict type checking"
                return 0
            else
                echo "Node project - no type checking configured"
                return 0
            fi
            ;;
        go)
            # Go has implicit type checking via build
            go build ./... 2>&1
            ;;
        rust)
            # Rust has implicit type checking via build
            cargo check 2>&1
            ;;
        java-maven|java-gradle)
            # Java has implicit type checking via compile
            echo "Java has compile-time type checking"
            return 0
            ;;
        ruby)
            if [ -f "sorbet/config" ]; then
                bundle exec srb tc 2>&1
            else
                echo "Ruby - no Sorbet configured"
                return 0
            fi
            ;;
        dotnet)
            # .NET has implicit type checking
            dotnet build --no-restore 2>&1
            ;;
        php)
            if command -v phpstan &> /dev/null; then
                ./vendor/bin/phpstan analyse 2>&1
            else
                echo "No PHP type checker found"
                return 0
            fi
            ;;
        elixir)
            if [ -f "dialyzer.ignore-warnings" ] || grep -q "dialyxir" mix.exs; then
                mix dialyzer 2>&1
            else
                echo "Elixir - no dialyzer configured"
                return 0
            fi
            ;;
        *)
            echo "No type checker for stack: $DETECTED_STACK"
            return 0
            ;;
    esac
}

run_typecheck
EXIT_CODE=$?

[ $EXIT_CODE -eq 0 ] && echo "=== TYPECHECK PASSED ===" || echo "=== TYPECHECK FAILED ==="
exit $EXIT_CODE
