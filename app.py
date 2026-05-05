from flask import Flask, jsonify, request
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Cyberbullying Detector is working!"

@app.route('/test')
def test():
    return jsonify({"status": "working", "message": "API is functional"})

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'No text provided.'}), 400
    
    # Simple rule-based detection
    has_target = any(word in text.lower() for word in ['you', 'your', 'u', 'ur'])
    has_offensive = any(word in text.lower() for word in ['stupid', 'idiot', 'hate', 'ugly'])
    
    is_cyberbullying = has_target and has_offensive
    
    if is_cyberbullying:
        risk_score = 0.75
        risk_level = "High"
    else:
        risk_score = 0.10
        risk_level = "Low"
    
    return jsonify({
        'detection_result': 'Cyberbullying Detected' if is_cyberbullying else 'Safe Content',
        'is_cyberbullying': is_cyberbullying,
        'risk_score_percent': int(risk_score * 100),
        'risk_score': round(risk_score, 4),
        'risk_level': risk_level,
        'confidence_score': round(risk_score, 4),
        'offensive_words': [word for word in ['stupid', 'idiot', 'hate', 'ugly'] if word in text.lower()],
        'target_indicators': [word for word in ['you', 'your', 'u', 'ur'] if word in text.lower()],
        'rule_triggered': is_cyberbullying,
        'warning': 'This message may be harmful. Please revise before posting.' if is_cyberbullying else '',
        'explanation': f'Offensive word(s) detected: {", ".join([word for word in ["stupid", "idiot", "hate", "ugly"] if word in text.lower()]) or "—"}. '
                       f'Target indicator(s) found: {", ".join([word for word in ["you", "your", "u", "ur"] if word in text.lower()]) or "—"}.'
                       if is_cyberbullying else 'No offensive language or direct targeting detected.',
        'highlighted_text': text,
        'safer_text': '',
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
