# GST reconciliation engine
Owner: Person 3 (branch `gst-engine`). Build deterministic, testable matching and exception classification here. Suggested public interface: `reconcile(purchase_rows, gstr2b_rows) -> list[dict]`. Do not put LLM calls in tax calculations.
