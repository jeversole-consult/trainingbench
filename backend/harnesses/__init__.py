"""TB-US-056: harness module namespace.

Each harness module exposes a top-level ``run(dataset_path, model_fn,
config) -> dict`` function that the harness runner invokes to measure
an agent's (prompt, RAG, adapter, LLM) stack against a dataset.
"""
