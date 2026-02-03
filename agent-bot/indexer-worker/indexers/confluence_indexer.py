import hashlib
import re
import structlog
from atlassian import Confluence

from config import settings
from models import ConfluenceSourceConfig, DocumentChunk

logger = structlog.get_logger()


class ConfluenceIndexer:
    def __init__(self, org_id: str, config: ConfluenceSourceConfig):
        self.org_id = org_id
        self.config = config
        self.client = Confluence(
            url=settings.confluence_url,
            username=settings.confluence_email,
            password=settings.confluence_api_token,
        )

    async def fetch_pages(self) -> list[dict]:
        pages = []

        for space in self.config.spaces:
            try:
                space_pages = self._fetch_space_pages(space)
                pages.extend(space_pages)
            except Exception as e:
                logger.error("confluence_space_fetch_failed", space=space, error=str(e))

        logger.info("confluence_pages_fetched", count=len(pages), org_id=self.org_id)
        return pages

    def _fetch_space_pages(self, space_key: str) -> list[dict]:
        pages = []
        start = 0
        limit = 50

        while True:
            try:
                result = self.client.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    expand="body.storage,metadata.labels,version",
                )

                if not result:
                    break

                for page in result:
                    if self._should_include_page(page):
                        pages.append(page)

                if len(result) < limit:
                    break

                start += limit

            except Exception as e:
                logger.error(
                    "confluence_page_fetch_failed", space=space_key, error=str(e)
                )
                break

        return pages

    def _should_include_page(self, page: dict) -> bool:
        labels = [
            label.get("name", "")
            for label in page.get("metadata", {}).get("labels", {}).get("results", [])
        ]

        if self.config.include_labels:
            if not any(label in self.config.include_labels for label in labels):
                return False

        if self.config.exclude_labels:
            if any(label in self.config.exclude_labels for label in labels):
                return False

        return True

    async def index_pages(self, pages: list[dict]) -> list[DocumentChunk]:
        chunks = []

        for page in pages:
            try:
                page_chunks = self._page_to_chunks(page)
                chunks.extend(page_chunks)
            except Exception as e:
                logger.warning(
                    "page_indexing_failed",
                    page=page.get("title", "unknown"),
                    error=str(e),
                )

        logger.info("confluence_pages_indexed", count=len(chunks), org_id=self.org_id)
        return chunks

    def _page_to_chunks(self, page: dict) -> list[DocumentChunk]:
        page_id = page.get("id", "")
        title = page.get("title", "")
        space_key = page.get("space", {}).get("key", "") if page.get("space") else ""

        body = page.get("body", {}).get("storage", {}).get("value", "")
        clean_content = self._clean_html(body)

        labels = [
            label.get("name", "")
            for label in page.get("metadata", {}).get("labels", {}).get("results", [])
        ]

        version = page.get("version", {}).get("number", 1)
        last_modified = page.get("version", {}).get("when", "")

        chunks = self._chunk_content(clean_content, title)
        result = []

        for i, chunk_content in enumerate(chunks):
            chunk_id = self._generate_chunk_id(page_id, i)

            result.append(
                DocumentChunk(
                    id=chunk_id,
                    content=chunk_content,
                    source_type="confluence",
                    source_id=f"{space_key}/{page_id}",
                    title=title,
                    metadata={
                        "page_id": page_id,
                        "page_title": title,
                        "space": space_key,
                        "labels": labels,
                        "version": version,
                        "last_modified": last_modified,
                        "chunk_index": i,
                        "org_id": self.org_id,
                    },
                )
            )

        return result

    def _clean_html(self, html_content: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _chunk_content(self, content: str, title: str) -> list[str]:
        chunks = []
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        content_with_title = f"# {title}\n\n{content}"

        if len(content_with_title) <= chunk_size:
            return [content_with_title]

        start = 0
        while start < len(content_with_title):
            end = start + chunk_size

            if end < len(content_with_title):
                break_point = content_with_title.rfind(". ", start, end)
                if break_point > start:
                    end = break_point + 1

            chunk = content_with_title[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def _generate_chunk_id(self, page_id: str, chunk_index: int) -> str:
        content = f"{self.org_id}:confluence:{page_id}:{chunk_index}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
