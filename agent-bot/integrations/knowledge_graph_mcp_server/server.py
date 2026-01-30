from mcp import FastMCP
import structlog

logger = structlog.get_logger()

mcp = FastMCP("Knowledge Graph")


@mcp.tool
async def get_function_callers(
    function_name: str, file_path: str | None = None
) -> list[dict[str, str | int]]:
    logger.info("get_function_callers", function=function_name, file=file_path)

    return [
        {
            "caller_name": "example_caller",
            "caller_file": "example/file.py",
            "caller_line": 42,
        }
    ]


@mcp.tool
async def get_class_hierarchy(class_name: str) -> dict[str, str | list[str]]:
    logger.info("get_class_hierarchy", class_name=class_name)

    return {
        "class": class_name,
        "parents": [],
        "children": [],
        "methods": [],
    }


@mcp.tool
async def get_file_dependencies(
    file_path: str,
) -> dict[str, str | list[dict[str, str]]]:
    logger.info("get_file_dependencies", file=file_path)

    return {
        "file": file_path,
        "imports": [],
    }


@mcp.tool
async def find_affected_by_change(file_path: str) -> list[str]:
    logger.info("find_affected_by_change", file=file_path)

    return []


@mcp.tool
async def get_test_coverage(
    function_name: str,
) -> dict[str, str | int | list[dict[str, str]]]:
    logger.info("get_test_coverage", function=function_name)

    return {
        "function": function_name,
        "coverage": 0,
        "tests": [],
    }


@mcp.tool
async def search_by_pattern(
    pattern: str, entity_type: str
) -> list[dict[str, str]]:
    logger.info("search_by_pattern", pattern=pattern, type=entity_type)

    return []


if __name__ == "__main__":
    mcp.run()
