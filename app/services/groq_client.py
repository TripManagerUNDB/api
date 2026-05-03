import logging
from groq import Groq, RateLimitError, APIStatusError
from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_NARRATIVE_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
]


def _build_client() -> Groq:
    return Groq(api_key=settings.GROQ_API_KEY)


def chat_with_retry(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple[str, str]:
    """
    Tenta cada modelo em ordem. Avança para o próximo ao atingir rate-limit.
    Retorna (conteúdo, modelo_usado).
    """
    client = _build_client()
    last_error: Exception | None = None

    for model in GROQ_NARRATIVE_MODELS:
        try:
            logger.info("Tentando modelo: %s", model)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.info("Resposta obtida com o modelo: %s", model)
            return content, model

        except RateLimitError as exc:
            logger.warning("Rate-limit no modelo %s, tentando próximo. Detalhe: %s", model, exc)
            last_error = exc
            continue

        except APIStatusError as exc:
            # 429 também pode chegar como APIStatusError dependendo da versão do SDK
            if exc.status_code == 429:
                logger.warning("Status 429 no modelo %s, tentando próximo.", model)
                last_error = exc
                continue
            logger.error("Erro de API no modelo %s: %s", model, exc)
            raise

    raise RuntimeError(
        f"Todos os modelos atingiram o limite de uso. Último erro: {last_error}"
    )
