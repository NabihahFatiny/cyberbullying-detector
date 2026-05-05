import os, re, string
from flask import Flask, render_template, request, jsonify
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

app = Flask(__name__)

# ── NLTK bootstrap ──────────────────────────────────────────────────
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

# ── Target Indicators ──────────────────────────────────────────────────
# Words that indicate targeting someone
_TARGET_WORDS = {
    'you', 'your', 'yours', 'yourself', 'u', 'ur', 'ye', 'ya',
    'bro', 'dude', 'man', 'buddy', 'pal', 'friend', 'kid', 'son',
    'mate', 'homie', 'fam', 'sister', 'brother', 'girl', 'boy',
    'lady', 'sir', 'mister', 'miss', 'yall', 'yous'
}

# ── Offensive Words ─────────────────────────────────────────────────────
# Only words that are actually offensive in cyberbullying context
_OFFENSIVE_WORDS = {
    # Direct insults
    'stupid', 'idiot', 'dumb', 'moron', 'idiot', 'fool', 'loser',
    'worthless', 'useless', 'pathetic', 'failure', 'brainless', 'clueless',
    
    # Appearance attacks
    'ugly', 'hideous', 'disgusting', 'gross', 'fat',
    
    # Hostility
    'hate', 'despise', 'detest', 'loathe', 'kill', 'hurt', 'attack', 'destroy', 'ruin',
    
    # Social rejection
    'weirdo', 'freak', 'outcast', 'loner',
    
    # General insults
    'trash', 'garbage', 'pig', 'rat', 'snake',
}

# ── Text preprocessing ───────────────────────────────────────────────
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

try:
    _lemmatizer = WordNetLemmatizer()
except Exception:
    _lemmatizer = None
try:
    _stop_words = set(stopwords.words('english'))
except Exception:
    _stop_words = set()

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

    # Remove stopwords but keep target-indicator words
    toks = [tk for tk in toks if tk not in _stop_words or tk in _TARGET_WORDS]
    if _lemmatizer is not None:
        try:
            toks = [_lemmatizer.lemmatize(tk) for tk in toks]
        except Exception:
            pass
    return t, toks

# ── Detection helpers ─────────────────────────────────────────────────
def _find_targets(text: str):
    """Find target indicators in text."""
    found = set()
    tokens = text.lower().split()
    
    # Find target words
    for token in tokens:
        if token in _TARGET_WORDS:
            found.add(token)
    
    # Find @mentions
    mentions = _MENTION_RE.findall(text)
    for mention in mentions:
        found.add(mention)
    
    return sorted(found)

def _find_offensive(tokens, clean_text: str):
    """Find offensive words in tokens."""
    found = set()
    
    for token in tokens:
        if token in _OFFENSIVE_WORDS:
            found.add(token)
    
    return sorted(found)

def _compute_risk(offensive, targets):
    """Compute risk score based on pattern matching."""
    has_offensive = len(offensive) > 0
    has_targets = len(targets) > 0
    
    # STRICT: Only cyberbullying if BOTH offensive AND targeting
    if has_offensive and has_targets:
        # High risk when both are present
        base_score = 0.70
        # Add penalty for multiple offensive words
        offensive_penalty = min(0.04 * len(offensive), 0.20)
        # Add penalty for multiple targets
        target_penalty = min(0.03 * len(targets), 0.10)
        risk_score = min(base_score + offensive_penalty + target_penalty, 1.0)
    elif has_offensive:
        # Medium risk if only offensive words
        risk_score = 0.30
    elif has_targets:
        # Low risk if only targeting
        risk_score = 0.10
    else:
        # Very low risk if neither
        risk_score = 0.05
    
    return risk_score

def _risk_level(score):
    if score >= 0.60:
        return 'High'
    if score >= 0.30:
        return 'Medium'
    return 'Low'

def _highlight_text(text: str, offensive: list, targets: list):
    """Return HTML with offensive words in red, targets in blue."""
    s = text
    
    # Highlight @mentions
    s = _MENTION_RE.sub(
        lambda m: f'<mark class="target-mark">{m.group()}</mark>', s)
    
    # Highlight target words
    for target in targets:
        if not target.startswith('@'):
            s = re.sub(r'\b' + re.escape(target) + r'\b',
                       f'<mark class="target-mark">{target}</mark>', s,
                       flags=re.IGNORECASE)
    
    # Highlight offensive words
    for word in offensive:
        s = re.sub(r'\b' + re.escape(word) + r'\b',
                       f'<mark class="offensive-mark">{word}</mark>', s,
                       flags=re.IGNORECASE)
    
    return s

# ── Core analysis ─────────────────────────────────────────────────────
def analyze(text: str) -> dict:
    text = text.strip()
    if not text:
        return {'error': 'Empty input.'}
    
    # Step 1: Find targets
    targets = _find_targets(text)
    
    # Step 2: Preprocess text
    clean, tokens = preprocess(text)
    
    # Step 3: Find offensive words
    offensive = _find_offensive(tokens, clean)
    
    # Step 4: Determine cyberbullying (STRICT rule)
    has_offensive = len(offensive) > 0
    has_targets = len(targets) > 0
    is_cyberbullying = has_offensive and has_targets
    
    # Step 5: Calculate scores
    risk_score = _compute_risk(offensive, targets)
    risk_pct = int(round(risk_score * 100))
    risk_level = _risk_level(risk_score)
    confidence = round(risk_score, 4)
    
    # Step 6: Generate response
    if is_cyberbullying:
        detection_result = 'Cyberbullying Detected'
        warning = 'This message may be harmful. Please revise before posting.'
        explanation = (f'Offensive word(s) detected: {", ".join(offensive) or "—"}. '
                       f'Target indicator(s) found: {", ".join(targets) or "—"}.')
        highlighted = _highlight_text(text, offensive, targets)
        safer_text = ''
    else:
        detection_result = 'Safe Content'
        warning = ''
        highlighted = text
        safer_text = ''
        
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
        'risk_score': round(risk_score, 4),
        'risk_level': risk_level,
        'confidence_score': confidence,
        'offensive_words': offensive,
        'target_indicators': targets,
        'rule_triggered': is_cyberbullying,
        'warning': warning,
        'explanation': explanation,
        'highlighted_text': highlighted,
        'safer_text': safer_text,
    }

# ── Routes ────────────────────────────────────────────────────────────
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
