"""LangChain client factories for Azure OpenAI.

Provides `get_chat_llm()` and `get_embeddings()` — the single seam between the
RAG pipeline and the underlying model provider. Demo mode kicks in automatically
when Azure credentials are absent, returning deterministic fake clients so the
API stays usable end-to-end without keys.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

AZURE_API_VERSION = "2024-10-21"
DEFAULT_TEMPERATURE = 0.6


def get_chat_llm(
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = 1024,
    response_format: dict | None = None,
) -> BaseChatModel:
    """Returns a LangChain chat model bound to AZURE_CHAT_DEPLOYMENT.

    When Azure creds are missing, returns a deterministic FakeListChatModel
    so the graph can still execute in tests and demo mode.
    """
    settings = get_settings()
    if not settings.ai_configured:
        log.warning("chat_llm.demo_mode")
        return FakeListChatModel(
            responses=[
                "I'd love to help. Here are a few items that match a clean, modern aesthetic."
                "\n\nPRODUCTS_JSON: []",
            ]
        )
    # GPT-5.x / o-series models reject `max_tokens` — they require `max_completion_tokens`
    # routed through model_kwargs. Passing it this way is backward-compatible with gpt-4x.
    model_kwargs: dict = {"max_completion_tokens": max_tokens}
    if response_format:
        model_kwargs["response_format"] = response_format
    return AzureChatOpenAI(
        azure_endpoint=settings.AZURE_AI_FOUNDRY_ENDPOINT,
        api_key=settings.AZURE_AI_FOUNDRY_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_deployment=settings.AZURE_CHAT_DEPLOYMENT,
        temperature=temperature,
        timeout=60,
        max_retries=2,
        model_kwargs=model_kwargs,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Returns a LangChain embeddings client bound to AZURE_EMBEDDING_DEPLOYMENT.

    In demo mode, returns a deterministic fake that produces EMBEDDING_DIM-sized
    vectors so pgvector queries still execute end-to-end (results are not useful,
    but the plumbing works).
    """
    settings = get_settings()
    if not settings.ai_configured:
        log.warning("embeddings.demo_mode")
        return _FakeEmbeddings()
    return AzureOpenAIEmbeddings(
        azure_endpoint=settings.AZURE_AI_FOUNDRY_ENDPOINT,
        api_key=settings.AZURE_AI_FOUNDRY_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_deployment=settings.AZURE_EMBEDDING_DEPLOYMENT,
        timeout=30,
        max_retries=2,
    )


class _FakeEmbeddings(Embeddings):
    """Deterministic fake embeddings for demo/test mode. Matches EMBEDDING_DIM."""

    def _vector_for(self, text: str) -> list[float]:
        from app.models.product import EMBEDDING_DIM

        seed = sum(ord(c) for c in text[:64]) or 1
        return [((seed * (i + 1)) % 1000) / 1000.0 - 0.5 for i in range(EMBEDDING_DIM)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector_for(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)
