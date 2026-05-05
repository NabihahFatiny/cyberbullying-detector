import os, re, string
from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import joblib
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

app = Flask(__name__)

# ── NLTK bootstrap ──────────────────────────────────────────────────────────
def _ensure_nltk():
    needed = {
        'tokenizers/punkt': 'punkt',
        'tokenizers/punkt_tab': 'punkt_tab',
        'corpora/stopwords': 'stopwords',
        'corpora/wordnet': 'wordnet',
    }
    missing = []
    for path, pkg in needed.items():
        try:
            nltk.data.find(path)
        except (LookupError, OSError):
            missing.append(pkg)
    if missing:
        print(f"INFO: NLTK packages missing: {missing}. Downloading in background...")
        import threading
        def _dl():
            for pkg in missing:
                try:
                    nltk.download(pkg, quiet=True)
                except Exception as e:
                    print(f"WARNING: Could not download '{pkg}': {e}")
        threading.Thread(target=_dl, daemon=True).start()

_ensure_nltk()

# ── HurtLex quality filters ──────────────────────────────────────────────────
# Words that appear in HurtLex but are NOT offensive in everyday English
_HURTLEX_EXCLUSIONS = {
    'love', 'poor', 'kill', 'poor', 'pretentious', 'barbarian', 'die',
    'minister', 'accountant', 'diplomat', 'counselor', 'auditor',
}

# Categories in HurtLex that are too broad / produce false positives
_SKIP_CATEGORIES = {'pa'}  # professional activities — not offensive

# Common bullying/hate words missing from HurtLex — manually curated
_EXTRA_OFFENSIVE = {
    # direct hostility
    'hate', 'despise', 'detest', 'loathe',
    # body shaming
    'fat', 'ugly', 'hideous', 'disgusting', 'gross',
    # social rejection
    'loser', 'weirdo', 'freak', 'weirdo', 'outcast', 'loner',
    # intelligence attacks
    'brainless', 'clueless', 'dimwit', 'dunce', 'imbecile',
    # worthlessness
    'worthless', 'useless', 'pathetic', 'hopeless', 'failure',
    # violence/threat
    'kill', 'hurt', 'attack', 'destroy', 'ruin',
    # general insults often used in bullying
    'trash', 'garbage', 'pig', 'rat', 'snake',
}

# ── Globals ──────────────────────────────────────────────────────────────────
hurtlex_tokens  = set()   # single-word lemmas
hurtlex_phrases = []      # multi-word lemmas (sorted longest-first)
target_set      = set()   # single-word target indicators
target_phrases  = []      # multi-word target indicators
ml_model        = None
ml_vectorizer   = None
try:
    _lemmatizer = WordNetLemmatizer()
except Exception:
    _lemmatizer = None
try:
    _stop_words = set(stopwords.words('english'))
except Exception:
    _stop_words = set()

# ── Resource loading ─────────────────────────────────────────────────────────
def _find(filename, subdirs=('data',)):
    """Return the first existing path for filename, checking subdirs then root."""
    for sub in subdirs:
        p = os.path.join(sub, filename)
        if os.path.exists(p):
            return p
    if os.path.exists(filename):
        return filename
    return None


def _load_hurtlex():
    global hurtlex_tokens, hurtlex_phrases
    path = _find('hurtlex_EN.tsv')
    if not path:
        print("WARNING: hurtlex_EN.tsv not found. Using extra offensive list only.")
        hurtlex_tokens.update(_EXTRA_OFFENSIVE)
        return
    try:
        df = pd.read_csv(path, sep='\t', on_bad_lines='skip', encoding='utf-8')
        if 'lemma' not in df.columns:
            return
        # Skip non-offensive categories and apply exclusion list
        if 'category' in df.columns:
            df = df[~df['category'].isin(_SKIP_CATEGORIES)]
        for raw in df['lemma'].dropna().str.lower().str.strip():
            if raw in _HURTLEX_EXCLUSIONS:
                continue
            if ' ' in raw:
                hurtlex_phrases.append(raw)
            else:
                hurtlex_tokens.add(raw)
        # Merge supplementary offensive words
        hurtlex_tokens.update(_EXTRA_OFFENSIVE)
        hurtlex_phrases.sort(key=len, reverse=True)
        print(f"HurtLex loaded: {len(hurtlex_tokens)} tokens, {len(hurtlex_phrases)} phrases.")
    except Exception as e:
        print(f"WARNING: hurtlex load error: {e}")


def _load_targets():
    global target_set, target_phrases
    path = _find('target_indicators.txt')
    if not path:
        # Fallback minimal set
        target_set = {'you','your','yours','yourself','u','ur','ye','ya',
                      'bro','dude','man','buddy','pal','friend','kid','son',
                      'mate','homie','fam','sister','brother','girl','boy',
                      'lady','sir','mister','miss','yall','yous'}
        print("WARNING: target_indicators.txt not found – using built-in fallback.")
        return
    try:
        with open(path, encoding='utf-8') as f:
            items = [ln.strip().lower() for ln in f if ln.strip()]
        for item in items:
            if ' ' in item:
                target_phrases.append(item)
            else:
                target_set.add(item)
        target_phrases.sort(key=len, reverse=True)
        print(f"Target indicators loaded: {len(target_set)} tokens, {len(target_phrases)} phrases.")
    except Exception as e:
        print(f"WARNING: target load error: {e}")


def _load_model():
    global ml_model, ml_vectorizer
    mp = _find('logistic_model.pkl',  ('model',))
    vp = _find('tfidf_vectorizer.pkl', ('model',))
    if mp and vp:
        try:
            ml_model      = joblib.load(mp)
            ml_vectorizer = joblib.load(vp)
            print("ML model loaded successfully.")
        except Exception as e:
            print(f"WARNING: model load error: {e}")
    else:
        print("INFO: No saved model found – running in rule-only mode.")


_load_hurtlex()
_load_targets()
_load_model()

# ── Text preprocessing ───────────────────────────────────────────────────────
_URL_RE   = re.compile(r'https?://\S+|www\.\S+')
_HASH_RE  = re.compile(r'#\w+')
_EMOJI_RE = re.compile(
    "["
    u"\U0001F600-\U0001F64F"
    u"\U0001F300-\U0001F5FF"
    u"\U0001F680-\U0001F9FF"
    u"☀-➿"
    "]+", flags=re.UNICODE)
_MENTION_RE = re.compile(r'@\w+')


def preprocess(text: str):
    """Return (clean_text, tokens) after full NLP pipeline."""
    t = text.lower()
    t = _URL_RE.sub(' ', t)
    t = _HASH_RE.sub(' ', t)
    t = _EMOJI_RE.sub(' ', t)
    t = t.encode('ascii', 'ignore').decode('ascii')
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\d+', ' ', t)
    t = ' '.join(t.split())

    try:
        toks = word_tokenize(t)
    except Exception:
        toks = t.split()

    # Remove stopwords but keep target-indicator words (pronouns etc.)
    _keep = {'you', 'your', 'yours', 'yourself', 'ye', 'u', 'ur'}
    toks = [tk for tk in toks if tk not in _stop_words or tk in _keep]
    if _lemmatizer is not None:
        try:
            toks = [_lemmatizer.lemmatize(tk) for tk in toks]
        except Exception:
            pass
    return t, toks


# ── Detection helpers ─────────────────────────────────────────────────────────
def _find_mentions(original: str):
    """Return list of @username mentions found in original text."""
    return _MENTION_RE.findall(original)


def _find_targets(original: str):
    """Find all target indicators (@ mentions + words/phrases) in original text."""
    found = set()

    # 1. @username always counts
    for m in _find_mentions(original):
        found.add(m)

    low = original.lower()

    # 2. Multi-word target phrases (longest first)
    for phrase in target_phrases:
        if re.search(r'\b' + re.escape(phrase) + r'\b', low):
            found.add(phrase)

    # 3. Single-word tokens
    words = re.findall(r"[a-z']+", low)
    for w in words:
        if w in target_set:
            found.add(w)

    return sorted(found)


def _find_offensive(tokens, clean_text: str):
    """Find HurtLex offensive words/phrases in preprocessed tokens & clean text."""
    found = set()

    # Multi-word HurtLex phrases in clean text (longest first)
    for phrase in hurtlex_phrases:
        if re.search(r'\b' + re.escape(phrase) + r'\b', clean_text):
            found.add(phrase)

    # Single-word tokens
    for tk in tokens:
        if tk in hurtlex_tokens:
            found.add(tk)

    return sorted(found)


def _model_score(clean_text: str):
    """Return ML probability of cyberbullying (0–1) or None if no model."""
    if ml_model is None or ml_vectorizer is None:
        return None
    try:
        X = ml_vectorizer.transform([clean_text])
        proba = ml_model.predict_proba(X)[0]
        classes = list(ml_model.classes_)
        idx = classes.index(1) if 1 in classes else 1
        return float(proba[idx])
    except Exception:
        return None


def _compute_risk(offensive, targets, clean_text):
    """Compute final risk score combining rules + ML."""
    has_off = len(offensive) > 0
    has_tgt = len(targets)  > 0

    # Rule-based base score
    if has_off and has_tgt:
        rule_score = min(0.70 + 0.04 * len(offensive) + 0.03 * len(targets), 1.0)
    elif has_off:
        rule_score = 0.30
    elif has_tgt:
        rule_score = 0.10
    else:
        rule_score = 0.05

    ml = _model_score(clean_text)
    if ml is not None:
        return (rule_score * 0.5 + ml * 0.5)
    return rule_score


def _risk_level(score):
    if score >= 0.60:
        return 'High'
    if score >= 0.30:
        return 'Medium'
    return 'Low'


def _safer_text(original, offensive, targets):
    s = original
    s = _MENTION_RE.sub('<span class="replaced">[person]</span>', s)
    for phrase in sorted(offensive, key=len, reverse=True):
        s = re.sub(r'\b' + re.escape(phrase) + r'\b',
                   '<span class="replaced">[removed]</span>', s, flags=re.IGNORECASE)
    return s


def _highlight_original(original, offensive, targets):
    """Return HTML with offensive words in red, target indicators in blue."""
    s = original

    # Highlight mentions
    s = _MENTION_RE.sub(
        lambda m: f'<mark class="target-mark">{m.group()}</mark>', s)

    # Highlight multi-word target phrases
    for phrase in sorted(targets, key=len, reverse=True):
        if ' ' in phrase:
            s = re.sub(r'\b' + re.escape(phrase) + r'\b',
                       f'<mark class="target-mark">{phrase}</mark>', s,
                       flags=re.IGNORECASE)

    # Highlight offensive phrases
    for phrase in sorted(offensive, key=len, reverse=True):
        if ' ' in phrase:
            s = re.sub(r'\b' + re.escape(phrase) + r'\b',
                       f'<mark class="offensive-mark">{phrase}</mark>', s,
                       flags=re.IGNORECASE)

    # Highlight single-word targets
    for tgt in targets:
        if ' ' not in tgt and not tgt.startswith('@'):
            s = re.sub(r'\b' + re.escape(tgt) + r'\b',
                       f'<mark class="target-mark">\\g<0></mark>', s,
                       flags=re.IGNORECASE)

    # Highlight single-word offensive
    for w in offensive:
        if ' ' not in w:
            s = re.sub(r'\b' + re.escape(w) + r'\b',
                       f'<mark class="offensive-mark">\\g<0></mark>', s,
                       flags=re.IGNORECASE)

    return s


# ── Core analysis ─────────────────────────────────────────────────────────────
def analyze(text: str) -> dict:
    text = text.strip()
    if not text:
        return {'error': 'Empty input.'}

    # Step 1 – target detection on RAW text
    targets   = _find_targets(text)

    # Step 2 – preprocess
    clean, tokens = preprocess(text)

    # Step 3 – HurtLex matching
    offensive = _find_offensive(tokens, clean)

    # Step 4 – rule
    rule_triggered   = bool(offensive) and bool(targets)
    is_cyberbullying = rule_triggered

    # Step 5 – scores
    risk_score  = _compute_risk(offensive, targets, clean)
    risk_pct    = int(round(risk_score * 100))
    risk_level  = _risk_level(risk_score)
    ml          = _model_score(clean)
    confidence  = round(ml if ml is not None else risk_score, 4)

    # Step 6 – presentation
    if is_cyberbullying:
        detection_result = 'Cyberbullying Detected'
        warning  = 'This message may be harmful. Please revise before posting.'
        explanation = (f'Offensive word(s) detected: {", ".join(offensive) or "—"}. '
                       f'Target indicator(s) found: {", ".join(targets) or "—"}.')
        highlighted  = _highlight_original(text, offensive, targets)
        safer_text   = _safer_text(text, offensive, targets)
    else:
        detection_result = 'Safe Content'
        warning     = ''
        highlighted = text
        safer_text  = ''
        if offensive and not targets:
            explanation = ('Potentially strong language detected, but no specific person '
                           'was targeted — may be self-referential or general expression.')
        elif targets and not offensive:
            explanation = 'A person was addressed, but no offensive language was found.'
        else:
            explanation = 'No offensive language or direct targeting detected.'

    return {
        'detection_result': detection_result,
        'is_cyberbullying': is_cyberbullying,
        'risk_score_percent': risk_pct,
        'risk_score':        round(risk_score, 4),
        'risk_level':        risk_level,
        'confidence_score':  confidence,
        'offensive_words':   offensive,
        'target_indicators': targets,
        'rule_triggered':    rule_triggered,
        'warning':           warning,
        'explanation':       explanation,
        'highlighted_text':  highlighted,
        'safer_text':        safer_text,
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
