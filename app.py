from flask import Flask, jsonify, request, render_template
from pathlib import Path
import html as html_lib
import os
import re
from cyberbullying_app.pipeline import CyberbullyingPipeline

app = Flask(__name__)

MAX_TEXT_LENGTH = 1000

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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid request body. Expected a JSON object with a "text" field.'}), 400

    raw_text = data.get('text', '')
    if not isinstance(raw_text, str):
        return jsonify({'error': 'Invalid input: "text" must be a string.'}), 400

    text = raw_text.strip()
    if not text:
        return jsonify({'error': 'No text provided.'}), 400

    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({'error': f'Text exceeds maximum length of {MAX_TEXT_LENGTH} characters.'}), 400

    try:
        result = pipeline.analyze_text(text)
    except Exception:
        app.logger.exception('Text analysis failed')
        return jsonify({'error': 'An internal error occurred while analyzing the text. Please try again.'}), 500

    is_cyberbullying = bool(result['label'])
    probability = float(result['probability'])
    offensive_words = result['hurtlex_matches']
    target_indicators = result['target_matches']
    risk_score_percent = int(result['risk_score'])

    off_str = ", ".join(offensive_words) if offensive_words else "none"
    tgt_str = ", ".join(target_indicators) if target_indicators else "none"

    # HurtLex terms and target indicators are supporting, informational
    # signals only - the predicted class always comes from the Logistic
    # Regression probability above, never from these matches.
    if offensive_words or target_indicators:
        rule_note = f'Supporting rule-based indicators - HurtLex terms: {off_str}; target indicators: {tgt_str}.'
    else:
        rule_note = 'No supporting HurtLex or target indicators were matched for this prediction.'

    if is_cyberbullying:
        explanation = (
            f'Logistic Regression estimates {risk_score_percent}% probability of cyberbullying. {rule_note}'
        )
    else:
        explanation = (
            f'Logistic Regression estimates {risk_score_percent}% probability of cyberbullying, '
            f'below the 50% prediction threshold. {rule_note}'
        )

    return jsonify({
        'detection_result': result['result_text'],
        'is_cyberbullying': is_cyberbullying,
        'risk_score_percent': risk_score_percent,
        'risk_score': round(probability, 4),
        'risk_level': result['risk_level'],
        'confidence_score': result['confidence_score'],
        'offensive_words': offensive_words,
        'target_indicators': target_indicators,
        'rule_triggered': result['rule_triggered'],
        'threshold_note': result['threshold_note'],
        'warning': result['warning_message'],
        'model_disclaimer': result['model_disclaimer'],
        'explanation': explanation,
        'highlighted_text': build_highlighted_html(text, offensive_words, target_indicators),
        'safer_text': result['safer_text'],
    })


@app.errorhandler(404)
def handle_not_found(_error):
    return jsonify({'error': 'Not found.'}), 404


@app.errorhandler(500)
def handle_server_error(_error):
    return jsonify({'error': 'Internal server error. Please try again later.'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
