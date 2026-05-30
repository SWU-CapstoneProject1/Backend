import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import torch
from torch.utils.data import DataLoader, Dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.analyze_pipeline import classify_clause_risk_by_rules


LABELS = ["LOW", "MEDIUM", "HIGH"]
LABEL_TO_ID = {label: idx for idx, label in enumerate(LABELS)}
ID_TO_LABEL = {idx: label for label, idx in LABEL_TO_ID.items()}

DEFAULT_BASE_MODEL = "snunlp/KR-ELECTRA-discriminator"
DEFAULT_DATASET_PATH = Path("data_collection/data/processed/koelectra_pseudo_labels.jsonl")
DEFAULT_OUTPUT_DIR = Path("models/koelectra-risk-pseudo")
DEFAULT_CORPUS_PATHS = [
    Path("data_collection/data/processed/rag_documents.jsonl"),
    Path("data_collection/data/processed/ftc_details.jsonl"),
    Path("data_collection/data/processed/ftc_summaries.jsonl"),
]


SEED_TEXTS = [
    "회사는 회원에게 발생한 손해에 대해 책임을 지지 않으며 어떠한 경우에도 환불하지 않습니다.",
    "회사는 사전 통지 없이 약관을 변경할 수 있고, 회원에게 발생한 손해를 배상하지 않습니다.",
    "회사는 임의로 서비스를 종료할 수 있으며 이미 납부한 이용료는 환불되지 않습니다.",
    "회사는 회원의 동의 없이 계약을 자동 갱신하고 위약금을 청구할 수 있습니다.",
    "회사는 일방적으로 이용 조건을 변경하고 계약을 즉시 해지할 수 있습니다.",
    "회사는 서비스 장애로 인한 손해에 대해 면책되며 환불은 불가합니다.",
    "회사는 사전 통지 없이 개인정보 처리방침과 이용약관을 변경할 수 있습니다.",
    "회원이 해지를 요청하더라도 회사는 위약금을 부과하고 환불을 제한할 수 있습니다.",
    "회사는 일방적으로 요금을 변경할 수 있으며 회원이 입은 손해에 대해 책임을 지지 않습니다.",
    "회사는 사전 통지 없이 서비스를 중단할 수 있고 남은 이용료는 환불되지 않습니다.",
    "회사는 회원의 귀책 여부와 관계없이 계약을 즉시 해지하고 위약금을 청구할 수 있습니다.",
    "회사는 약관을 임의로 변경할 수 있으며 변경으로 인한 손해배상 책임을 부담하지 않습니다.",
    "회사는 어떠한 경우에도 손해를 배상하지 않고 이용자가 납부한 금액은 환불하지 않습니다.",
    "회원은 자동 갱신된 계약을 해지할 수 없으며 중도 해지 시 과도한 위약금을 부담합니다.",
    "회사는 사전 통지 없이 계정을 정지할 수 있고 이로 인한 손해에 대해서는 면책됩니다.",
    "회사는 일방적으로 계약 내용을 변경하고 회원에게 발생한 손해를 배상하지 않습니다.",
    "회사는 이용자의 동의 없이 유료 서비스를 자동 갱신하고 환불을 제한할 수 있습니다.",
    "회사는 약관 변경을 사후에 통지할 수 있으며 변경으로 인한 모든 책임을 지지 않습니다.",
    "회사는 책임을 지지 않으며 환불 불가 정책을 적용합니다.",
    "회사는 사전 통지 없이 약관을 변경할 수 있고 회원에게 위약금을 부과합니다.",
    "회사는 임의로 계약 조건을 변경하고 유료 서비스는 자동 갱신됩니다.",
    "회사는 회원 자격을 즉시 해지할 수 있으며 결제 금액은 환불되지 않습니다.",
    "회사는 손해배상 예정 금액을 청구할 수 있고 그 외 책임을 지지 않습니다.",
    "회사는 서비스를 일방적으로 변경하고 필요하면 계약을 해지할 수 있습니다.",
    "회사는 면책되며 회원과의 계약을 종료할 수 있습니다.",
    "서비스는 자동 갱신되며 어떠한 경우에도 환불은 제한됩니다.",
    "회사는 사전 통지 없이 요금을 변경하고 손해배상 예정액을 청구할 수 있습니다.",
    "회사는 책임을 지지 않으며 회원 계정을 즉시 해지할 수 있습니다.",
    "회사는 환불 불가 조항을 적용하고 약관을 임의로 변경할 수 있습니다.",
    "회사는 면책 조항에 따라 손해를 배상하지 않으며 위약금을 부과합니다.",
    "회사는 사전 통지 후 약관을 변경할 수 있습니다.",
    "회원이 약관을 위반하는 경우 회사는 계약을 해지할 수 있습니다.",
    "유료 서비스는 결제 후 환불되지 않을 수 있습니다.",
    "본 계약은 별도 의사표시가 없으면 자동 갱신됩니다.",
    "회원은 중도 해지 시 위약금을 부담할 수 있습니다.",
    "회사는 관계 법령이 정한 범위에서 책임을 제한할 수 있습니다.",
    "회원은 언제든지 서비스 이용을 중단하고 탈퇴를 신청할 수 있습니다.",
    "회사는 약관 변경 시 시행일 7일 전부터 공지합니다.",
    "환불은 관련 법령과 회사의 환불 정책에 따라 처리됩니다.",
    "서비스 이용 시간과 이용 방법은 화면에 안내된 절차에 따릅니다.",
    "회원은 본인의 계정 정보를 정확하게 관리해야 합니다.",
    "회사는 안정적인 서비스 제공을 위해 정기 점검을 실시할 수 있습니다.",
    "개인정보는 서비스 제공 목적 범위에서 처리됩니다.",
    "분쟁이 발생한 경우 회사와 회원은 성실히 협의하여 해결합니다.",
]

RISK_PHRASE_GROUPS = {
    "liability": [
        "회사는 책임을 지지 않습니다",
        "회사는 손해를 배상하지 않습니다",
        "회사는 서비스 장애에 대해 면책됩니다",
    ],
    "change": [
        "회사는 사전 통지 없이 약관을 변경할 수 있습니다",
        "회사는 약관을 일방적으로 변경할 수 있습니다",
        "회사는 계약 조건을 임의로 변경할 수 있습니다",
    ],
    "termination": [
        "회사는 계약을 즉시 해지할 수 있습니다",
        "회사는 서비스 이용을 해지할 수 있습니다",
        "회사는 계약을 종료할 수 있습니다",
    ],
    "refund": [
        "결제 금액은 환불 불가입니다",
        "이용료는 환불되지 않습니다",
        "어떠한 경우에도 환불은 제한됩니다",
    ],
    "renewal": [
        "본 계약은 자동 갱신됩니다",
        "유료 서비스는 자동 갱신됩니다",
    ],
    "penalty": [
        "회원은 위약금을 부담해야 합니다",
        "회사는 손해배상 예정액을 청구할 수 있습니다",
    ],
}

LOW_RISK_SEED_TEXTS = [
    "회원은 언제든지 서비스 이용을 중단하고 탈퇴를 신청할 수 있습니다.",
    "회사는 약관 변경 시 시행일 7일 전부터 공지합니다.",
    "회사는 약관 변경 내용을 앱 화면과 이메일로 안내합니다.",
    "환불은 관련 법령과 회사의 환불 정책에 따라 처리됩니다.",
    "서비스 이용 시간과 이용 방법은 화면에 안내된 절차에 따릅니다.",
    "회원은 본인의 계정 정보를 정확하게 관리해야 합니다.",
    "회사는 안정적인 서비스 제공을 위해 정기 점검을 실시할 수 있습니다.",
    "개인정보는 서비스 제공 목적 범위에서 처리됩니다.",
    "분쟁이 발생한 경우 회사와 회원은 성실히 협의하여 해결합니다.",
    "회원은 고객센터를 통해 이용 내역과 결제 내역을 확인할 수 있습니다.",
    "회사는 이용자의 문의에 대해 합리적인 기간 안에 답변합니다.",
    "회원은 법령과 본 약관을 준수하여 서비스를 이용해야 합니다.",
]


def generate_rule_seed_texts() -> List[str]:
    generated = list(LOW_RISK_SEED_TEXTS)
    all_phrases = [phrase for phrases in RISK_PHRASE_GROUPS.values() for phrase in phrases]

    service_names = ["서비스", "앱", "웹사이트", "계정", "고객센터", "알림 기능"]
    low_actions = [
        "이용 방법은 화면에 표시된 절차에 따릅니다",
        "운영 정책은 공지사항을 통해 안내합니다",
        "문의 사항은 고객센터에서 접수합니다",
        "이용 내역은 마이페이지에서 확인할 수 있습니다",
        "개인정보는 수집 목적 범위 안에서 처리합니다",
        "정기 점검 일정은 사전에 안내합니다",
        "분쟁이 발생하면 성실히 협의하여 해결합니다",
        "회원은 등록 정보를 최신 상태로 유지해야 합니다",
    ]
    for service_name in service_names:
        for action in low_actions:
            generated.append(f"{service_name}의 {action}.")

    for phrase in all_phrases:
        generated.append(f"{phrase}. 다만 회사는 관련 법령에 따른 절차를 준수합니다.")

    groups = list(RISK_PHRASE_GROUPS.values())
    for idx, left_group in enumerate(groups):
        for right_group in groups[idx + 1:]:
            for left in left_group:
                for right in right_group:
                    generated.append(f"{left}. 또한 {right}.")

    return generated


def _extract_text_from_json_row(row: Dict) -> str:
    values = []
    for key in ("text", "content", "summary", "preview", "title"):
        value = row.get(key)
        if isinstance(value, str):
            values.append(value)
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        for key in ("summary", "preview", "title"):
            value = metadata.get(key)
            if isinstance(value, str):
                values.append(value)
    return "\n".join(values)


def _read_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def _split_candidates(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = re.split(r"(?<=[.!?다요음함])\s+|[\n\r]+", text)
    candidates = []
    buffer = ""
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(buffer) < 80:
            buffer = f"{buffer} {chunk}".strip()
            continue
        candidates.append(buffer)
        buffer = chunk
    if buffer:
        candidates.append(buffer)

    return [candidate[:600] for candidate in candidates if 20 <= len(candidate) <= 600]


def collect_candidate_texts(corpus_paths: List[Path], max_source_rows: int) -> List[str]:
    candidates = list(SEED_TEXTS) + generate_rule_seed_texts()

    for path in corpus_paths:
        if not path.exists():
            continue
        for idx, row in enumerate(_read_jsonl(path)):
            if idx >= max_source_rows:
                break
            candidates.extend(_split_candidates(_extract_text_from_json_row(row)))

    deduped = []
    seen = set()
    for text in candidates:
        key = re.sub(r"\s+", " ", text).strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def build_pseudo_dataset(
    corpus_paths: List[Path],
    *,
    max_source_rows: int,
    max_samples_per_label: int,
    seed: int,
) -> List[Dict[str, str]]:
    rng = random.Random(seed)
    candidates = collect_candidate_texts(corpus_paths, max_source_rows=max_source_rows)

    buckets: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for text in candidates:
        label = classify_clause_risk_by_rules(text)["risk_level"]
        buckets[label].append({"text": text, "label": label})

    dataset = []
    for label in LABELS:
        rows = buckets.get(label, [])
        rng.shuffle(rows)
        dataset.extend(rows[:max_samples_per_label])

    rng.shuffle(dataset)
    return dataset


def write_jsonl(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


class ClauseRiskDataset(Dataset):
    def __init__(self, rows: List[Dict[str, str]], tokenizer, max_length: int) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        row = self.rows[idx]
        encoded = self.tokenizer(
            row["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = torch.tensor(LABEL_TO_ID[row["label"]], dtype=torch.long)
        return item


def split_train_eval(rows: List[Dict[str, str]], eval_ratio: float, seed: int):
    rng = random.Random(seed)
    by_label: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)

    train_rows = []
    eval_rows = []
    for label_rows in by_label.values():
        rng.shuffle(label_rows)
        eval_count = max(1, int(len(label_rows) * eval_ratio)) if len(label_rows) > 1 else 0
        eval_rows.extend(label_rows[:eval_count])
        train_rows.extend(label_rows[eval_count:])

    rng.shuffle(train_rows)
    rng.shuffle(eval_rows)
    return train_rows, eval_rows


def evaluate(model, dataloader: DataLoader, device: torch.device) -> Dict[str, float]:
    model.eval()
    total = 0
    correct = 0
    loss_total = 0.0

    with torch.no_grad():
        for batch in dataloader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            loss_total += float(outputs.loss.item())
            predictions = outputs.logits.argmax(dim=-1)
            labels = batch["labels"]
            correct += int((predictions == labels).sum().item())
            total += int(labels.numel())

    model.train()
    return {
        "eval_loss": round(loss_total / max(len(dataloader), 1), 4),
        "eval_accuracy": round(correct / max(total, 1), 4),
    }


def train(args) -> None:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    rows = build_pseudo_dataset(
        [Path(path) for path in args.corpus_path],
        max_source_rows=args.max_source_rows,
        max_samples_per_label=args.max_samples_per_label,
        seed=args.seed,
    )
    if len(rows) < 6:
        raise RuntimeError("학습할 pseudo-label 데이터가 너무 적습니다.")

    write_jsonl(rows, Path(args.dataset_path))

    train_rows, eval_rows = split_train_eval(rows, args.eval_ratio, args.seed)
    label_counts = Counter(row["label"] for row in rows)
    print(f"pseudo dataset: {len(rows)} rows {dict(label_counts)}")
    print(f"train/eval split: {len(train_rows)}/{len(eval_rows)}")

    local_files_only = not args.allow_download
    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        local_files_only=local_files_only,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=len(LABELS),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
        local_files_only=local_files_only,
        ignore_mismatched_sizes=True,
    )

    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model.to(device)

    train_dataset = ClauseRiskDataset(train_rows, tokenizer, args.max_length)
    eval_dataset = ClauseRiskDataset(eval_rows, tokenizer, args.max_length)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    eval_loader = DataLoader(eval_dataset, batch_size=args.batch_size)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    model.train()
    for epoch in range(args.epochs):
        running_loss = 0.0
        for step, batch in enumerate(train_loader, start=1):
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            running_loss += float(loss.item())

            if step % args.log_every == 0:
                avg_loss = running_loss / step
                print(f"epoch {epoch + 1}/{args.epochs} step {step}/{len(train_loader)} loss={avg_loss:.4f}")

        metrics = evaluate(model, eval_loader, device) if eval_rows else {}
        avg_loss = running_loss / max(len(train_loader), 1)
        print(f"epoch {epoch + 1} done train_loss={avg_loss:.4f} {metrics}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    metadata = {
        "base_model": args.base_model,
        "dataset_path": str(args.dataset_path),
        "dataset_size": len(rows),
        "label_counts": dict(label_counts),
        "labels": LABELS,
        "note": "Demo checkpoint trained from rule-based pseudo labels, not human-reviewed labels.",
    }
    (output_dir / "pseudo_training_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved model: {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Train KR-ELECTRA with rule-based pseudo labels.")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--corpus-path", action="append", default=[str(path) for path in DEFAULT_CORPUS_PATHS])
    parser.add_argument("--max-source-rows", type=int, default=500)
    parser.add_argument("--max-samples-per-label", type=int, default=80)
    parser.add_argument("--max-length", type=int, default=160)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--eval-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-every", type=int, default=5)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
