import json
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


INPUT_JSONL = Path("data_collection/data/processed/rag_documents.jsonl")
INDEX_DIR = Path("data_collection/data/index")
INDEX_PATH = INDEX_DIR / "ftc_faiss.index"
METADATA_PATH = INDEX_DIR / "ftc_faiss_metadata.json"
CONFIG_PATH = INDEX_DIR / "ftc_faiss_config.json"

# 한국어/다국어 대응이 무난한 범용 모델
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_l2(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return vectors / norms


def build_index() -> None:
    if not INPUT_JSONL.exists():
        raise FileNotFoundError(
            f"입력 파일이 없습니다: {INPUT_JSONL}\n"
            "먼저 preprocess_ftc_for_rag.py를 실행하세요."
        )

    docs = load_jsonl(INPUT_JSONL)
    if not docs:
        raise ValueError("rag_documents.jsonl이 비어 있습니다.")

    texts: List[str] = []
    metadata_rows: List[Dict[str, Any]] = []

    for i, doc in enumerate(docs):
        doc_id = str(doc.get("id", "")).strip()
        title = str(doc.get("title", "")).strip()
        text = str(doc.get("text", "")).strip()
        metadata = doc.get("metadata", {})

        if not doc_id or not text:
            continue

        texts.append(text)
        metadata_rows.append({
            "faiss_id": i,
            "id": doc_id,
            "title": title,
            "metadata": metadata,
            "preview": doc.get("preview", ""),
            "text": text,
        })

    if not texts:
        raise ValueError("임베딩할 유효 문서가 없습니다.")

    print(f"문서 수: {len(texts)}")
    print(f"모델 로드: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    # Sentence Transformers 공식 사용 패턴
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    embeddings = np.asarray(embeddings, dtype="float32")
    embeddings = normalize_l2(embeddings)

    dim = embeddings.shape[1]
    print(f"임베딩 shape: {embeddings.shape}")

    # cosine similarity처럼 쓰기 위해 정규화 후 Inner Product 사용
    base_index = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap(base_index)

    ids = np.arange(len(embeddings), dtype=np.int64)
    index.add_with_ids(embeddings, ids)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))

    save_json(METADATA_PATH, metadata_rows)
    save_json(CONFIG_PATH, {
        "model_name": MODEL_NAME,
        "dimension": dim,
        "document_count": len(metadata_rows),
        "index_type": "IndexIDMap(IndexFlatIP)",
        "normalized": True,
        "input_file": str(INPUT_JSONL),
    })

    print("인덱스 생성 완료")
    print(f"- index: {INDEX_PATH}")
    print(f"- metadata: {METADATA_PATH}")
    print(f"- config: {CONFIG_PATH}")


if __name__ == "__main__":
    build_index()