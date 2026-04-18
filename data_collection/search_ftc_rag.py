import json
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


INDEX_DIR = Path("data_collection/data/index")
INDEX_PATH = INDEX_DIR / "ftc_faiss.index"
METADATA_PATH = INDEX_DIR / "ftc_faiss_metadata.json"
CONFIG_PATH = INDEX_DIR / "ftc_faiss_config.json"


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_l2(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return vectors / norms


class FTCRetriever:
    def __init__(self) -> None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                f"FAISS 인덱스가 없습니다: {INDEX_PATH}\n"
                "먼저 build_faiss_index.py를 실행하세요."
            )
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"메타데이터가 없습니다: {METADATA_PATH}")
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"설정 파일이 없습니다: {CONFIG_PATH}")

        self.index = faiss.read_index(str(INDEX_PATH))
        self.metadata_rows: List[Dict[str, Any]] = load_json(METADATA_PATH)
        self.config = load_json(CONFIG_PATH)

        self.model_name = self.config["model_name"]
        self.model = SentenceTransformer(self.model_name)

        self.row_by_faiss_id: Dict[int, Dict[str, Any]] = {}
        for row in self.metadata_rows:
            self.row_by_faiss_id[int(row["faiss_id"])] = row

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        query_embedding = np.asarray(query_embedding, dtype="float32")
        query_embedding = normalize_l2(query_embedding)

        scores, ids = self.index.search(query_embedding, top_k)

        results: List[Dict[str, Any]] = []
        for score, faiss_id in zip(scores[0], ids[0]):
            if int(faiss_id) == -1:
                continue

            row = self.row_by_faiss_id.get(int(faiss_id))
            if not row:
                continue

            results.append({
                "score": float(score),
                "id": row["id"],
                "title": row["title"],
                "preview": row.get("preview", ""),
                "metadata": row.get("metadata", {}),
                "text": row.get("text", ""),
            })

        return results


def pretty_print(results: List[Dict[str, Any]]) -> None:
    if not results:
        print("검색 결과가 없습니다.")
        return

    for i, r in enumerate(results, start=1):
        print("=" * 80)
        print(f"[{i}] score={r['score']:.4f}")
        print(f"id: {r['id']}")
        print(f"title: {r['title']}")
        print(f"decision_date: {r['metadata'].get('decision_date', '')}")
        print(f"case_number: {r['metadata'].get('case_number', '')}")
        print(f"tags: {', '.join(r['metadata'].get('tags', []))}")
        print("- preview -")
        print(r["preview"][:500])


if __name__ == "__main__":
    retriever = FTCRetriever()

    while True:
        query = input("\n검색할 약관 조항/문장을 입력하세요 (종료: exit): ").strip()
        if query.lower() in {"exit", "quit"}:
            break

        results = retriever.search(query, top_k=5)
        pretty_print(results)