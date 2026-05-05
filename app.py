import argparse
import html
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from urllib.parse import parse_qs

from cyberbullying_app.pipeline import CyberbullyingPipeline, PipelineConfigError


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DATASET = DATA_DIR / "dataset.csv"
DEFAULT_HURTLEX = DATA_DIR / "hurtlex_EN.tsv"
DEFAULT_TARGETS = DATA_DIR / "target_indicators.txt"


def env_or_default(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else default


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_setup_message(message: str) -> str:
    return (
        f"{message} Expected dataset file at {DEFAULT_DATASET}. "
        f"You can override it with DATASET_PATH."
    )


def load_styles() -> str:
    return (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")


def pattern_for_term(term: str) -> re.Pattern:
    if term == "@mention":
        return re.compile(r"@\w+")
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?i)(?<!\w){escaped}(?!\w)")


def build_highlight_spans(text: str, terms: Sequence[str], css_class: str, priority: int) -> List[Tuple[int, int, str, int]]:
    spans: List[Tuple[int, int, str, int]] = []
    for term in terms:
        for match in pattern_for_term(term).finditer(text):
            spans.append((match.start(), match.end(), css_class, priority))
    return spans


def render_highlighted_text(text: str, hurtlex_matches: Sequence[str], target_matches: Sequence[str]) -> str:
    if not text.strip():
        return "<span class=\"empty-text\">No text to highlight yet.</span>"

    spans = build_highlight_spans(text, hurtlex_matches, "hl-offensive", 0)
    spans.extend(build_highlight_spans(text, target_matches, "hl-target", 1))
    spans.sort(key=lambda item: (item[0], item[3], -(item[1] - item[0])))

    merged: List[Tuple[int, int, str]] = []
    last_end = -1
    for start, end, css_class, _priority in spans:
        if start < last_end:
            continue
        merged.append((start, end, css_class))
        last_end = end

    if not merged:
        return html.escape(text)

    parts: List[str] = []
    cursor = 0
    for start, end, css_class in merged:
        if start > cursor:
            parts.append(html.escape(text[cursor:start]))
        parts.append(f"<mark class=\"{css_class}\">{html.escape(text[start:end])}</mark>")
        cursor = end
    if cursor < len(text):
        parts.append(html.escape(text[cursor:]))
    return "".join(parts)


def render_match_list(items: Sequence[str]) -> str:
    if not items:
        return "None"
    return ", ".join(html.escape(item) for item in items)


def render_history(history: Sequence[Dict[str, object]]) -> str:
    if not history:
        return """
    <section class="panel-card">
        <div class="panel-title">Recent Predictions</div>
        <div class="empty-text">No predictions yet.</div>
    </section>
    """

    items = []
    for item in history:
        items.append(
            f"""
            <li class="history-item">
                <div class="history-result">{html.escape(str(item['result']))}</div>
                <div class="history-text">{html.escape(str(item['comment']))}</div>
                <div class="history-meta">Risk: {item['risk_score']:.2f}%</div>
            </li>
            """
        )
    return f"""
    <section class="panel-card">
        <div class="panel-title">Recent Predictions</div>
        <ul class="history-list">
            {''.join(items)}
        </ul>
    </section>
    """


def render_analytics(analytics: Dict[str, int]) -> str:
    total_tested = int(analytics.get("total_tested", 0))
    total_detected = int(analytics.get("total_detected", 0))
    safe_count = total_tested - total_detected
    return f"""
    <section class="panel-card analytics-card">
        <div class="panel-title">Simple Analytics</div>
        <div class="analytics-grid">
            <div class="analytics-item">
                <span class="analytics-label">Total Tested</span>
                <strong>{total_tested}</strong>
            </div>
            <div class="analytics-item">
                <span class="analytics-label">Total Detected</span>
                <strong>{total_detected}</strong>
            </div>
            <div class="analytics-item">
                <span class="analytics-label">Safe Content</span>
                <strong>{safe_count}</strong>
            </div>
        </div>
    </section>
    """


def render_page(
    prediction=None,
    comment_text: str = "",
    setup_message: str = "",
    history: Sequence[Dict[str, object]] = (),
    analytics: Dict[str, int] = None,
) -> str:
    styles = load_styles()
    analytics = analytics or {"total_tested": 0, "total_detected": 0}

    setup_block = ""
    if setup_message:
        setup_block = f"""
        <section class="alert-card">
            <div class="panel-title">Setup Required</div>
            <div class="alert-text">{html.escape(setup_message)}</div>
        </section>
        """

    if prediction:
        result_class = "danger" if prediction["label"] == 1 else "safe"
        highlighted_text = render_highlighted_text(
            str(prediction["comment"]),
            prediction["hurtlex_matches"],
            prediction["target_matches"],
        )
        warning_block = (
            f"""
            <section class="warning-card">
                <div class="panel-title">Warning Message</div>
                <div class="warning-text">{html.escape(prediction['warning_message'])}</div>
            </section>
            """
            if prediction["warning_message"]
            else ""
        )
    else:
        result_class = "idle"
        highlighted_text = "<span class=\"empty-text\">Submit a message to see highlighted words.</span>"
        warning_block = ""
        prediction = {
            "label": 0,
            "result_text": "Waiting for Analysis",
            "risk_score": 0.0,
            "risk_level": "Low",
            "confidence_score": 0.0,
            "hurtlex_matches": [],
            "target_matches": [],
            "rule_triggered": False,
            "safer_text": "",
        }

    history_block = render_history(history)
    analytics_block = render_analytics(analytics)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Intelligent Real-Time Cyberbullying Detection System</title>
    <style>{styles}</style>
</head>
<body>
    <main class="page-shell">
        <section class="hero-card">
            <p class="eyebrow">AI Content Safety</p>
            <h1>Intelligent Real-Time Cyberbullying Detection System</h1>
            <p class="hero-text">Detects cyberbullying in real-time using AI and text analysis.</p>
        </section>

        {setup_block}

        <section class="workspace-card">
            <form method="post" action="/predict" class="predict-form">
                <div class="section-heading">
                    <h2>Input Section</h2>
                    <p>Check your message before posting it.</p>
                </div>
                <label for="comment" class="input-label">Text input box</label>
                <textarea id="comment" name="comment" rows="6" placeholder="Type your message before posting...">{html.escape(comment_text)}</textarea>
                <div class="button-row">
                    <button type="submit" class="btn-primary">Detect</button>
                    <button type="button" class="btn-secondary" onclick="window.location='/'">Clear</button>
                </div>
            </form>

            <section class="result-card {result_class}">
                <div class="section-heading">
                    <h2>Detection Result</h2>
                    <p>Instant classification and explainable cues.</p>
                </div>
                <div class="result-banner">{html.escape(prediction['result_text'])}</div>
                <div class="metrics-grid">
                    <div class="metric-box">
                        <span class="metric-label">Risk Score</span>
                        <strong>{prediction['risk_score']:.2f}%</strong>
                    </div>
                    <div class="metric-box">
                        <span class="metric-label">Risk Level</span>
                        <strong>{html.escape(prediction['risk_level'])}</strong>
                    </div>
                    <div class="metric-box">
                        <span class="metric-label">Confidence Score</span>
                        <strong>{prediction['confidence_score']:.2f}</strong>
                    </div>
                </div>

                <div class="detail-grid">
                    <section class="panel-card">
                        <div class="panel-title">Explanation</div>
                        <div class="detail-row"><strong>HurtLex word detected:</strong> {render_match_list(prediction['hurtlex_matches'])}</div>
                        <div class="detail-row"><strong>Target indicator detected:</strong> {render_match_list(prediction['target_matches'])}</div>
                        <div class="detail-row"><strong>Rule triggered:</strong> {"Yes" if prediction['rule_triggered'] else "No"}</div>
                    </section>

                    <section class="panel-card">
                        <div class="panel-title">Suggested Safer Text</div>
                        <div class="safer-text">{html.escape(prediction['safer_text'] or 'No suggestion yet.')}</div>
                    </section>
                </div>

                {warning_block}

                <section class="panel-card">
                    <div class="panel-title">Highlighted Text</div>
                    <div class="highlighted-text">{highlighted_text}</div>
                    <div class="highlight-legend">
                        <span class="legend-pill offensive">Offensive word</span>
                        <span class="legend-pill target">Target word</span>
                    </div>
                </section>
            </section>

            {analytics_block}
            {history_block}
        </section>
    </main>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    pipeline: CyberbullyingPipeline = None
    setup_message: str = ""
    history: List[Dict[str, object]] = []
    analytics: Dict[str, int] = {"total_tested": 0, "total_detected": 0}

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self._send_html("<h1>Not Found</h1>", HTTPStatus.NOT_FOUND)
            return
        self._send_html(
            render_page(
                setup_message=self.setup_message,
                history=self.history,
                analytics=self.analytics,
            )
        )

    def do_POST(self) -> None:
        if self.path != "/predict":
            self._send_html("<h1>Not Found</h1>", HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)
        comment = form.get("comment", [""])[0].strip()
        prediction = self.pipeline.predict(comment) if self.pipeline and comment else None

        if prediction and comment:
            self.analytics["total_tested"] += 1
            self.analytics["total_detected"] += int(prediction["label"])
            self.history.insert(
                0,
                {
                    "comment": comment,
                    "result": prediction["result_text"],
                    "risk_score": prediction["risk_score"],
                },
            )
            self.history = self.history[:5]

        self._send_html(
            render_page(
                prediction=prediction,
                comment_text=comment,
                setup_message=self.setup_message,
                history=self.history,
                analytics=self.analytics,
            )
        )

    def log_message(self, fmt, *args):
        return


def create_pipeline(dataset_path: Path, hurtlex_path: Path, target_path: Path) -> CyberbullyingPipeline:
    pipeline = CyberbullyingPipeline(dataset_path, hurtlex_path, target_path)
    pipeline.load()
    return pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Intelligent Real-Time Cyberbullying Detection System")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=env_int("PORT", 8080))
    parser.add_argument("--dataset", default=str(env_or_default("DATASET_PATH", DEFAULT_DATASET)))
    parser.add_argument("--hurtlex", default=str(env_or_default("HURTLEX_PATH", DEFAULT_HURTLEX)))
    parser.add_argument("--targets", default=str(env_or_default("TARGETS_PATH", DEFAULT_TARGETS)))
    parser.add_argument("--train-only", action="store_true")
    args = parser.parse_args()

    pipeline = None
    setup_message = ""
    try:
        pipeline = create_pipeline(Path(args.dataset), Path(args.hurtlex), Path(args.targets))
    except PipelineConfigError as exc:
        setup_message = build_setup_message(str(exc))

    if args.train_only:
        if pipeline is None:
            raise SystemExit(setup_message)
        print(pipeline.summary_text())
        return

    AppHandler.pipeline = pipeline
    AppHandler.setup_message = setup_message
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    print(f"Intelligent Real-Time Cyberbullying Detection System running at http://{display_host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
