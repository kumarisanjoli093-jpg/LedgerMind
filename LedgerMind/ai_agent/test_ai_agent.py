
import pytest

from ai_agent.schemas import AskRequest, InvoiceExtraction
from ai_agent.agent import LedgerMindAgent


class FakeRAG:

    def retrieve_context(self, query, top_k=5, vendor=None):
        return "Invoice INV-101 from ABC Traders. GST amount: 1800."


def test_ask_request_validation():
    request = AskRequest(
        question="Show my invoice history",
        vendor="ABC Traders",
        top_k=5,
    )

    assert request.question == "Show my invoice history"
    assert request.top_k == 5


def test_invoice_extraction_defaults():
    invoice = InvoiceExtraction()

    assert invoice.document_type == "unknown"
    assert invoice.currency == "INR"
    assert invoice.line_items == []


def test_rag_history_retrieval():
    agent = LedgerMindAgent(rag=FakeRAG())

    result = agent.search_history(
        question="Show invoice history",
        vendor="ABC Traders",
    )

    assert result["success"] is True
    assert "INV-101" in result["context"]


def test_direct_answer_tool():
    result = LedgerMindAgent.answer_directly(
        "What is GST?"
    )

    assert result["success"] is True
    assert result["tool"] == "answer_directly"


def test_invalid_question():
    agent = LedgerMindAgent(rag=FakeRAG())

    with pytest.raises(ValueError):
        agent.run("Hi")

