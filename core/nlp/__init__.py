"""
NLP v2 — Hybrid Custom + ML Pipeline

Modules:
- tokenizer.py       — Word/sentence splitting with token-value hooks
- classifier.py      — Rules fast-path + TF-IDF for ambiguous inputs
- cleaner.py         — Input normalization and sanitization
- patterns.py        — Intent + entity pattern banks
- embeddings.py      — Sentence embeddings (MiniLM via sentence-transformers)
- spell_check.py     — SymSpell + custom dictionary spelling correction
- entity_extractor.py — Slot-filling templates + regex entity extraction
- context_manager.py — Conversational context: sliding window + topic tracking
- summarizer.py      — Text summarization (kept from v1)
"""
