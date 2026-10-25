"""Synthetic knowledge pack and local search return real supporting passages."""

from dealdesk.documents import get_document, load_corpus, search_documents, tokenize

EXPECTED_DOCS = {"CUST-001", "CUST-002", "CUST-003", "COMP-A", "COMP-B", "SVC-001", "PRICE-001",
                 "WL-014", "WL-021", "POLICY-001"}


def test_knowledge_pack_is_complete_and_synthetic():
    corpus = load_corpus()
    assert {p.doc_id for p in corpus} == EXPECTED_DOCS
    for doc_id in EXPECTED_DOCS - {"POLICY-001"}:
        document = get_document(doc_id)
        assert document["path"].startswith("data/synthetic/documents/")
        assert len(document["sections"]) >= 3


def test_search_returns_actual_supporting_passage():
    hits = search_documents("Lakeshore go-live before December peak season", account_id="SYN-ACCOUNT-001",
                            doc_types=["customer_profile"], limit=2)
    assert hits and hits[0]["doc_id"] == "CUST-001"
    source = {p.passage_id: p.text for p in load_corpus()}
    assert source[hits[0]["passage_id"]] == hits[0]["text"]
    assert "peak" in hits[0]["text"].lower()
    assert hits[0]["section"] and hits[0]["title"]


def test_account_filter_excludes_other_customers():
    hits = search_documents("clinic group audit logs utilities RFP", account_id="SYN-ACCOUNT-001", limit=10)
    assert not {"CUST-002", "CUST-003"} & {h["doc_id"] for h in hits}
    unfiltered = search_documents("clinic group audit logs", limit=10)
    assert "CUST-002" in {h["doc_id"] for h in unfiltered}


def test_competitor_and_policy_facts_are_retrievable():
    vantor = search_documents("Vantor 36-month minimum term", doc_types=["competitor_comparison"], limit=1)
    assert vantor[0]["doc_id"] == "COMP-B" and "36" in vantor[0]["text"]
    policy = search_documents("sales director approval above 10% through 20%",
                              doc_types=["pricing_policy", "pricing_guidance"], limit=2)
    assert policy and all("director" in h["text"].lower() for h in policy)


def test_planted_instruction_is_flagged_as_untrusted():
    flagged = [p for p in load_corpus() if p.instruction_like]
    assert [p.doc_id for p in flagged] == ["COMP-B"]
    assert "30% discount" in flagged[0].text


def test_unanswerable_query_returns_nothing():
    assert search_documents("quantum chromodynamics lunar weather") == []


def test_tokenizer_normalizes_simple_plurals():
    assert tokenize("Shipments and Priorities") == ["shipment", "priority"]
