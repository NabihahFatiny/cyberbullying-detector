import os
from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

# Simple word lists (no NLTK needed)
_TARGET_WORDS = {
    'you', 'your', 'yours', 'yourself', 'u', 'ur', 'ye', 'ya',
    'bro', 'dude', 'man', 'buddy', 'pal', 'friend', 'kid', 'son',
    'mate', 'homie', 'fam', 'sister', 'brother', 'girl', 'boy',
    'lady', 'sir', 'mister', 'miss', 'yall', 'yous'
}

_OFFENSIVE_WORDS = {
    # Direct insults
    'stupid', 'idiot', 'dumb', 'moron', 'idiot', 'fool', 'loser',
    # Appearance attacks
    'ugly', 'hideous', 'disgusting', 'gross', 'fat',
    # Hostility
    'hate', 'despise', 'detest', 'loathe',
    # Social rejection
    'weirdo', 'freak', 'outcast', 'loner',
    # Worthlessness
    'worthless', 'useless', 'pathetic', 'hopeless', 'failure',
    # Violence/threat
    'kill', 'hurt', 'attack', 'destroy', 'ruin',
    # General insults
    'trash', 'garbage', 'pig', 'rat', 'snake',
}

def find_targets(text):
    """Find target indicators in text."""
    found = set()
    words = text.lower().split()
    
    # Find @mentions
    mentions = re.findall(r'@\w+', text)
    for mention in mentions:
        found.add(mention)
    
    # Find target words
    for word in words:
        if word in _TARGET_WORDS:
            found.add(word)
    
    return sorted(found)

def find_offensive(text):
    """Find offensive words in text."""
    found = set()
    words = text.lower().split()
    
    for word in words:
        if word in _OFFENSIVE_WORDS:
            found.add(word)
    
    return sorted(found)

def compute_risk(offensive, targets):
    """Compute risk score - only cyberbullying if BOTH present."""
    has_offensive = len(offensive) > 0
    has_targets = len(targets) > 0
    
    # STRICT: Only cyberbullying if BOTH offensive AND targeting
    if has_offensive and has_targets:
        base_score = 0.70
        # Add penalties for multiple words
        offensive_penalty = min(0.04 * len(offensive), 0.20)
        target_penalty = min(0.03 * len(targets), 0.10)
        risk_score = min(base_score + offensive_penalty + target_penalty, 1.0)
    elif has_offensive:
        # Medium risk if only offensive
        risk_score = 0.30
    elif has_targets:
        # Low risk if only targeting
        risk_score = 0.10
    else:
        # Very low risk if neither
        risk_score = 0.05
    
    return risk_score

def get_risk_level(score):
    if score >= 0.60:
        return 'High'
    if score >= 0.30:
        return 'Medium'
    return 'Low'

def analyze_text(text):
    """Analyze text for cyberbullying."""
    targets = find_targets(text)
    offensive = find_offensive(text)
    
    # Rule-based detection
    is_cyberbullying = len(targets) > 0 and len(offensive) > 0
    
    # Calculate scores
    risk_score = compute_risk(offensive, targets)
    risk_pct = int(round(risk_score * 100))
    risk_level = get_risk_level(risk_score)
    confidence = round(risk_score, 4)
    
    return {
        'is_cyberbullying': is_cyberbullying,
        'risk_score': risk_score,
        'risk_level': risk_level,
        'confidence_score': confidence,
        'offensive_words': offensive,
        'target_indicators': targets,
        'hurtlex_matches': offensive,
        'target_matches': targets,
        'probability': risk_score,
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def api_analyze():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided.'}), 400
    
    result = analyze_text(text)
    
    return jsonify({
        'detection_result': 'Cyberbullying Detected' if result['is_cyberbullying'] else 'Safe Content',
        'is_cyberbullying': result['is_cyberbullying'],
        'risk_score_percent': int(round(result['risk_score'] * 100)),
        'risk_score': round(result['risk_score'], 4),
        'risk_level': result['risk_level'],
        'confidence_score': result['confidence_score'],
        'offensive_words': result['offensive_words'],
        'target_indicators': result['target_indicators'],
        'rule_triggered': result['is_cyberbullying'],
        'warning': 'This message may be harmful. Please revise before posting.' if result['is_cyberbullying'] else '',
        'explanation': f'Offensive word(s) detected: {", ".join(result["offensive_words"]) or "—"}. '
                       f'Target indicator(s) found: {", ".join(result["target_indicators"]) or "—"}.'
                       if result['is_cyberbullying'] else 'No offensive language or direct targeting detected.',
        'highlighted_text': text,
        'safer_text': '',
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
