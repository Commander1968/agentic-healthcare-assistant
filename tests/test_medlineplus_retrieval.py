from io import BytesIO
from urllib.error import URLError

import pytest

from app.agents import healthcare_graph
from app.models.medical_record import MedicalRecord
from app.models.workflow_state import WorkflowState
from app.retrieval.medlineplus import (
    ExternalRetrievalError,
    search_medlineplus,
)


XML_RESULT = b"""<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <list>
    <document rank="0" url="https://medlineplus.gov/chronickidneydisease.html">
      <content name="title">&lt;span class="qt0"&gt;Chronic&lt;/span&gt; &lt;span class="qt1"&gt;Kidney&lt;/span&gt; Disease</content>
      <content name="organizationName">National Library of Medicine</content>
      <content name="FullSummary">&lt;p&gt;Chronic &lt;span class="qt0"&gt;kidney&lt;/span&gt; disease affects kidney function.&lt;/p&gt;</content>
      <content name="snippet">Kidney disease information.</content>
    </document>
  </list>
</nlmSearchResult>"""


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_medlineplus_result_is_normalized_with_provenance_and_date():
    def transport(request, timeout):
        assert request.full_url.startswith("https://wsearch.nlm.nih.gov/ws/query?")
        assert timeout == 8.0
        return FakeResponse(XML_RESULT)

    results = search_medlineplus(
        "chronic kidney disease",
        transport=transport,
    )

    assert len(results) == 1
    assert results[0].title == "Chronic Kidney Disease"
    assert "<span" not in results[0].title
    assert "<p>" not in results[0].content
    assert results[0].source_name.startswith("MedlinePlus.gov")
    assert results[0].source_url == "https://medlineplus.gov/chronickidneydisease.html"
    assert results[0].retrieved_at is not None
    assert results[0].distance is None


def test_medlineplus_empty_query_makes_no_request():
    def transport(*args, **kwargs):
        raise AssertionError("Transport must not be called")

    assert search_medlineplus("  ", transport=transport) == []


def test_medlineplus_empty_results_are_returned_safely():
    def transport(*args, **kwargs):
        return FakeResponse(b"<nlmSearchResult><list /></nlmSearchResult>")

    assert search_medlineplus("unknown condition", transport=transport) == []


def test_medlineplus_network_failure_is_explicit():
    def transport(*args, **kwargs):
        raise URLError("offline")

    with pytest.raises(ExternalRetrievalError, match="URLError"):
        search_medlineplus("kidney disease", transport=transport)


def test_graph_uses_external_result_before_faiss_fallback(monkeypatch):
    document = search_medlineplus(
        "kidney disease",
        transport=lambda *args, **kwargs: FakeResponse(XML_RESULT),
    )[0]
    captured_query = {}

    def external_search(query, top_k):
        captured_query["query"] = query
        captured_query["top_k"] = top_k
        return [document]

    monkeypatch.setattr(healthcare_graph, "search_medlineplus", external_search)
    monkeypatch.setattr(
        healthcare_graph,
        "search_knowledge",
        lambda *args, **kwargs: pytest.fail("FAISS fallback should not run"),
    )
    state = WorkflowState(
        patient_id="P001",
        requested_specialty="Nephrology",
        reason="Chronic kidney disease treatment information",
        medical_record=MedicalRecord(
            record_id="R001",
            patient_id="P001",
            diagnoses=["Chronic Kidney Disease", "Hypertension"],
        ),
    )

    updated = healthcare_graph.retrieve_knowledge(state)

    assert updated.retrieved_documents == [document]
    assert updated.external_retrieval_error is None
    assert captured_query == {
        "query": "Chronic Kidney Disease",
        "top_k": 2,
    }


def test_graph_falls_back_to_faiss_after_external_failure(monkeypatch):
    monkeypatch.setattr(
        healthcare_graph,
        "search_medlineplus",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ExternalRetrievalError("MedlinePlus retrieval failed: timeout")
        ),
    )
    monkeypatch.setattr(
        healthcare_graph,
        "search_knowledge",
        lambda query, top_k: [
            {
                "id": "fallback",
                "title": "Fallback",
                "source_name": "Local",
                "source_type": "Synthetic",
                "source_url": None,
                "content": "Fallback educational content",
                "distance": 0.1,
            }
        ],
    )
    state = WorkflowState(patient_id="P001", reason="kidney disease")

    updated = healthcare_graph.retrieve_knowledge(state)

    assert updated.retrieved_documents[0].id == "fallback"
    assert "timeout" in updated.external_retrieval_error
