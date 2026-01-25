#!/bin/bash
# Stack Detection Script
# Detects project type and outputs stack identifier

detect_stack() {
    # Python
    if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
        echo "python"
        return
    fi

    # Node/TypeScript
    if [ -f "package.json" ]; then
        if [ -f "tsconfig.json" ]; then
            echo "typescript"
        else
            echo "node"
        fi
        return
    fi

    # Go
    if [ -f "go.mod" ]; then
        echo "go"
        return
    fi

    # Rust
    if [ -f "Cargo.toml" ]; then
        echo "rust"
        return
    fi

    # Java/Kotlin (Maven)
    if [ -f "pom.xml" ]; then
        echo "java-maven"
        return
    fi

    # Java/Kotlin (Gradle)
    if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
        echo "java-gradle"
        return
    fi

    # Ruby
    if [ -f "Gemfile" ]; then
        echo "ruby"
        return
    fi

    # .NET
    if ls *.csproj 1> /dev/null 2>&1 || ls *.fsproj 1> /dev/null 2>&1; then
        echo "dotnet"
        return
    fi

    # PHP
    if [ -f "composer.json" ]; then
        echo "php"
        return
    fi

    # Elixir
    if [ -f "mix.exs" ]; then
        echo "elixir"
        return
    fi

    # Unknown
    echo "unknown"
}

# Output detected stack
STACK=$(detect_stack)
echo "DETECTED_STACK=$STACK"
export DETECTED_STACK=$STACK
