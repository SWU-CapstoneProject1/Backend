import json
import os
import re
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
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FTCRetriever, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        if not INDEX_PATH.exists():
            raise FileNotFoundError(f"FAISS 인덱스가 없습니다: {INDEX_PATH}")
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"메타데이터가 없습니다: {METADATA_PATH}")
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"설정 파일이 없습니다: {CONFIG_PATH}")

        self.index = faiss.read_index(str(INDEX_PATH))
        self.metadata_rows: List[Dict[str, Any]] = load_json(METADATA_PATH)
        self.config = load_json(CONFIG_PATH)

        self.model_name = self.config["model_name"]
        self.model = None
        use_semantic = os.getenv("USE_SEMANTIC_RAG", "").lower() in {"1", "true", "yes"}
        allow_download = os.getenv("ALLOW_MODEL_DOWNLOAD", "").lower() in {"1", "true", "yes"}
        if use_semantic:
            try:
                self.model = SentenceTransformer(self.model_name, local_files_only=not allow_download)
            except Exception:
                self.model = None

        self.row_by_faiss_id: Dict[int, Dict[str, Any]] = {}
        for row in self.metadata_rows:
            self.row_by_faiss_id[int(row["faiss_id"])] = row

        self._initialized = True

    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        keywords = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", query))
        if not keywords:
            return []

        scored: List[Dict[str, Any]] = []
        for row in self.metadata_rows:
            haystack = " ".join([
                row.get("title", ""),
                row.get("preview", ""),
                row.get("text", ""),
                " ".join(row.get("metadata", {}).get("tags", [])),
            ])
            matched = sum(1 for keyword in keywords if keyword in haystack)
            if matched == 0:
                continue

            score = min(1.0, matched / max(len(keywords), 1))
            scored.append({
                "score": score,
                "id": row["id"],
                "title": row["title"],
                "preview": row.get("preview", ""),
                "metadata": row.get("metadata", {}),
                "text": row.get("text", ""),
            })

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        if self.model is None:
            return self._keyword_search(query, top_k)

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
