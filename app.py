import argparse
import html
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from cyberbullying_app.pipeline import CyberbullyingPipeline, PipelineConfigError


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DATASET = DATA_DIR / "dataset.xlsx"
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
        f"{message} "
        f"Expected files: dataset at {DEFAULT_DATASET} (optional), "
        f"HurtLex at {DEFAULT_HURTLEX}, and target indicators at {DEFAULT_TARGETS}. "
        f"You can override these with DATASET_PATH, HURTLEX_PATH, and TARGETS_PATH."
    )


def load_styles() -> str:
    return (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")


def render_page(prediction=None, comment_text="", setup_message="", pipeline_status=None) -> str:
    styles = load_styles()
    if prediction:
        state_class = "danger" if prediction["label"] == 1 else "safe"
        result_title = prediction["result_text"]
        confidence_text = f"Confidence: {prediction['confidence']}%"
        hurtlex_text = ", ".join(prediction["lexicon_matches"]) if prediction["lexicon_matches"] else "-"
        target_text = ", ".join(prediction["target_matches"]) if prediction["target_matches"] else "-"
    else:
        state_class = "idle"
        result_title = "No result yet"
        confidence_text = "Confidence: -"
        hurtlex_text = "-"
        target_text = "-"

    status_block = ""
    if pipeline_status:
        dataset_label = (
            f"Loaded from {pipeline_status['dataset_path']}"
            if pipeline_status.get("dataset_loaded")
            else "Not loaded. Predictions still work without it."
        )
        status_block = f"""
        <section class="status-card">
            <div class="status-title">Deployment Status</div>
            <div class="status-text"><strong>Dataset:</strong> {html.escape(dataset_label)}</div>
            <div class="status-text"><strong>HurtLex:</strong> {html.escape(pipeline_status['hurtlex_path'])}</div>
            <div class="status-text"><strong>Targets:</strong> {html.escape(pipeline_status['target_path'])}</div>
        </section>
        """

    setup_block = ""
    if setup_message:
        setup_block = f"""
        <section class="setup-card">
            <div class="setup-title">Setup Required</div>
            <div class="setup-text">{html.escape(setup_message)}</div>
        </section>
        """

    prediction_block = f"""
    <section class="result-card {state_class}">
        <div class="result-label">Prediction Result</div>
        <div class="result-main">{html.escape(result_title)}</div>
        <div class="result-sub">{html.escape(confidence_text)}</div>
        <div class="result-details">
            <div><strong>HurtLex word:</strong> {html.escape(hurtlex_text)}</div>
            <div><strong>Target indicator:</strong> {html.escape(target_text)}</div>
            <div><strong>Rule:</strong> Cyberbullying only if both are detected.</div>
        </div>
    </section>
    """

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
        <section class="app-card">
            <h1>Intelligent Real-Time Cyberbullying Detection System</h1>
            <section class="info-card">
                <div class="info-title">How This Detection Works</div>
                <div class="info-text">The system labels a tweet as cyberbullying only when both conditions are present in the same text:</div>
                <ol class="rule-list">
                    <li>A HurtLex offensive word is detected.</li>
                    <li>A target indicator is detected, such as <code>you</code>, <code>your</code>, <code>u</code>, or a mention like <code>@username</code>.</li>
                </ol>
                <div class="example-row">
                    <span class="example-chip">Cyberbullying: "you are stupid"</span>
                    <span class="example-chip">Not Cyberbullying: "stupid"</span>
                    <span class="example-chip">Not Cyberbullying: "you are kind"</span>
                </div>
            </section>
            {setup_block}
            {status_block}
            <form method="post" action="/predict" class="predict-form">
                <label for="comment" class="input-label">Enter Tweet Text</label>
                <textarea id="comment" name="comment" rows="6" placeholder="Example: You are so stupid and useless.">{html.escape(comment_text)}</textarea>
                <div class="button-row">
                    <button type="submit" class="btn-primary">Detect</button>
                    <button type="button" class="btn-secondary" onclick="window.location='/'">Clear</button>
                </div>
            </form>
            {prediction_block}
        </section>
    </main>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    pipeline: CyberbullyingPipeline = None
    setup_message: str = ""

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
        pipeline_status = self.pipeline.status if self.pipeline else None
        self._send_html(render_page(setup_message=self.setup_message, pipeline_status=pipeline_status))

    def do_POST(self) -> None:
        if self.path != "/predict":
            self._send_html("<h1>Not Found</h1>", HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)
        comment = form.get("comment", [""])[0].strip()
        prediction = self.pipeline.predict(comment) if self.pipeline and comment else None
        pipeline_status = self.pipeline.status if self.pipeline else None
        self._send_html(
            render_page(
                prediction=prediction,
                comment_text=comment,
                setup_message=self.setup_message,
                pipeline_status=pipeline_status,
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
