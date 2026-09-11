from collections.abc import Callable
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import BinaryIO
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from app.models.retrieved_document import RetrievedDocument


MEDLINEPLUS_ENDPOINT = "https://wsearch.nlm.nih.gov/ws/query"
MEDLINEPLUS_SOURCE_NAME = "MedlinePlus.gov — National Library of Medicine"
MEDLINEPLUS_SOURCE_TYPE = "Trusted external health-topic web service"


class ExternalRetrievalError(RuntimeError):
    """Raised when a trusted external retrieval cannot be completed safely."""


Transport = Callable[..., BinaryIO]


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _normalized_text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    parser = _PlainTextParser()
    parser.feed("".join(element.itertext()))
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def search_medlineplus(
    query: str,
    *,
    top_k: int = 2,
    timeout_seconds: float = 8.0,
    transport: Transport = urlopen,
) -> list[RetrievedDocument]:
    if not query.strip() or top_k < 1:
        return []

    parameters = urlencode(
        {
            "db": "healthTopics",
            "term": query.strip(),
            "retmax": top_k,
            "rettype": "brief",
            "tool": "agentic-healthcare-assistant",
        }
    )
    request = Request(
        f"{MEDLINEPLUS_ENDPOINT}?{parameters}",
        headers={"User-Agent": "AgenticHealthcareAssistant/1.0"},
    )

    try:
        with transport(request, timeout=timeout_seconds) as response:
            payload = response.read()
        root = ElementTree.fromstring(payload)
    except Exception as exc:
        raise ExternalRetrievalError(
            f"MedlinePlus retrieval failed: {type(exc).__name__}"
        ) from exc

    retrieved_at = datetime.now(timezone.utc).isoformat()
    results: list[RetrievedDocument] = []

    for document in root.findall("./list/document"):
        fields = {
            content.attrib.get("name", "").lower(): _normalized_text(content)
            for content in document.findall("content")
        }
        title = fields.get("title", "").strip()
        summary = (
            fields.get("fullsummary", "").strip()
            or fields.get("snippet", "").strip()
        )
        source_url = document.attrib.get("url", "").strip()

        if not title or not summary or not source_url.startswith("https://"):
            continue

        results.append(
            RetrievedDocument(
                id=f"medlineplus:{source_url}",
                title=title,
                source_name=MEDLINEPLUS_SOURCE_NAME,
                source_type=MEDLINEPLUS_SOURCE_TYPE,
                source_url=source_url,
                content=summary,
                distance=None,
                retrieved_at=retrieved_at,
            )
        )

    return results[:top_k]
