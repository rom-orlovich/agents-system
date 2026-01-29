from typing import Any, Tuple


class TextExtractor:

    @staticmethod
    def extract(
        value: Any,
        default: str = "",
        keys_to_try: Tuple[str, ...] = ("text", "body", "content"),
    ) -> str:
        if value is None:
            return default

        if isinstance(value, str):
            return value if value else default

        if isinstance(value, list):
            if not value:
                return default
            parts = []
            for item in value:
                if item is not None:
                    extracted = TextExtractor.extract(item, "")
                    if extracted:
                        parts.append(extracted)
            return " ".join(parts) if parts else default

        if isinstance(value, dict):
            for key in keys_to_try:
                if key in value:
                    return TextExtractor.extract(value[key], default, keys_to_try)
            if "content" in value and isinstance(value.get("content"), list):
                return TextExtractor.extract_jira_adf(value)

        return str(value) if value else default

    @staticmethod
    def extract_jira_adf(adf_content: Any) -> str:
        if adf_content is None:
            return ""

        if isinstance(adf_content, str):
            return adf_content

        if isinstance(adf_content, dict):
            if "text" in adf_content:
                return adf_content["text"]
            if "content" in adf_content:
                return TextExtractor.extract_jira_adf(adf_content["content"])
            return ""

        if isinstance(adf_content, list):
            texts = []
            for item in adf_content:
                extracted = TextExtractor.extract_jira_adf(item)
                if extracted:
                    texts.append(extracted)
            return " ".join(texts)

        return ""

    @staticmethod
    def safe_string(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if "content" in value:
                return TextExtractor.extract_jira_adf(value)
            if "text" in value:
                return str(value.get("text", default))
        return str(value) if value else default
