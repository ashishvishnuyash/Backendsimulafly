"""Thin wrapper over Azure's image endpoints.

Uses the Azure-native path: `{endpoint}/openai/deployments/{deployment}/images/{op}`
with the `api-key` header (not Bearer). Model name lives in the URL path —
NOT in the request body.

Important: the OpenAI-compat path `{endpoint}/openai/v1/images/...` does NOT
expose the edits endpoint on this Azure resource (returns "model doesn't exist"
or "DeploymentNotFound"). The Azure-native path is the only one that works for
gpt-image-1.5 edits.

LangChain handles chat / embeddings / vision — only image gen + edit live here.
"""

from __future__ import annotations

import base64

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

IMAGE_API_VERSION = "2025-04-01-preview"

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9+3PqpkAAAAASUVORK5CYII="
)


def _deployment_url(endpoint: str, deployment: str, op: str) -> str:
    base = endpoint.rstrip("/")
    if base.endswith("/openai/v1"):
        base = base[: -len("/openai/v1")]
    return f"{base}/openai/deployments/{deployment}/images/{op}?api-version={IMAGE_API_VERSION}"


class AzureImageClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.ai_configured

    async def image_edit(
        self,
        room_bytes: bytes,
        product_bytes: bytes | None,  # noqa: ARG002 — reserved for future multi-image support
        prompt: str,
        *,
        size: str = "1024x1024",
        fallback_prompt: str | None = None,
    ) -> bytes:
        """Primary compositing path — Azure /images/edits on gpt-image-1.5 deployment.

        Falls back to text-to-image generation on any 4xx (lets the API stay usable
        even if the deployment doesn't expose edits).

        We enforce n=1 throughout to prevent the API from returning multiple data
        items and to avoid unexpected duplicate renders on the client.
        """
        deployment = self.settings.AZURE_IMAGE_EDIT_DEPLOYMENT
        gen_prompt = fallback_prompt or prompt
        if not deployment or not self.enabled:
            log.warning(
                "image_edit.unavailable",
                has_deployment=bool(deployment),
                ai_enabled=self.enabled,
            )
            return await self.image_gen(gen_prompt, size=size)

        url = _deployment_url(self.settings.AZURE_AI_FOUNDRY_ENDPOINT, deployment, "edits")
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            ("image", ("room.png", room_bytes, "image/png")),
        ]
        data = {
            "prompt": prompt[:4000],
            "size": size,
            "n": "1",  # always exactly one output image
        }
        try:
            return await self._post_multipart(url, files=files, data=data)
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                log.warning(
                    "image_edit.fallback_to_gen",
                    status=e.response.status_code,
                    body=e.response.text[:300],
                )
                return await self.image_gen(gen_prompt, size=size)
            raise

    async def image_gen(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        seed: int | None = 42,
    ) -> bytes:
        """Text-to-image via Azure /images/generations on the configured deployment.

        ``seed`` is passed to the API so repeated calls with the same prompt produce
        consistent (though not identical) outputs and avoid wildly different styles.
        Set seed=None to use a random seed.
        """
        deployment = self.settings.AZURE_IMAGE_GEN_DEPLOYMENT or self.settings.AZURE_IMAGE_EDIT_DEPLOYMENT
        if not deployment or not self.enabled:
            log.warning("image_gen.mock_mode")
            return _TINY_PNG

        url = _deployment_url(self.settings.AZURE_AI_FOUNDRY_ENDPOINT, deployment, "generations")
        headers = {
            "api-key": self.settings.AZURE_AI_FOUNDRY_API_KEY,
            "Content-Type": "application/json",
        }
        payload: dict = {
            "prompt": prompt[:4000],
            "size": size,
            "n": 1,  # always exactly one output image
        }
        if seed is not None:
            payload["seed"] = seed
        return await self._post_json(url, headers=headers, json=payload)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.TransportError),
    )
    async def _post_json(self, url: str, *, headers: dict, json: dict) -> bytes:
        async with httpx.AsyncClient(timeout=httpx.Timeout(400.0, connect=30.0)) as client:
            resp = await client.post(url, json=json, headers=headers)
            resp.raise_for_status()
            return _decode_image(resp.json())

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.TransportError),
    )
    async def _post_multipart(
        self,
        url: str,
        *,
        files: list[tuple[str, tuple[str, bytes, str]]],
        data: dict[str, str],
    ) -> bytes:
        headers = {"api-key": self.settings.AZURE_AI_FOUNDRY_API_KEY}
        async with httpx.AsyncClient(timeout=httpx.Timeout(400.0, connect=30.0)) as client:
            resp = await client.post(url, headers=headers, data=data, files=files)
            resp.raise_for_status()
            return _decode_image(resp.json())


def _decode_image(body: dict) -> bytes:
    if not body.get("data"):
        raise ValueError(f"image response missing data: {body}")
    item = body["data"][0]
    if "b64_json" in item and item["b64_json"]:
        return base64.b64decode(item["b64_json"])
    if "url" in item and item["url"]:
        with httpx.Client(timeout=60) as c:
            r = c.get(item["url"])
            r.raise_for_status()
            return r.content
    raise ValueError(f"image response has neither b64_json nor url: {item}")


_client: AzureImageClient | None = None


def get_image_client() -> AzureImageClient:
    global _client
    if _client is None:
        _client = AzureImageClient()
    return _client
