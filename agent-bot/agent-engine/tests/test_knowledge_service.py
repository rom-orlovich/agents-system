import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.knowledge import (
    KnowledgeService,
    NoopKnowledgeService,
)


class TestKnowledgeServiceDisabled:
    @pytest.mark.asyncio
    async def test_search_returns_empty_when_disabled(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=False,
        )

        results = await service.search("test query", "org-1")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_related_code_returns_empty_when_disabled(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=False,
        )

        results = await service.get_related_code("test_func", "function", "org-1")

        assert results == {}

    @pytest.mark.asyncio
    async def test_health_check_shows_disabled(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=False,
        )

        status = await service.health_check()

        assert status.enabled is False
        assert status.llamaindex_available is False
        assert status.gkg_available is False


class TestKnowledgeServiceGracefulDegradation:
    @pytest.mark.asyncio
    async def test_search_returns_empty_on_timeout(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=True,
            timeout=0.001,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            import httpx

            mock_instance.post.side_effect = httpx.TimeoutException("timeout")

            results = await service.search("test query", "org-1")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_http_error(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=True,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            import httpx

            mock_instance.post.side_effect = httpx.HTTPError("connection failed")

            results = await service.search("test query", "org-1")

            assert results == []

    @pytest.mark.asyncio
    async def test_get_related_code_returns_empty_on_error(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=True,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            import httpx

            mock_instance.post.side_effect = httpx.HTTPError("connection failed")

            results = await service.get_related_code("test_func", "function", "org-1")

            assert results == {}


class TestKnowledgeServiceToggle:
    def test_enable_sets_enabled_flag(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=False,
        )

        service.enable()

        assert service._enabled is True
        assert service._status.enabled is True

    def test_disable_clears_enabled_flag(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=True,
        )

        service.disable()

        assert service._enabled is False
        assert service._status.enabled is False


class TestNoopKnowledgeService:
    @pytest.mark.asyncio
    async def test_search_always_returns_empty(self):
        service = NoopKnowledgeService()

        results = await service.search("test query", "org-1")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_related_code_always_returns_empty(self):
        service = NoopKnowledgeService()

        results = await service.get_related_code("test_func", "function", "org-1")

        assert results == {}

    @pytest.mark.asyncio
    async def test_health_check_shows_disabled(self):
        service = NoopKnowledgeService()

        status = await service.health_check()

        assert status.enabled is False

    def test_is_available_always_false(self):
        service = NoopKnowledgeService()

        assert service.is_available is False

    def test_enable_is_noop(self):
        service = NoopKnowledgeService()
        service.enable()

    def test_disable_is_noop(self):
        service = NoopKnowledgeService()
        service.disable()


class TestKnowledgeServiceSearch:
    @pytest.mark.asyncio
    async def test_search_parses_response_correctly(self):
        service = KnowledgeService(
            llamaindex_url="http://localhost:8100",
            gkg_url="http://localhost:4000",
            enabled=True,
        )

        mock_response = {
            "results": [
                {
                    "source_type": "code",
                    "source_id": "file.py",
                    "content": "def test(): pass",
                    "relevance_score": 0.95,
                    "metadata": {"language": "python"},
                }
            ]
        }

        with patch("services.knowledge.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_instance.post.return_value = mock_response_obj

            results = await service.search("test query", "org-1")

            assert len(results) == 1
            assert results[0].source_type == "code"
            assert results[0].source_id == "file.py"
            assert results[0].relevance_score == 0.95
            assert results[0].metadata == {"language": "python"}
