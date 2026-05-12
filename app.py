from flask import Flask, jsonify, request, render_template
from pathlib import Path
import html as html_lib
import os
import re
from cyberbullying_app.pipeline import CyberbullyingPipeline

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
pipeline = CyberbullyingPipeline(
    dataset_path=BASE_DIR / "data" / "dataset.csv",
    hurtlex_path=BASE_DIR / "data" / "hurtlex_EN.tsv",
    target_path=BASE_DIR / "data" / "target_indicators.txt",
)
pipeline.load()


def build_highlighted_html(text, offensive_words, target_words):
    if not text:
        return ""

    spans = []
    for word in offensive_words:
        for m in re.finditer(re.escape(word), text, re.IGNORECASE):
            spans.append((m.start(), m.end(), 'offensive'))
    for word in target_words:
        for m in re.finditer(re.escape(word), text, re.IGNORECASE):
            spans.append((m.start(), m.end(), 'target'))

    if not spans:
        return html_lib.escape(text)

    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))

    merged = []
    last_end = 0
    for start, end, typ in spans:
        if start >= last_end:
            merged.append((start, end, typ))
            last_end = end

    result = []
    pos = 0
    for start, end, typ in merged:
        if pos < start:
            result.append(html_lib.escape(text[pos:start]))
        css = 'offensive-mark' if typ == 'offensive' else 'target-mark'
        result.append(f'<mark class="{css}">{html_lib.escape(text[start:end])}</mark>')
        pos = end
    if pos < len(text):
        result.append(html_lib.escape(text[pos:]))

    return ''.join(result)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/test')
def test():
    return jsonify({"status": "working", "message": "API is functional"})


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'No text provided.'}), 400

    result = pipeline.analyze_text(text)

    is_cyberbullying = bool(result['label'])
    probability = float(result['probability'])
    offensive_words = result['hurtlex_matches']
    target_indicators = result['target_matches']

    off_str = ", ".join(offensive_words) if offensive_words else "—"
    tgt_str = ", ".join(target_indicators) if target_indicators else "—"

    if is_cyberbullying:
        explanation = f'Offensive word(s) detected: {off_str}. Target indicator(s) found: {tgt_str}.'
    else:
        explanation = 'No offensive language or direct targeting detected.'

    return jsonify({
        'detection_result': result['result_text'],
        'is_cyberbullying': is_cyberbullying,
        'risk_score_percent': int(result['risk_score']),
        'risk_score': round(probability, 4),
        'risk_level': result['risk_level'],
        'confidence_score': result['confidence_score'],
        'offensive_words': offensive_words,
        'target_indicators': target_indicators,
        'rule_triggered': result['rule_triggered'],
        'warning': result['warning_message'],
        'explanation': explanation,
        'highlighted_text': build_highlighted_html(text, offensive_words, target_indicators),
        'safer_text': result['safer_text'],
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
