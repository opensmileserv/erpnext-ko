import http.client
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast
from urllib.parse import urlsplit

TIMEOUT_SECONDS = 600
HTTP_OK = 200


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Provider:
    base_url: str
    model: str
    api_key: str | None = None
    extra: Mapping[str, object] = field(default_factory=dict[str, object])
    temperature: float = 0.7
    top_p: float = 0.8

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Provider:
        base_url = env.get("KOTR_BASE_URL", "").rstrip("/")
        model = env.get("KOTR_MODEL", "")
        if not base_url or not model:
            message = (
                "KOTR_BASE_URL 과 KOTR_MODEL 을 정한다. "
                "OpenAI 호환 엔드포인트면 된다 (예: http://host:8001/v1, Qwen/Qwen3.8-27B)."
            )
            raise ProviderError(message)
        extra_text = env.get("KOTR_EXTRA_JSON", "")
        extra = cast("dict[str, object]", json.loads(extra_text)) if extra_text else {}
        return cls(base_url, model, env.get("KOTR_API_KEY") or None, extra)


@dataclass(frozen=True, slots=True)
class Reply:
    content: object
    prompt_tokens: int
    completion_tokens: int


def connect(base_url: str) -> tuple[http.client.HTTPConnection, str]:
    parts = urlsplit(base_url)
    if parts.scheme == "https":
        return http.client.HTTPSConnection(parts.netloc, timeout=TIMEOUT_SECONDS), parts.path
    if parts.scheme == "http":
        return http.client.HTTPConnection(parts.netloc, timeout=TIMEOUT_SECONDS), parts.path
    message = f"KOTR_BASE_URL 은 http 나 https 주소여야 한다: {base_url!r}"
    raise ProviderError(message)


def post_json(provider: Provider, path: str, body: Mapping[str, object]) -> dict[str, object]:
    headers = {"Content-Type": "application/json"}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    connection, prefix = connect(provider.base_url)
    try:
        connection.request("POST", prefix + path, json.dumps(body).encode(), headers)
        response = connection.getresponse()
        raw = response.read()
    finally:
        connection.close()
    if response.status != HTTP_OK:
        message = f"모델 서버가 {response.status} 로 답했다: {raw[:300]!r}"
        raise ProviderError(message)
    return cast("dict[str, object]", json.loads(raw))


def count(usage: Mapping[str, object], name: str) -> int:
    value = usage.get(name)
    return value if isinstance(value, int) else 0


def complete(provider: Provider, system: str, user: str, schema: Mapping[str, object]) -> Reply:
    body: dict[str, object] = {
        "model": provider.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": provider.temperature,
        "top_p": provider.top_p,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "translations", "strict": True, "schema": schema},
        },
        **provider.extra,
    }
    payload = post_json(provider, "/chat/completions", body)
    choices = cast("list[dict[str, object]]", payload.get("choices") or [])
    if not choices:
        message = f"응답에 choices 가 없다: {str(payload)[:300]}"
        raise ProviderError(message)
    message_body = cast("dict[str, object]", choices[0].get("message") or {})
    content = message_body.get("content")
    if not isinstance(content, str):
        message = "응답 본문이 비었다"
        raise ProviderError(message)
    usage = cast("dict[str, object]", payload.get("usage") or {})
    return Reply(
        content=cast("object", json.loads(content)),
        prompt_tokens=count(usage, "prompt_tokens"),
        completion_tokens=count(usage, "completion_tokens"),
    )
