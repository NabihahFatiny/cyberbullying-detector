"""
Train a TF-IDF + Logistic Regression model on synthetic cyberbullying data.
Run this once to generate model/logistic_model.pkl and model/tfidf_vectorizer.pkl
"""
import os, re, random
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

os.makedirs('model', exist_ok=True)

# --- load HurtLex lemmas ---
def load_hurtlex():
    for p in ('data/hurtlex_EN.tsv', 'hurtlex_EN.tsv'):
        if os.path.exists(p):
            df = pd.read_csv(p, sep='\t', on_bad_lines='skip')
            if 'lemma' in df.columns:
                return df['lemma'].dropna().str.lower().str.strip().tolist()
    return []

# --- load target indicators ---
def load_targets():
    for p in ('data/target_indicators.txt', 'target_indicators.txt'):
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return [ln.strip().lower() for ln in f if ln.strip() and ' ' not in ln.strip()]
    return ['you', 'your', 'u', 'bro', 'dude', 'man', 'buddy', 'pal', 'kid', 'son', 'girl', 'boy']

hurtlex  = load_hurtlex()
targets  = load_targets()

# Filter to single offensive words that look realistic
single_off = [w for w in hurtlex if ' ' not in w and len(w) > 2
              and re.match(r'^[a-z]+$', w)]
random.shuffle(single_off)
single_off = single_off[:300] if len(single_off) > 300 else single_off

# Sentence templates
cyber_templates = [
    "{tgt} are such a {off}",
    "{tgt} are a complete {off}",
    "hey {tgt} you {off} piece of trash",
    "{tgt} look like a total {off}",
    "{tgt} stupid {off} get out",
    "nobody likes {tgt} because {tgt} a {off}",
    "go away {tgt} {off}",
    "{tgt} deserve nothing you {off}",
    "i hate {tgt} {off}",
    "{tgt} are worthless like a {off}",
    "@user {tgt} is such a {off}",
    "everyone thinks {tgt} a {off}",
    "shut up {tgt} you {off}",
    "{tgt} will always be a {off}",
    "look at {tgt} acting like a {off}",
]

safe_templates = [
    "I feel so {off} today",
    "that was a {off} move by me",
    "i acted like a {off} in that moment",
    "sometimes i think im a {off}",
    "feeling like a {off} after that mistake",
    "the weather is nice today",
    "i love spending time with friends",
    "just had a great coffee this morning",
    "the movie last night was amazing",
    "finished my homework early today",
    "feeling happy and grateful",
    "good morning everyone",
    "i really enjoy reading books",
    "nature walks are so refreshing",
    "cooked dinner for the first time",
    "practice makes perfect",
    "learning something new every day",
    "music helps me concentrate",
    "spent the day at the park",
    "started a new hobby this week",
]

samples, labels = [], []

if single_off and targets:
    for _ in range(1500):
        off = random.choice(single_off)
        tgt = random.choice(targets[:20])
        tmpl = random.choice(cyber_templates)
        s = tmpl.format(tgt=tgt, off=off)
        samples.append(s); labels.append(1)

    for _ in range(1500):
        tmpl = random.choice(safe_templates)
        if '{off}' in tmpl and single_off:
            s = tmpl.format(off=random.choice(single_off))
        else:
            s = tmpl
        samples.append(s); labels.append(0)
else:
    # absolute fallback
    samples = [
        "you are stupid and ugly", "you idiot get out", "bro you are trash",
        "hey dude you loser", "you pathetic moron",
        "i feel dumb today", "nice weather outside", "i love learning",
        "just had coffee", "good morning everyone",
    ]
    labels = [1,1,1,1,1, 0,0,0,0,0]

# Vectorize & train
vec = TfidfVectorizer(ngram_range=(1,2), max_features=10000, sublinear_tf=True)
X   = vec.fit_transform(samples)
y   = np.array(labels)

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

clf = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
clf.fit(X_tr, y_tr)

print("=== Evaluation ===")
print(classification_report(y_te, clf.predict(X_te)))

joblib.dump(clf, 'model/logistic_model.pkl')
joblib.dump(vec, 'model/tfidf_vectorizer.pkl')
print("Model saved to model/")
