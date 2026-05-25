"""PII detection and anonymisation using Microsoft Presidio.

Activated via PII_DETECTION_ENABLED=true.
PII_ACTION=anonymize  →  replaces entities with <ENTITY_TYPE> placeholders
PII_ACTION=log        →  logs a warning but leaves text unchanged
PII_LANGUAGE          →  "en" (en_core_web_sm) or "fr" (fr_core_news_md)
"""
from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "DATE_TIME",
    "NRP",
    "MEDICAL_LICENSE",
    "URL",
]

_SPACY_MODELS: dict[str, str] = {
    "en": "en_core_web_sm",
    "fr": "fr_core_news_md",
}


@lru_cache(maxsize=4)
def _get_engines(language: str):
    """Lazily initialise Presidio engines (cached per language)."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    model_name = _SPACY_MODELS.get(language, "en_core_web_sm")
    logger.info("Initialising Presidio for language=%s model=%s", language, model_name)

    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": language, "model_name": model_name}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=[language],
    )
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def process_chunk(content: str, language: str, action: str) -> str:
    """Detect (and optionally anonymize) PII in a chunk of text.

    Returns the original or anonymized content.
    Never raises — failures are logged and the original chunk is returned.
    """
    try:
        analyzer, anonymizer = _get_engines(language)
        results = analyzer.analyze(text=content, entities=ENTITIES, language=language)

        if not results:
            return content

        entity_types = sorted({r.entity_type for r in results})

        if action == "anonymize":
            anonymized = anonymizer.anonymize(text=content, analyzer_results=results)
            logger.info(
                "PII anonymized — %d entit%s: %s",
                len(results),
                "y" if len(results) == 1 else "ies",
                entity_types,
            )
            return anonymized.text

        # action == "log": warn but preserve original
        logger.warning(
            "PII detected (not anonymized) — %d entit%s: %s",
            len(results),
            "y" if len(results) == 1 else "ies",
            entity_types,
        )
        return content

    except Exception:
        logger.exception("PII detection failed — chunk passed through unchanged")
        return content
