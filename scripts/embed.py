"""BGE-M3 文本嵌入 CLI

Usage:
  python scripts/embed.py "你的文本"
  python scripts/embed.py --file input.txt
  python scripts/embed.py --pair "查询" "段落"
  type input.txt | python scripts/embed.py

Output: JSON to stdout, logs to stderr
"""
import sys, json, argparse, time
sys.stdout.reconfigure(encoding='utf-8')

def load_model():
    from FlagEmbedding import FlagModel
    t0 = time.time()
    model = FlagModel('BAAI/bge-m3', use_fp16=True)
    print(f"model loaded in {time.time()-t0:.1f}s", file=sys.stderr)
    return model

MODEL = None
def get_model():
    global MODEL
    if MODEL is None:
        MODEL = load_model()
    return MODEL

def encode(texts, normalize=True):
    model = get_model()
    t0 = time.time()
    emb = model.encode(texts) if isinstance(texts, list) else model.encode([texts])
    if normalize:
        import numpy as np
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        emb = emb / norms
    print(f"encoded {len(texts)} texts in {time.time()-t0:.2f}s", file=sys.stderr)
    return emb

def main():
    parser = argparse.ArgumentParser(description="BGE-M3 文本嵌入")
    parser.add_argument("text", nargs="*", help="要编码的文本")
    parser.add_argument("--file", "-f", help="从文件读取（每行一条）")
    parser.add_argument("--pair", nargs=2, metavar=("QUERY", "PASSAGE"), help="计算一对文本的相似度")
    parser.add_argument("--ndjson", action="store_true", help="从 stdin 读取逐行 JSON（每行有 text 字段）")
    args = parser.parse_args()

    texts = None

    if args.pair:
        emb = encode(list(args.pair))
        import numpy as np
        sim = float((emb[0] @ emb[1]).item())
        print(json.dumps({"similarity": round(sim, 4)}, ensure_ascii=False))
        return

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            texts = [line.strip() for line in f if line.strip()]

    elif args.ndjson:
        texts = []
        for line in sys.stdin:
            line = line.strip()
            if line:
                texts.append(json.loads(line)["text"])

    elif args.text:
        texts = args.text

    elif not sys.stdin.isatty():
        texts = [line.strip() for line in sys.stdin if line.strip()]

    if not texts:
        print(json.dumps({"error": "no input text"}), ensure_ascii=False)
        sys.exit(1)

    emb = encode(texts)
    result = {
        "dim": emb.shape[1],
        "count": len(emb),
        "embeddings": [[round(float(v), 6) for v in row] for row in emb],
    }
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
