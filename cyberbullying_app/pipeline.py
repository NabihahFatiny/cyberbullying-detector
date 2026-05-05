import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Set
from xml.etree import ElementTree


XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


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


def build_phrase_index(phrases: Sequence[str]) -> Dict[int, Set[str]]:
    index: Dict[int, Set[str]] = defaultdict(set)
    for phrase in phrases:
        normalized = normalize_lookup_text(phrase)
        if not normalized or normalized == "nan":
            continue
        index[len(normalized.split())].add(normalized)
    return dict(index)

def find_phrase_matches(text: str, phrase_index: Dict[int, Set[str]]) -> List[str]:
    normalized = normalize_lookup_text(text)
    tokens = normalized.split()
    matches = set()

    if not tokens:
        return []

    for phrase_length, phrases in phrase_index.items():
        if phrase_length <= 0 or len(tokens) < phrase_length:
            continue
        for start in range(len(tokens) - phrase_length + 1):
            candidate = " ".join(tokens[start : start + phrase_length])
            if candidate in phrases:
                matches.add(candidate)

    return sorted(matches, key=lambda item: (len(item.split()), item))


def read_target_words(path: Path) -> Set[str]:
    words = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            normalized = normalize_lookup_text(line.strip())
            if normalized:
                words.add(normalized)
    return words


def read_hurtlex(path: Path) -> Set[str]:
    lexicon = set()
    with path.open("r", encoding="utf-8") as handle:
        header_line = handle.readline().rstrip("\n")
        headers = header_line.split("\t") if header_line else []
        lemma_index = 0
        for index, name in enumerate(headers):
            if name.strip().lower() == "lemma":
                lemma_index = index
                break

        for line in handle:
            cols = line.rstrip("\n").split("\t")
            if lemma_index < len(cols):
                normalized = normalize_lookup_text(cols[lemma_index].strip())
                if normalized:
                    lexicon.add(normalized)
    return lexicon


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


class CyberbullyingPipeline:
    def __init__(self, dataset_path: Path, hurtlex_path: Path, target_path: Path):
        self.dataset_path = Path(dataset_path)
        self.hurtlex_path = Path(hurtlex_path)
        self.target_path = Path(target_path)
        self.lexicon_words: Set[str] = set()
        self.target_words: Set[str] = set()
        self.lexicon_index: Dict[int, Set[str]] = {}
        self.target_index: Dict[int, Set[str]] = {}
        self.records: List[Dict[str, object]] = []
        self.status: Dict[str, object] = {}

    def _validate_required_file(self, path: Path, label: str) -> None:
        if path.exists() and path.is_file():
            return
        raise PipelineConfigError(
            f"Missing required {label} file: {path}. "
            f"Add the file to the repo or set the matching environment variable."
        )

    def _load_detection_resources(self) -> None:
        if self.lexicon_words and self.target_words:
            return

        self._validate_required_file(self.hurtlex_path, "HurtLex lexicon")
        self._validate_required_file(self.target_path, "target indicators")

        self.lexicon_words = read_hurtlex(self.hurtlex_path)
        self.target_words = read_target_words(self.target_path)
        self.lexicon_index = build_phrase_index(sorted(self.lexicon_words))
        self.target_index = build_phrase_index(sorted(self.target_words))

    def analyze_text(self, text: str) -> Dict[str, object]:
        self._load_detection_resources()
        normalized = normalize_lookup_text(text)
        lexicon_matches = find_phrase_matches(text, self.lexicon_index)
        target_matches = find_phrase_matches(text, self.target_index)
        is_cyberbullying = bool(lexicon_matches and target_matches)

        return {
            "comment": text,
            "normalized_text": normalized,
            "lexicon_matches": lexicon_matches,
            "target_matches": target_matches,
            "lexicon_hit": bool(lexicon_matches),
            "target_hit": bool(target_matches),
            "label": 1 if is_cyberbullying else 0,
            "confidence": 100 if is_cyberbullying else 0,
            "result_text": "Cyberbullying Detected" if is_cyberbullying else "Not Cyberbullying",
        }

    def load(self) -> None:
        self._load_detection_resources()

        rows: List[Dict[str, str]] = []
        dataset_loaded = self.dataset_path.exists() and self.dataset_path.is_file()
        if dataset_loaded:
            rows = read_xlsx_rows(self.dataset_path)

        prepared = []
        cyberbullying_count = 0

        for row in rows:
            comment = str(row.get("comment", "") or "").strip()
            if not comment:
                continue

            analysis = self.analyze_text(comment)
            prepared.append(
                {
                    "tweet_id": str(row.get("tweet_id", "") or ""),
                    "username": str(row.get("username", "") or ""),
                    "comment": comment,
                    "label": analysis["label"],
                }
            )
            cyberbullying_count += int(analysis["label"])

        self.records = prepared
        self.status = {
            "dataset_rows": len(prepared),
            "cyberbullying_count": cyberbullying_count,
            "non_cyberbullying_count": len(prepared) - cyberbullying_count,
            "hurtlex_entries": len(self.lexicon_words),
            "target_entries": len(self.target_words),
            "dataset_loaded": dataset_loaded,
            "dataset_path": str(self.dataset_path),
            "hurtlex_path": str(self.hurtlex_path),
            "target_path": str(self.target_path),
            "rule": "Cyberbullying is detected only when both a HurtLex word and a target indicator are found.",
        }

    def predict(self, comment: str) -> Dict[str, object]:
        return self.analyze_text(comment)

    def summary_text(self) -> str:
        if not self.records:
            self.load()
        return "\n".join(
            [
                f"Rows: {self.status['dataset_rows']}",
                f"Cyberbullying: {self.status['cyberbullying_count']}",
                f"Non-Cyberbullying: {self.status['non_cyberbullying_count']}",
                f"HurtLex entries: {self.status['hurtlex_entries']}",
                f"Target indicators: {self.status['target_entries']}",
                f"Dataset loaded: {'yes' if self.status['dataset_loaded'] else 'no'}",
                f"Rule: {self.status['rule']}",
            ]
        )
