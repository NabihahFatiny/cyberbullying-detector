import csv
import json
import math
import random
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree


XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MODEL_VERSION = 1


class PipelineConfigError(RuntimeError):
    """Raised when deployment-time data files are missing or invalid."""


def normalize_lookup_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " @mention ", text)
    text = text.replace("#", " ")
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^a-z\s@']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_text(text: str) -> List[str]:
    normalized = normalize_lookup_text(text)
    if not normalized:
        return []
    return [token for token in normalized.split() if token]


def sigmoid(value: float) -> float:
    clipped = max(min(value, 35.0), -35.0)
    return 1.0 / (1.0 + math.exp(-clipped))


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, str]] = []
        for row in reader:
            normalized = {}
            for key, value in row.items():
                normalized[str(key or "").strip().lower()] = "" if value is None else str(value)
            if any(value.strip() for value in normalized.values()):
                rows.append(normalized)
        return rows


def col_letter_to_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    value = 0
    for char in letters:
        value = value * 26 + (ord(char.upper()) - 64)
    return value - 1


def _extract_xlsx_to_temp(path: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="cyberbullying-xlsx-"))
    command = r"""
param([string]$src, [string]$tempRoot)
$ErrorActionPreference = 'Stop'
$copy = Join-Path $tempRoot 'dataset.zip'
$unzipped = Join-Path $tempRoot 'unzipped'
New-Item -ItemType Directory -Path $unzipped | Out-Null
$in = [System.IO.File]::Open($src,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
$out = [System.IO.File]::Open($copy,[System.IO.FileMode]::Create,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
$in.CopyTo($out)
$out.Close()
$in.Close()
Expand-Archive -LiteralPath $copy -DestinationPath $unzipped -Force
Write-Output $unzipped
"""
    script_path = temp_root / "extract_xlsx.ps1"
    script_path.write_text(command, encoding="utf-8")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-File", str(script_path), str(path), str(temp_root)],
        capture_output=True,
        text=True,
        check=True,
    )
    extracted_path = result.stdout.strip().splitlines()[-1].strip()
    return Path(extracted_path)


def read_xlsx_rows(path: Path) -> List[Dict[str, str]]:
    extracted_dir = _extract_xlsx_to_temp(path)
    try:
        shared_path = extracted_dir / "xl" / "sharedStrings.xml"
        sheet_path = extracted_dir / "xl" / "worksheets" / "sheet1.xml"

        shared_strings = []
        if shared_path.exists():
            root = ElementTree.fromstring(shared_path.read_bytes())
            for item in root.findall("x:si", XLSX_NS):
                text_parts = [node.text or "" for node in item.findall(".//x:t", XLSX_NS)]
                shared_strings.append("".join(text_parts))

        sheet_root = ElementTree.fromstring(sheet_path.read_bytes())
        rows = []
        for row_node in sheet_root.findall(".//x:sheetData/x:row", XLSX_NS):
            values_by_index = {}
            for cell in row_node.findall("x:c", XLSX_NS):
                ref = cell.attrib.get("r", "")
                index = col_letter_to_index(ref)
                cell_type = cell.attrib.get("t")
                value_node = cell.find("x:v", XLSX_NS)
                inline_node = cell.find("x:is/x:t", XLSX_NS)
                value = ""
                if inline_node is not None and inline_node.text is not None:
                    value = inline_node.text
                elif value_node is not None and value_node.text is not None:
                    value = value_node.text
                    if cell_type == "s":
                        shared_index = int(value)
                        value = shared_strings[shared_index] if shared_index < len(shared_strings) else ""
                values_by_index[index] = value
            if values_by_index:
                width = max(values_by_index) + 1
                row_values = [values_by_index.get(i, "") for i in range(width)]
                rows.append(row_values)
    finally:
        shutil.rmtree(extracted_dir.parent, ignore_errors=True)

    if not rows:
        return []

    headers = [str(item).strip().lower() for item in rows[0]]
    data_rows = []
    for row_values in rows[1:]:
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = row_values[index] if index < len(row_values) else ""
        if any(str(value).strip() for value in record.values()):
            data_rows.append(record)
    return data_rows


def read_dataset_rows(path: Path) -> List[Dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_rows(path)
    if suffix == ".xlsx":
        return read_xlsx_rows(path)
    raise PipelineConfigError(
        f"Unsupported dataset format: {path}. Use a .csv or .xlsx dataset file."
    )


def detect_text_column(headers: Iterable[str]) -> Optional[str]:
    candidates = [
        "comment",
        "tweet_text",
        "tweet",
        "text",
        "content",
        "message",
        "post",
    ]
    header_set = list(headers)
    for candidate in candidates:
        if candidate in header_set:
            return candidate
    return None


def detect_label_column(headers: Iterable[str]) -> Optional[str]:
    candidates = [
        "label",
        "cyberbullying_type",
        "cyberbullying",
        "class",
        "category",
        "target",
        "is_cyberbullying",
    ]
    header_set = list(headers)
    for candidate in candidates:
        if candidate in header_set:
            return candidate
    return None


def normalize_binary_label(raw_value: object) -> Optional[int]:
    text = str(raw_value or "").strip().lower()
    if not text:
        return None

    negative_labels = {
        "0",
        "false",
        "no",
        "negative",
        "not_cyberbullying",
        "not cyberbullying",
        "non_cyberbullying",
        "non-cyberbullying",
        "none",
        "safe",
    }
    positive_labels = {
        "1",
        "true",
        "yes",
        "positive",
        "cyberbullying",
        "cyber_bullying",
        "bullying",
        "abusive",
    }

    if text in negative_labels:
        return 0
    if text in positive_labels:
        return 1

    try:
        numeric = float(text)
    except ValueError:
        numeric = None
    if numeric is not None:
        if numeric <= 0:
            return 0
        if numeric >= 1:
            return 1

    if "not" in text and "cyber" in text:
        return 0

    return 1


def prepare_labeled_rows(rows: Sequence[Dict[str, str]]) -> Tuple[List[Dict[str, object]], str, str]:
    if not rows:
        raise PipelineConfigError("The dataset is empty, so the TF-IDF model cannot be trained.")

    text_column = detect_text_column(rows[0].keys())
    label_column = detect_label_column(rows[0].keys())
    if not text_column or not label_column:
        raise PipelineConfigError(
            "The dataset must include a text column (for example comment or tweet_text) "
            "and a label column (for example label or cyberbullying_type)."
        )

    prepared: List[Dict[str, object]] = []
    for row in rows:
        text = str(row.get(text_column, "") or "").strip()
        label = normalize_binary_label(row.get(label_column, ""))
        if not text or label is None:
            continue
        prepared.append(
            {
                "comment": text,
                "label": label,
            }
        )

    if len(prepared) < 10:
        raise PipelineConfigError("The dataset does not contain enough labeled rows to train the model.")

    positives = sum(int(item["label"]) for item in prepared)
    negatives = len(prepared) - positives
    if positives == 0 or negatives == 0:
        raise PipelineConfigError("The dataset needs both cyberbullying and non-cyberbullying examples.")

    return prepared, text_column, label_column


class TfidfVectorizer:
    def __init__(self, max_features: int = 8000, min_df: int = 2):
        self.max_features = max_features
        self.min_df = min_df
        self.vocabulary: Dict[str, int] = {}
        self.idf: List[float] = []

    def fit(self, documents: Sequence[str]) -> None:
        document_frequency: Counter = Counter()
        term_frequency: Counter = Counter()
        total_documents = len(documents)

        for document in documents:
            tokens = tokenize_text(document)
            if not tokens:
                continue
            unique_tokens = set(tokens)
            document_frequency.update(unique_tokens)
            term_frequency.update(tokens)

        items = [
            (term, df, term_frequency[term])
            for term, df in document_frequency.items()
            if df >= self.min_df
        ]
        items.sort(key=lambda item: (-item[1], -item[2], item[0]))
        if self.max_features > 0:
            items = items[: self.max_features]

        self.vocabulary = {term: index for index, (term, _, _) in enumerate(items)}
        self.idf = [0.0] * len(self.vocabulary)
        for term, index in self.vocabulary.items():
            df = document_frequency[term]
            self.idf[index] = math.log((1.0 + total_documents) / (1.0 + df)) + 1.0

    def transform_one(self, document: str) -> Dict[int, float]:
        counts: Dict[int, int] = {}
        for token in tokenize_text(document):
            index = self.vocabulary.get(token)
            if index is None:
                continue
            counts[index] = counts.get(index, 0) + 1

        if not counts:
            return {}

        vector: Dict[int, float] = {}
        norm = 0.0
        for index, count in counts.items():
            value = (1.0 + math.log(count)) * self.idf[index]
            vector[index] = value
            norm += value * value

        if norm > 0.0:
            scale = math.sqrt(norm)
            for index in list(vector):
                vector[index] = vector[index] / scale

        return vector

    def transform(self, documents: Sequence[str]) -> List[Dict[int, float]]:
        return [self.transform_one(document) for document in documents]

    def to_dict(self) -> Dict[str, object]:
        return {
            "max_features": self.max_features,
            "min_df": self.min_df,
            "vocabulary": self.vocabulary,
            "idf": self.idf,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "TfidfVectorizer":
        instance = cls(
            max_features=int(payload.get("max_features", 8000)),
            min_df=int(payload.get("min_df", 2)),
        )
        instance.vocabulary = {
            str(term): int(index)
            for term, index in dict(payload.get("vocabulary", {})).items()
        }
        instance.idf = [float(value) for value in list(payload.get("idf", []))]
        return instance


class LogisticRegressionClassifier:
    def __init__(
        self,
        epochs: int = 6,
        learning_rate: float = 0.35,
        l2_penalty: float = 0.0005,
        seed: int = 42,
    ):
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.l2_penalty = l2_penalty
        self.seed = seed
        self.weights: List[float] = []
        self.bias: float = 0.0

    def fit(self, vectors: Sequence[Dict[int, float]], labels: Sequence[int], feature_count: int) -> None:
        self.weights = [0.0] * feature_count
        self.bias = 0.0
        indices = list(range(len(vectors)))

        for epoch in range(self.epochs):
            learning_rate = self.learning_rate / (1.0 + (epoch * 0.35))
            random.Random(self.seed + epoch).shuffle(indices)
            for row_index in indices:
                vector = vectors[row_index]
                label = labels[row_index]
                probability = self.predict_probability(vector)
                error = probability - label
                self.bias -= learning_rate * error
                for feature_index, value in vector.items():
                    gradient = (error * value) + (self.l2_penalty * self.weights[feature_index])
                    self.weights[feature_index] -= learning_rate * gradient

    def predict_probability(self, vector: Dict[int, float]) -> float:
        score = self.bias
        for feature_index, value in vector.items():
            score += self.weights[feature_index] * value
        return sigmoid(score)

    def to_dict(self) -> Dict[str, object]:
        return {
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "l2_penalty": self.l2_penalty,
            "seed": self.seed,
            "weights": self.weights,
            "bias": self.bias,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "LogisticRegressionClassifier":
        instance = cls(
            epochs=int(payload.get("epochs", 6)),
            learning_rate=float(payload.get("learning_rate", 0.35)),
            l2_penalty=float(payload.get("l2_penalty", 0.0005)),
            seed=int(payload.get("seed", 42)),
        )
        instance.weights = [float(value) for value in list(payload.get("weights", []))]
        instance.bias = float(payload.get("bias", 0.0))
        return instance


def split_dataset(rows: Sequence[Dict[str, object]], test_ratio: float = 0.2, seed: int = 42) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    test_size = max(1, int(len(rows) * test_ratio))
    test_indices = set(indices[:test_size])

    train_rows = [rows[index] for index in indices if index not in test_indices]
    test_rows = [rows[index] for index in indices if index in test_indices]
    return train_rows, test_rows


def evaluate_predictions(labels: Sequence[int], probabilities: Sequence[float]) -> Dict[str, float]:
    if not labels:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    correct = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0

    for label, probability in zip(labels, probabilities):
        prediction = 1 if probability >= 0.5 else 0
        if prediction == label:
            correct += 1
        if prediction == 1 and label == 1:
            true_positive += 1
        elif prediction == 1 and label == 0:
            false_positive += 1
        elif prediction == 0 and label == 1:
            false_negative += 1

    accuracy = correct / len(labels)
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


class CyberbullyingPipeline:
    def __init__(self, dataset_path: Path, hurtlex_path: Path, target_path: Path):
        self.dataset_path = Path(dataset_path)
        self.hurtlex_path = Path(hurtlex_path)
        self.target_path = Path(target_path)
        self.model_cache_path = self.dataset_path.parent / "tfidf_logreg_model.json"
        self.vectorizer = TfidfVectorizer()
        self.classifier = LogisticRegressionClassifier()
        self.records: List[Dict[str, object]] = []
        self.status: Dict[str, object] = {}
        self.trained = False

    def _validate_required_file(self, path: Path, label: str) -> None:
        if path.exists() and path.is_file():
            return
        raise PipelineConfigError(
            f"Missing required {label} file: {path}. "
            f"Add the file to the repo or set the matching environment variable."
        )

    def _dataset_signature(self) -> Dict[str, object]:
        stat = self.dataset_path.stat()
        return {
            "path": str(self.dataset_path.resolve()),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }

    def _load_cache(self) -> bool:
        if not self.model_cache_path.exists():
            return False

        try:
            payload = json.loads(self.model_cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        signature = payload.get("dataset_signature", {})
        current_signature = self._dataset_signature() if self.dataset_path.exists() else None
        if payload.get("model_version") != MODEL_VERSION or signature != current_signature:
            return False

        self.vectorizer = TfidfVectorizer.from_dict(dict(payload.get("vectorizer", {})))
        self.classifier = LogisticRegressionClassifier.from_dict(dict(payload.get("classifier", {})))
        self.records = list(payload.get("records_preview", []))
        self.status = dict(payload.get("status", {}))
        self.status["model_cached"] = True
        self.trained = True
        return True

    def _save_cache(self) -> None:
        payload = {
            "model_version": MODEL_VERSION,
            "dataset_signature": self._dataset_signature(),
            "vectorizer": self.vectorizer.to_dict(),
            "classifier": self.classifier.to_dict(),
            "records_preview": self.records[:200],
            "status": self.status,
        }
        self.model_cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def _train_model(self) -> None:
        self._validate_required_file(self.dataset_path, "dataset")
        rows = read_dataset_rows(self.dataset_path)
        prepared, text_column, label_column = prepare_labeled_rows(rows)
        train_rows, test_rows = split_dataset(prepared)

        train_texts = [str(row["comment"]) for row in train_rows]
        train_labels = [int(row["label"]) for row in train_rows]
        test_texts = [str(row["comment"]) for row in test_rows]
        test_labels = [int(row["label"]) for row in test_rows]

        self.vectorizer.fit(train_texts)
        train_vectors = self.vectorizer.transform(train_texts)
        test_vectors = self.vectorizer.transform(test_texts)
        self.classifier.fit(train_vectors, train_labels, len(self.vectorizer.vocabulary))

        train_probabilities = [self.classifier.predict_probability(vector) for vector in train_vectors]
        test_probabilities = [self.classifier.predict_probability(vector) for vector in test_vectors]
        train_metrics = evaluate_predictions(train_labels, train_probabilities)
        test_metrics = evaluate_predictions(test_labels, test_probabilities)

        positive_rows = sum(int(row["label"]) for row in prepared)
        negative_rows = len(prepared) - positive_rows

        self.records = prepared[:500]
        self.status = {
            "dataset_rows": len(prepared),
            "cyberbullying_count": positive_rows,
            "non_cyberbullying_count": negative_rows,
            "dataset_loaded": True,
            "dataset_path": str(self.dataset_path),
            "model_cache_path": str(self.model_cache_path),
            "model_cached": False,
            "text_column": text_column,
            "label_column": label_column,
            "training_rows": len(train_rows),
            "test_rows": len(test_rows),
            "vocabulary_size": len(self.vectorizer.vocabulary),
            "training_accuracy": train_metrics["accuracy"],
            "test_accuracy": test_metrics["accuracy"],
            "precision": test_metrics["precision"],
            "recall": test_metrics["recall"],
            "f1_score": test_metrics["f1"],
            "model_name": "TF-IDF + Logistic Regression",
            "rule": "Tweets are vectorized with TF-IDF features and classified with a logistic regression model.",
        }
        self._save_cache()
        self.trained = True

    def load(self) -> None:
        if self.trained:
            return

        if self._load_cache():
            return

        self._train_model()

    def analyze_text(self, text: str) -> Dict[str, object]:
        self.load()
        normalized = normalize_lookup_text(text)
        vector = self.vectorizer.transform_one(text)
        probability = self.classifier.predict_probability(vector) if vector else 0.0
        is_cyberbullying = probability >= 0.5
        confidence = probability if is_cyberbullying else (1.0 - probability)

        top_tokens = []
        token_counts = Counter(tokenize_text(text))
        for token, _ in token_counts.most_common(8):
            if token in self.vectorizer.vocabulary:
                top_tokens.append(token)

        return {
            "comment": text,
            "normalized_text": normalized,
            "active_tokens": top_tokens,
            "label": 1 if is_cyberbullying else 0,
            "probability": probability,
            "confidence": round(confidence * 100, 2),
            "result_text": "Cyberbullying Detected" if is_cyberbullying else "Not Cyberbullying",
        }

    def predict(self, comment: str) -> Dict[str, object]:
        return self.analyze_text(comment)

    def summary_text(self) -> str:
        self.load()
        return "\n".join(
            [
                f"Model: {self.status['model_name']}",
                f"Rows: {self.status['dataset_rows']}",
                f"Cyberbullying: {self.status['cyberbullying_count']}",
                f"Non-Cyberbullying: {self.status['non_cyberbullying_count']}",
                f"Training rows: {self.status['training_rows']}",
                f"Test rows: {self.status['test_rows']}",
                f"Vocabulary size: {self.status['vocabulary_size']}",
                f"Training accuracy: {self.status['training_accuracy'] * 100:.2f}%",
                f"Test accuracy: {self.status['test_accuracy'] * 100:.2f}%",
                f"Precision: {self.status['precision'] * 100:.2f}%",
                f"Recall: {self.status['recall'] * 100:.2f}%",
                f"F1 score: {self.status['f1_score'] * 100:.2f}%",
                f"Dataset loaded: {'yes' if self.status['dataset_loaded'] else 'no'}",
                f"Rule: {self.status['rule']}",
            ]
        )
