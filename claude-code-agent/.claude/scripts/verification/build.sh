#!/bin/bash
# Stack-Agnostic Build Check
# Exit 0 = PASS, Exit 1 = FAIL

SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/detect-stack.sh"

echo "=== Running Build Check (Stack: $DETECTED_STACK) ==="

run_build() {
    case $DETECTED_STACK in
        python)
            if command -v uv &> /dev/null; then
                uv build 2>&1
            elif [ -f "setup.py" ]; then
                python setup.py build 2>&1
            elif [ -f "pyproject.toml" ]; then
                pip install -e . 2>&1
            else
                echo "Python project - no build needed"
                return 0
            fi
            ;;
        typescript)
            npm run build 2>&1 || npx tsc 2>&1
            ;;
        node)
            if grep -q '"build"' package.json 2>/dev/null; then
                npm run build 2>&1
            else
                echo "Node project - no build script"
                return 0
            fi
            ;;
        go)
            go build ./... 2>&1
            ;;
        rust)
            cargo build 2>&1
            ;;
        java-maven)
            mvn compile -q 2>&1
            ;;
        java-gradle)
            ./gradlew build -x test 2>&1
            ;;
        ruby)
            echo "Ruby project - no build needed"
            return 0
            ;;
        dotnet)
            dotnet build 2>&1
            ;;
        php)
            if [ -f "composer.json" ]; then
                composer install --no-dev 2>&1
            else
                echo "PHP project - no build needed"
                return 0
            fi
            ;;
        elixir)
            mix compile 2>&1
            ;;
        *)
            if [ -f "Makefile" ]; then
                if grep -q "build:" Makefile; then
                    make build 2>&1
                elif grep -q "all:" Makefile; then
                    make all 2>&1
                else
                    echo "No build target in Makefile"
                    return 0
                fi
            else
                echo "No build system detected for stack: $DETECTED_STACK"
                return 0
            fi
            ;;
    esac
}

run_build
EXIT_CODE=$?

[ $EXIT_CODE -eq 0 ] && echo "=== BUILD PASSED ===" || echo "=== BUILD FAILED ==="
exit $EXIT_CODE
