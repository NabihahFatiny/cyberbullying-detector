import os, re, threading
from flask import Flask, render_template, request, jsonify
from cyberbullying_app.pipeline import CyberbullyingPipeline, soften_text

app = Flask(__name__)

# ── Pipeline initialisation (lazy — loads on first request) ──────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))

_pipeline = CyberbullyingPipeline(
    dataset_path=os.path.join(_BASE, 'data', 'dataset.csv'),
    hurtlex_path=os.path.join(_BASE, 'data', 'hurtlex_EN.tsv'),
    target_path=os.path.join(_BASE, 'data', 'target_indicators.txt'),
)
_pipeline_lock = threading.Lock()
_pipeline_ready = False


def _ensure_pipeline():
    global _pipeline_ready
    if _pipeline_ready:
        return
    with _pipeline_lock:
        if _pipeline_ready:
            return
        try:
            _pipeline.load()
            print("Pipeline loaded successfully.")
        except Exception as e:
            print(f"WARNING: Pipeline load error: {e}")
        _pipeline_ready = True


# Start loading in background so port binds immediately and pipeline
# is ready before the first user request arrives.
threading.Thread(target=_ensure_pipeline, daemon=True).start()

# ── Highlighting helper ───────────────────────────────────────────────────────
_MENTION_RE = re.compile(r'@\w+')


def _highlight(original, offensive, targets):
    s = original

    s = _MENTION_RE.sub(
        lambda m: f'<mark class="target-mark">{m.group()}</mark>', s)

    for phrase in sorted(targets, key=len, reverse=True):
        if ' ' in phrase:
            s = re.sub(r'\b' + re.escape(phrase) + r'\b',
                       f'<mark class="target-mark">{phrase}</mark>', s,
                       flags=re.IGNORECASE)

    for phrase in sorted(offensive, key=len, reverse=True):
        if ' ' in phrase:
            s = re.sub(r'\b' + re.escape(phrase) + r'\b',
                       f'<mark class="offensive-mark">{phrase}</mark>', s,
                       flags=re.IGNORECASE)

    for tgt in targets:
        if ' ' not in tgt and not tgt.startswith('@'):
            s = re.sub(r'\b' + re.escape(tgt) + r'\b',
                       r'<mark class="target-mark">\g<0></mark>', s,
                       flags=re.IGNORECASE)

    for w in offensive:
        if ' ' not in w:
            s = re.sub(r'\b' + re.escape(w) + r'\b',
                       r'<mark class="offensive-mark">\g<0></mark>', s,
                       flags=re.IGNORECASE)

    return s


# ── Core analysis ─────────────────────────────────────────────────────────────
def analyze(text: str) -> dict:
    text = text.strip()
    if not text:
        return {'error': 'Empty input.'}

    _ensure_pipeline()
    result    = _pipeline.analyze_text(text)
    offensive = result['hurtlex_matches']
    targets   = result['target_matches']
    prob      = result['probability']
    risk_level = result['risk_level']
    risk_pct   = int(round(prob * 100))

    rule_triggered   = bool(offensive and targets)
    # ML probability is the primary signal; avoids HurtLex lemmatizer false positives
    is_cyberbullying = prob >= 0.5

    if is_cyberbullying:
        highlighted = _highlight(text, offensive, targets)
        safer       = soften_text(text, offensive)
        warning     = 'This message may be harmful. Please revise before posting.'
        if offensive and targets:
            explanation = (f'Offensive word(s) detected: {", ".join(offensive)}. '
                           f'Target indicator(s) found: {", ".join(targets)}.')
        else:
            explanation = f'Offensive word(s) detected: {", ".join(offensive)}.'
    else:
        highlighted = text
        safer       = ''
        warning     = ''
        if targets:
            explanation = 'A person was addressed, but no offensive language was found.'
        else:
            explanation = 'No offensive language or direct targeting detected.'

    return {
        'detection_result':   'Cyberbullying Detected' if is_cyberbullying else 'Safe Content',
        'is_cyberbullying':   is_cyberbullying,
        'risk_score_percent': risk_pct,
        'risk_score':         round(prob, 4),
        'risk_level':         risk_level,
        'confidence_score':   round(prob, 4),
        'offensive_words':    offensive,
        'target_indicators':  targets,
        'rule_triggered':     rule_triggered,
        'warning':            warning,
        'explanation':        explanation,
        'highlighted_text':   highlighted,
        'safer_text':         safer,
    }


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def api_analyze():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided.'}), 400
    return jsonify(analyze(text))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    try:
        from waitress import serve
        print(f"Starting waitress on port {port}")
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=False)
