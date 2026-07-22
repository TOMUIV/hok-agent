"""Lazy BGE embedding manager for memory dedup and similarity checks."""
import time, numpy as np

_MODEL = None
_DB_CACHE = {}  # {(hero_ai, hero_bot, kind, text_idx) -> embedding}


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    from FlagEmbedding import FlagModel
    t0 = time.time()
    _MODEL = FlagModel('BAAI/bge-m3', use_fp16=True)
    print(f"[Embedding] model loaded in {time.time()-t0:.1f}s", flush=True)
    return _MODEL


def encode(texts):
    model = _load_model()
    emb = model.encode(texts) if isinstance(texts, list) else model.encode([texts])
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    emb = emb / norms
    return emb


def _item_text(item):
    if item.get("kind") == "episodic":
        return (item.get("context", "") + " " + item.get("lesson", "")).strip()
    return item.get("rule", "") or item.get("text", "")


def max_similarity(buffer_item, db_items):
    """Compute max cosine similarity between buffer_item and all db_items."""
    text = _item_text(buffer_item)
    if not text or not db_items:
        return 0.0
    db_texts = [_item_text(d) for d in db_items if _item_text(d)]
    if not db_texts:
        return 0.0
    all_texts = [text] + db_texts
    try:
        vecs = encode(all_texts)
        query = vecs[0]
        rest = vecs[1:]
        sims = rest @ query
        return float(sims.max())
    except Exception:
        return -1.0
