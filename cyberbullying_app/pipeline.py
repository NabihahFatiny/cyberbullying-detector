import csv
import json
import math
import random
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree


XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MODEL_VERSION = 6
MODEL_DISCLAIMER = (
    "This automated result is a model-generated indicator, not a confirmed "
    "judgment of cyberbullying or actual harm. Human review is recommended."
)
# Sentence-level rewrites for the safer-rewrite feature: instead of swapping
# individual words in place (which reads as an edited insult, not a genuine
# rewrite), each entry maps a flagged word to one complete, natural,
# respectful sentence that addresses the underlying issue/behaviour rather
# than the person - e.g. "idiot" -> "I disagree with your idea." HurtLex only
# identifies which words are harmful here - it never supplies this wording,
# and none of this affects the trained model's prediction.
CURATED_SAFE_SENTENCES = {
    # Intelligence-related insults
    "idiot": "I disagree with your idea.",
    "stupid": "I think you may have misunderstood the topic.",
    "dumb": "Could you review the information again?",
    "moron": "I do not agree with your answer.",
    "fool": "I think that decision was unwise.",
    "brainless": "Please think carefully before making a decision.",
    "slow": "Please take your time and review the instructions.",
    "witless": "Please think carefully before making a decision.",
    "thickheaded": "Please think carefully before making a decision.",
    "dense": "I think you may have misunderstood the topic.",
    "imbecile": "I do not agree with your answer.",
    "dimwit": "I do not agree with your answer.",
    "nitwit": "I do not agree with your answer.",
    "dunce": "I think that decision was unwise.",
    "airhead": "I think you may have misunderstood the topic.",
    "airheaded": "I think you may have misunderstood the topic.",
    "blockhead": "I do not agree with your answer.",
    "bonehead": "I do not agree with your answer.",
    "numbskull": "I do not agree with your answer.",
    "halfwit": "I do not agree with your answer.",
    "simpleton": "I think that decision was unwise.",
    "cretin": "I do not agree with your answer.",
    "buffoon": "I do not think you are taking this discussion seriously.",
    "dolt": "I do not agree with your answer.",
    "twit": "I do not agree with your answer.",
    "oaf": "I do not agree with your answer.",
    "nincompoop": "I do not agree with your answer.",
    "meathead": "I do not agree with your answer.",
    "knucklehead": "I do not agree with your answer.",
    "lunkhead": "I do not agree with your answer.",
    "birdbrain": "I think you may have misunderstood the topic.",
    "scatterbrain": "I think you may have misunderstood the topic.",
    "dumbbell": "I do not agree with your answer.",
    # Mockery / not taking things seriously
    "clown": "I do not think you are taking this discussion seriously.",
    "joke": "I do not think your response addresses the issue.",
    # Appearance (mild only - see VIOLENT_THREAT_TERMS/PROFANITY_TERMS for the rest)
    "ugly": "I should not comment negatively on someone's appearance.",
    "hideous": "I should not comment negatively on someone's appearance.",
    "freakish": "I should respect people's differences.",
    "disgusting": "I found that unpleasant, but I should not comment on someone's appearance.",
    "revolting": "I found that unpleasant, but I should not comment on someone's appearance.",
    "repulsive": "I found that unpleasant, but I should not comment on someone's appearance.",
    "gross": "I found that unpleasant, but I should not comment on someone's appearance.",
    "filthy": "Your appearance seems untidy today.",
    "unkempt": "Your appearance seems untidy today.",
    "sloppy": "Your appearance seems untidy today.",
    "scruffy": "Your appearance seems untidy today.",
    "homely": "I should not comment negatively on someone's appearance.",
    # Value judgments (about the person)
    "worthless": "I think you can make a more positive contribution.",
    "useless": "I think you can make a more positive contribution.",
    "pathetic": "I am disappointed with what happened.",
    "hopeless": "I am disappointed with what happened.",
    "pitiful": "I am disappointed with what happened.",
    "lame": "I think you can make a more positive contribution.",
    "inferior": "I think you can make a more positive contribution.",
    "weak": "I think this could be stronger.",
    "feeble": "I think this could be stronger.",
    "flimsy": "I think this could be stronger.",
    "vile": "I found that unpleasant.",
    "incompetent": "You may need more practice with this task.",
    "unqualified": "You may need more practice with this task.",
    "amateurish": "You may need more practice with this task.",
    "mediocre": "You may need more practice with this task.",
    "subpar": "You may need more practice with this task.",
    "secondrate": "You may need more practice with this task.",
    "terrible": "I am disappointed with what happened.",
    "awful": "I am disappointed with what happened.",
    "horrible": "I am disappointed with what happened.",
    "dreadful": "I am disappointed with what happened.",
    "lousy": "I am disappointed with what happened.",
    "abysmal": "I am disappointed with what happened.",
    "atrocious": "I am disappointed with what happened.",
    "appalling": "I am disappointed with what happened.",
    "deplorable": "I am disappointed with what happened.",
    "wretched": "I am disappointed with what happened.",
    "miserable": "I am disappointed with what happened.",
    "crappy": "I am disappointed with what happened.",
    "shoddy": "I am disappointed with what happened.",
    # Someone's work/output specifically
    "garbage": "Your work needs further improvement.",
    "trash": "Your presentation could be improved with clearer information.",
    # Difference / social exclusion
    "freak": "I should respect people's differences.",
    "weirdo": "I should respect people's differences.",
    "misfit": "I should respect people's differences.",
    "outcast": "Let us make sure everyone feels included.",
    "sheep": "I encourage you to express your own opinion.",
    "follower": "I encourage you to express your own opinion.",
    # Fear / cowardice
    "coward": "I understand that you may feel afraid.",
    "cowardly": "I understand that you may feel afraid.",
    "wimp": "I understand that you may feel afraid.",
    "gutless": "I understand that you may feel afraid.",
    "spineless": "I understand that you may feel afraid.",
    "crybaby": "I understand that this situation may be upsetting.",
    "whiny": "I understand that this situation may be upsetting.",
    # Dishonesty
    "liar": "I am not sure that the information you provided is accurate.",
    "cheater": "I am concerned that the rules may not have been followed.",
    "cheat": "I am concerned that the rules may not have been followed.",
    "hypocrite": "Your actions seem inconsistent with what you said.",
    "traitor": "I feel disappointed because you did not support the group.",
    "fraud": "I am concerned that you may not be presenting accurate information.",
    "fake": "I feel that your response may not be sincere.",
    "phony": "I feel that your response may not be sincere.",
    "scammer": "I am concerned that this offer may be misleading.",
    "snake": "I am finding it difficult to trust your actions.",
    "deceiver": "I am not sure that the information you provided is accurate.",
    "swindler": "I am concerned that this offer may be misleading.",
    "backstabber": "I am finding it difficult to trust your actions.",
    "manipulator": "I am finding it difficult to trust your actions.",
    "crook": "I am finding it difficult to trust your actions.",
    "sneaky": "I am finding it difficult to trust your actions.",
    "shady": "I am finding it difficult to trust your actions.",
    "sketchy": "I am finding it difficult to trust your actions.",
    "shifty": "I am finding it difficult to trust your actions.",
    "underhanded": "I am concerned that the rules may not have been followed.",
    "crooked": "I am not sure that the information you provided is accurate.",
    "corrupt": "I am not sure that the information you provided is accurate.",
    "unscrupulous": "I am concerned that the rules may not have been followed.",
    # Laziness / low effort
    "lazy": "I think you could contribute more effort to the task.",
    "slacker": "Please complete your assigned part of the project.",
    "slob": "Your appearance seems untidy today.",
    "deadbeat": "I think you could contribute more effort to the task.",
    "freeloader": "I would appreciate it if you contributed equally to the group.",
    "parasite": "I would appreciate it if you contributed equally to the group.",
    "leech": "I would appreciate it if you contributed equally to the group.",
    "moocher": "I would appreciate it if you contributed equally to the group.",
    # Arrogance
    "arrogant": "Your response sounds overly confident.",
    "conceited": "Your response sounds overly confident.",
    "smug": "Your response sounds overly confident.",
    "pompous": "Your response sounds overly confident.",
    "snob": "Your response may make others feel excluded.",
    "elitist": "Your response may make others feel excluded.",
    "egotist": "Please allow others to share their achievements too.",
    "narcissist": "Please allow others to share their achievements too.",
    "braggart": "Please allow others to share their achievements too.",
    "showoff": "Please allow others to share their achievements too.",
    # Rudeness / meanness
    "rude": "I found your response disrespectful.",
    "obnoxious": "I found your response disrespectful.",
    "mean": "Your words may hurt someone's feelings.",
    "cruel": "Please consider how your actions may affect others.",
    "heartless": "Please consider how your actions may affect others.",
    "callous": "Please consider how your actions may affect others.",
    "insensitive": "Please consider how your actions may affect others.",
    "spiteful": "Please consider how your actions may affect others.",
    "vindictive": "Please consider how your actions may affect others.",
    "petty": "Please consider how your actions may affect others.",
    "annoying": "I found your response disrespectful.",
    "irritating": "I found your response disrespectful.",
    "bossy": "Please allow others to share their opinions too.",
    "pushy": "Please allow others to share their opinions too.",
    # Immaturity
    "childish": "I think this situation could be handled more maturely.",
    "immature": "I think this situation could be handled more maturely.",
    "babyish": "I think this situation could be handled more maturely.",
    "brat": "I think this situation could be handled more maturely.",
    "bratty": "I think this situation could be handled more maturely.",
    "spoiled": "I think this situation could be handled more maturely.",
    "needy": "I understand that this situation may be upsetting.",
    "clingy": "I understand that this situation may be upsetting.",
    "dramatic": "I think this could be discussed more calmly.",
    "melodramatic": "I think this could be discussed more calmly.",
    # Troublemaking / aggression (non-violent)
    "troublemaker": "Your actions are disrupting the group.",
    "delinquent": "Your actions are disrupting the group.",
    "hooligan": "Your actions are disrupting the group.",
    "nuisance": "Your actions are disrupting the group.",
    "punk": "Your actions are disrupting the group.",
    "thug": "Your actions are disrupting the group.",
    "pest": "Your actions are disrupting the group.",
    "bully": "Your behaviour is causing harm and needs to stop.",
    "abuser": "Your behaviour is causing harm and needs to stop.",
    "tormentor": "Your behaviour is causing harm and needs to stop.",
    "oppressor": "Your behaviour is causing harm and needs to stop.",
    "tyrant": "Your behaviour is causing harm and needs to stop.",
    "menace": "Your behaviour is causing harm and needs to stop.",
    # Greed / self-interest
    "greedy": "Please consider sharing fairly with others.",
    "stingy": "I would appreciate it if you were more willing to share.",
    "miserly": "I would appreciate it if you were more willing to share.",
    "selfish": "Please consider sharing fairly with others.",
    "gluttonous": "Please consider sharing fairly with others.",
    "vain": "Please allow others to share their achievements too.",
    "envious": "Please consider how your actions may affect others.",
    "jealous": "Please consider how your actions may affect others.",
    # Gossip / privacy
    "gossip": "Please avoid sharing other people's private information.",
    "gossiper": "Please avoid sharing other people's private information.",
    "busybody": "Please respect other people's privacy.",
    "nosy": "Please respect other people's privacy.",
    "snitch": "Please avoid sharing other people's private information.",
    "tattletale": "Please avoid sharing other people's private information.",
    # Boring / stubborn
    "boring": "I am having difficulty staying engaged with this discussion.",
    "dull": "I am having difficulty staying engaged with this discussion.",
    "tedious": "I am having difficulty staying engaged with this discussion.",
    "monotonous": "I am having difficulty staying engaged with this discussion.",
    "bland": "I am having difficulty staying engaged with this discussion.",
    "stubborn": "Please consider another point of view.",
    "pigheaded": "Please consider another point of view.",
    "obstinate": "Please consider another point of view.",
    # Careless / disorganized
    "careless": "Please take more care with this.",
    "clumsy": "Please take more care with this.",
    "chaotic": "This could be more organized.",
    "klutz": "Please take more care with this.",
    "dork": "I should respect people's differences.",
    "dweeb": "I should respect people's differences.",
    "pushover": "I understand that you may feel afraid.",
    "doormat": "I understand that you may feel afraid.",
    "scum": "I am disappointed with what happened.",
    "scumbag": "I am disappointed with what happened.",
    "creep": "I found your behaviour unpleasant.",
    "rat": "I am finding it difficult to trust your actions.",
    "pig": "I found your behaviour unpleasant.",
    "loser": "I think you can make a more positive contribution.",
    "failure": "I think you can make a more positive contribution.",
    "bum": "I think you could contribute more effort to the task.",
    "nasty": "I found your behaviour unpleasant.",
    "hate": "I strongly disagree with this.",
    "despise": "I strongly disagree with this.",
    "loathe": "I strongly disagree with this.",
    "detest": "I strongly disagree with this.",
    "abhor": "I strongly disagree with this.",
}

# HurtLex's own category tags (the "category" column in hurtlex_EN.tsv, e.g.
# "cds", "an", "qas"...) give a fallback sentence for any of the ~11,000
# lexicon words not covered above, in the same natural "I" statement style,
# extending coverage far beyond the curated list. Checked in this order so a
# message matching several categories gets one consistent sentence.
# Reference: Bassignana et al., "HurtLex: A Multilingual Lexicon of Words to
# Hurt", CLiC-it 2018.
HURTLEX_CATEGORY_PRIORITY = ["cds", "qas", "dmc", "svp", "re", "an", "or", "pa"]
HURTLEX_CATEGORY_SENTENCES = {
    "cds": "I do not agree with how that was expressed.",
    "qas": "I think this could be discussed more constructively.",
    "dmc": "I have concerns about that behaviour.",
    "svp": "I think this could be approached differently.",
    "re": "I have concerns about what happened.",
    "an": "Please avoid name-calling and focus on the actual concern.",
    "or": "Let's keep this conversation respectful.",
    "pa": "Let's avoid judging someone by their job or role.",
}

# Any matched term in this set gets the safety-alert message below instead of
# a softened sentence - HurtLex has no dedicated "violence" category (these
# share the generic "re" crime category with harmless words like "liar"), so
# this small, human-reviewed list is the only reliable way to catch genuine
# threats. A softened rewrite of a threat would still be inappropriate to
# suggest; the right response is to stop the post and flag it, not reword it.
VIOLENT_THREAT_TERMS = {
    "kill", "murder", "hurt", "destroy", "beat", "attack", "fight",
    "smash", "crush", "demolish", "harm", "torture", "stab", "shoot",
    "strangle", "slap", "punch", "burn",
}
VIOLENT_THREAT_MESSAGE = (
    "Threatening language detected. Do not post this message and seek help "
    "from a trusted adult immediately."
)

# Universal fallback whenever at least one harmful term was matched but it
# isn't in the curated list or a rewritable HurtLex category (e.g. slurs and
# strong profanity) - acknowledges the emotion without repeating the word or
# leaving the box empty.
GENERAL_CONCERN_SENTENCE = "I am upset, but I would like to discuss this calmly."
STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "ours",
    "she",
    "so",
    "than",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "those",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "with",
}
IRREGULAR_LEMMAS = {
    "am": "be",
    "are": "be",
    "is": "be",
    "was": "be",
    "were": "be",
    "has": "have",
    "had": "have",
    "does": "do",
    "did": "do",
}


class PipelineConfigError(RuntimeError):
    """Raised when deployment-time data files are missing or invalid."""


def unique_in_order(items: Sequence[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def lemmatize_token(token: str) -> str:
    if not token:
        return token
    if token in IRREGULAR_LEMMAS:
        return IRREGULAR_LEMMAS[token]
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("ing"):
        base = token[:-3]
        return base[:-1] if len(base) > 2 and base[-1] == base[-2] else base
    if len(token) > 3 and token.endswith("ed"):
        base = token[:-2]
        return base[:-1] if len(base) > 2 and base[-1] == base[-2] else base
    if len(token) > 3 and token.endswith("es"):
        stem = token[:-2]
        if len(stem) >= 5:
            return stem
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def clean_and_tokenize(
    text: str,
    *,
    remove_stopwords: bool,
    lemmatize: bool,
) -> List[str]:
    normalized = "" if text is None else str(text).lower()
    normalized = re.sub(r"http\S+|www\S+", " ", normalized)
    normalized = re.sub(r"#\w+", " ", normalized)
    normalized = re.sub(r"@\w+", " ", normalized)
    normalized = re.sub(r"[^\x00-\x7F]+", " ", normalized)
    normalized = re.sub(r"\d+", " ", normalized)
    normalized = re.sub(r"[^a-z\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return []

    processed: List[str] = []
    for token in tokens:
        if remove_stopwords and token in STOPWORDS:
            continue
        value = lemmatize_token(token) if lemmatize else token
        if remove_stopwords and value in STOPWORDS:
            continue
        if value:
            processed.append(value)
    return processed


def preprocess_text(text: str) -> Dict[str, object]:
    raw_text = "" if text is None else str(text)
    lowered = raw_text.lower()
    username_mentions = unique_in_order(re.findall(r"@\w+", lowered))
    feature_tokens = clean_and_tokenize(raw_text, remove_stopwords=True, lemmatize=True)
    surface_tokens = clean_and_tokenize(raw_text, remove_stopwords=False, lemmatize=False)
    hurtlex_tokens = clean_and_tokenize(raw_text, remove_stopwords=False, lemmatize=True)

    return {
        "raw_text": raw_text,
        "username_mentions": username_mentions,
        "cleaned_text": " ".join(feature_tokens),
        "feature_tokens": feature_tokens,
        "surface_tokens": surface_tokens,
        "hurtlex_tokens": hurtlex_tokens,
        "target_tokens": surface_tokens,
    }


def tokenize_feature_text(text: str) -> List[str]:
    return list(preprocess_text(text)["feature_tokens"])


def tokenize_text_with_spans(text: str) -> List[Tuple[str, int, int]]:
    source = "" if text is None else str(text)
    tokens: List[Tuple[str, int, int]] = []
    for match in re.finditer(r"[A-Za-z]+", source):
        tokens.append((match.group(0).lower(), match.start(), match.end()))
    return tokens


def normalize_phrase(text: str, *, lemmatize: bool) -> str:
    tokens = clean_and_tokenize(text, remove_stopwords=False, lemmatize=lemmatize)
    return " ".join(tokens).strip()


def build_phrase_index(phrases: Sequence[str], *, lemmatize: bool) -> Dict[int, Set[str]]:
    index: Dict[int, Set[str]] = {}
    for phrase in phrases:
        normalized = normalize_phrase(phrase, lemmatize=lemmatize)
        if not normalized or normalized == "nan":
            continue
        size = len(normalized.split())
        index.setdefault(size, set()).add(normalized)
    return index


def find_phrase_matches_from_tokens(tokens: Sequence[str], phrase_index: Dict[int, Set[str]]) -> List[str]:
    if not tokens:
        return []

    matches: List[str] = []
    seen: Set[str] = set()
    lengths = sorted(phrase_index, reverse=True)
    start = 0
    token_count = len(tokens)

    while start < token_count:
        matched = False
        for phrase_length in lengths:
            phrases = phrase_index[phrase_length]
            if phrase_length <= 0 or start + phrase_length > token_count:
                continue
            candidate = " ".join(tokens[start : start + phrase_length])
            if candidate in phrases:
                if candidate not in seen:
                    seen.add(candidate)
                    matches.append(candidate)
                start += phrase_length
                matched = True
                break
        if not matched:
            start += 1

    return matches


def recover_surface_phrase_matches(text: str, matches: Sequence[str], *, lemmatize: bool) -> List[str]:
    if not matches:
        return []

    token_spans = tokenize_text_with_spans(text)
    if not token_spans:
        return []

    raw_tokens = [token for token, _start, _end in token_spans]
    compare_tokens = [lemmatize_token(token) if lemmatize else token for token in raw_tokens]
    source = "" if text is None else str(text)
    recovered: List[str] = []
    seen: Set[str] = set()

    for phrase in matches:
        phrase_tokens = phrase.split()
        phrase_length = len(phrase_tokens)
        if phrase_length <= 0 or phrase_length > len(compare_tokens):
            continue
        for start in range(len(compare_tokens) - phrase_length + 1):
            candidate = compare_tokens[start : start + phrase_length]
            if candidate != phrase_tokens:
                continue
            start_pos = token_spans[start][1]
            end_pos = token_spans[start + phrase_length - 1][2]
            surface = source[start_pos:end_pos].strip()
            key = surface.lower()
            if surface and key not in seen:
                seen.add(key)
                recovered.append(surface)
            break

    return recovered


def read_target_words(path: Path) -> Set[str]:
    words = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw_value = line.strip()
            if not raw_value:
                continue
            if raw_value.startswith("@"):
                continue
            normalized = normalize_phrase(raw_value, lemmatize=False)
            if normalized:
                words.add(normalized)
    return words


def read_hurtlex(path: Path) -> Set[str]:
    lexicon = set()
    with path.open("r", encoding="utf-8") as handle:
        header_line = handle.readline().rstrip("\n")
        headers = [item.strip().lower() for item in header_line.split("\t")] if header_line else []
        lemma_index = None
        for column_name in ("lemma", "term"):
            if column_name in headers:
                lemma_index = headers.index(column_name)
                break
        if lemma_index is None:
            lemma_index = 0

        for line in handle:
            cols = line.rstrip("\n").split("\t")
            if lemma_index >= len(cols):
                continue
            normalized = normalize_phrase(cols[lemma_index].strip(), lemmatize=True)
            if normalized:
                lexicon.add(normalized)
    return lexicon


def read_hurtlex_categories(path: Path) -> Dict[str, Set[str]]:
    # Separate from read_hurtlex() on purpose: read_hurtlex()'s output feeds
    # the actual detection/highlighting lexicon and must stay untouched. This
    # reads the same file again just to capture each lemma's HurtLex
    # "category" column, used only by build_safer_rewrite() below to pick a
    # respectful rewrite template - it has no effect on matching or scoring.
    #
    # A lemma can legitimately appear under more than one HurtLex category
    # (e.g. "whore" is tagged both "an" and the more severe "pr"), so every
    # category a lemma is ever tagged with is kept, not just the first one
    # seen in the file.
    categories: Dict[str, Set[str]] = {}
    with path.open("r", encoding="utf-8") as handle:
        header_line = handle.readline().rstrip("\n")
        headers = [item.strip().lower() for item in header_line.split("\t")] if header_line else []
        lemma_index = None
        for column_name in ("lemma", "term"):
            if column_name in headers:
                lemma_index = headers.index(column_name)
                break
        if lemma_index is None:
            lemma_index = 0
        category_index = headers.index("category") if "category" in headers else None
        if category_index is None:
            return categories

        for line in handle:
            cols = line.rstrip("\n").split("\t")
            if lemma_index >= len(cols) or category_index >= len(cols):
                continue
            normalized = normalize_phrase(cols[lemma_index].strip(), lemmatize=True)
            category = cols[category_index].strip().lower()
            if normalized and category:
                categories.setdefault(normalized, set()).add(category)
    return categories


_LEADING_ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+(.+)$", re.IGNORECASE)


def _resolve_safer_sentence(term: str, hurtlex_categories: Dict[str, Set[str]]) -> Optional[str]:
    lowered = term.lower()
    lemma = normalize_phrase(term, lemmatize=True) or lowered

    curated = CURATED_SAFE_SENTENCES.get(lemma) or CURATED_SAFE_SENTENCES.get(lowered)
    if curated:
        return curated

    # HurtLex sometimes lists a leading article as part of the lemma itself
    # (e.g. "an idiot" is its own entry, separate from "idiot", tagged under
    # its own - often noisier - set of categories), and the phrase matcher
    # prefers that longer match. Try the content word alone first, since
    # that's far more likely to hit a precise curated sentence than the
    # combined phrase's own category tags.
    article_match = _LEADING_ARTICLE_RE.match(term)
    if article_match:
        content_sentence = _resolve_safer_sentence(article_match.group(1), hurtlex_categories)
        if content_sentence:
            return content_sentence

    term_categories = hurtlex_categories.get(lemma) or hurtlex_categories.get(lowered)
    if term_categories:
        for category in HURTLEX_CATEGORY_PRIORITY:
            if category in term_categories:
                return HURTLEX_CATEGORY_SENTENCES[category]

    return None


def build_safer_rewrite(offensive_terms: Sequence[str], hurtlex_categories: Dict[str, Set[str]]) -> str:
    # Interface-level safeguard only - this does not touch the trained model,
    # the HurtLex resource, or the pseudo-labelling rule used in the research
    # methodology. Rather than editing the author's own wording (which still
    # reads as an edited insult), this produces one complete, natural,
    # respectful sentence addressing the underlying issue/behaviour instead
    # of the person - e.g. "You are such an idiot." -> "I disagree with your
    # idea." A genuine threat gets a distinct safety message instead of a
    # softened rewrite, since rewording a threat would still be inappropriate
    # to suggest. HurtLex only identifies which words are harmful; it never
    # supplies this wording, and the message shown here never changes the
    # student's original text.
    if not offensive_terms:
        return ""

    lowered_terms = {str(term).lower() for term in offensive_terms}
    if lowered_terms & VIOLENT_THREAT_TERMS:
        return VIOLENT_THREAT_MESSAGE

    for term in offensive_terms:
        sentence = _resolve_safer_sentence(str(term), hurtlex_categories)
        if sentence:
            return sentence

    return GENERAL_CONCERN_SENTENCE


def format_match_text(items: Sequence[str], empty_message: str) -> str:
    if not items:
        return empty_message
    return ", ".join(items)


def sigmoid(value: float) -> float:
    clipped = max(min(value, 35.0), -35.0)
    return 1.0 / (1.0 + math.exp(-clipped))


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, str]] = []
        for row in reader:
            normalized = {}
            for key, value in row.items():
                normalized[str(key or "").strip().lower()] = "" if value is None else str(value)
            if any(value.strip() for value in normalized.values()):
                rows.append(normalized)
        return rows


def col_letter_to_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    value = 0
    for char in letters:
        value = value * 26 + (ord(char.upper()) - 64)
    return value - 1


def _extract_xlsx_to_temp(path: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="cyberbullying-xlsx-"))
    command = r"""
param([string]$src, [string]$tempRoot)
$ErrorActionPreference = 'Stop'
$copy = Join-Path $tempRoot 'dataset.zip'
$unzipped = Join-Path $tempRoot 'unzipped'
New-Item -ItemType Directory -Path $unzipped | Out-Null
$in = [System.IO.File]::Open($src,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
$out = [System.IO.File]::Open($copy,[System.IO.FileMode]::Create,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
$in.CopyTo($out)
$out.Close()
$in.Close()
Expand-Archive -LiteralPath $copy -DestinationPath $unzipped -Force
Write-Output $unzipped
"""
    script_path = temp_root / "extract_xlsx.ps1"
    script_path.write_text(command, encoding="utf-8")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-File", str(script_path), str(path), str(temp_root)],
        capture_output=True,
        text=True,
        check=True,
    )
    extracted_path = result.stdout.strip().splitlines()[-1].strip()
    return Path(extracted_path)


def read_xlsx_rows(path: Path) -> List[Dict[str, str]]:
    extracted_dir = _extract_xlsx_to_temp(path)
    try:
        shared_path = extracted_dir / "xl" / "sharedStrings.xml"
        sheet_path = extracted_dir / "xl" / "worksheets" / "sheet1.xml"

        shared_strings = []
        if shared_path.exists():
            root = ElementTree.fromstring(shared_path.read_bytes())
            for item in root.findall("x:si", XLSX_NS):
                text_parts = [node.text or "" for node in item.findall(".//x:t", XLSX_NS)]
                shared_strings.append("".join(text_parts))

        sheet_root = ElementTree.fromstring(sheet_path.read_bytes())
        rows = []
        for row_node in sheet_root.findall(".//x:sheetData/x:row", XLSX_NS):
            values_by_index = {}
            for cell in row_node.findall("x:c", XLSX_NS):
                ref = cell.attrib.get("r", "")
                index = col_letter_to_index(ref)
                cell_type = cell.attrib.get("t")
                value_node = cell.find("x:v", XLSX_NS)
                inline_node = cell.find("x:is/x:t", XLSX_NS)
                value = ""
                if inline_node is not None and inline_node.text is not None:
                    value = inline_node.text
                elif value_node is not None and value_node.text is not None:
                    value = value_node.text
                    if cell_type == "s":
                        shared_index = int(value)
                        value = shared_strings[shared_index] if shared_index < len(shared_strings) else ""
                values_by_index[index] = value
            if values_by_index:
                width = max(values_by_index) + 1
                row_values = [values_by_index.get(i, "") for i in range(width)]
                rows.append(row_values)
    finally:
        shutil.rmtree(extracted_dir.parent, ignore_errors=True)

    if not rows:
        return []

    headers = [str(item).strip().lower() for item in rows[0]]
    data_rows = []
    for row_values in rows[1:]:
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = row_values[index] if index < len(row_values) else ""
        if any(str(value).strip() for value in record.values()):
            data_rows.append(record)
    return data_rows


def read_dataset_rows(path: Path) -> List[Dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_rows(path)
    if suffix == ".xlsx":
        return read_xlsx_rows(path)
    raise PipelineConfigError("Unsupported dataset format. Use a .csv or .xlsx dataset file.")


def detect_text_column(headers: Iterable[str]) -> Optional[str]:
    candidates = [
        "comment",
        "tweet_text",
        "tweet",
        "text",
        "content",
        "message",
        "post",
    ]
    header_set = list(headers)
    for candidate in candidates:
        if candidate in header_set:
            return candidate
    return None


def build_rule_label(
    text: str,
    lexicon_index: Dict[int, Set[str]],
    lexicon_surface_index: Dict[int, Set[str]],
    target_index: Dict[int, Set[str]],
) -> Tuple[int, List[str], List[str]]:
    preprocessed = preprocess_text(text)
    hurtlex_surface_matches = find_phrase_matches_from_tokens(
        list(preprocessed["surface_tokens"]),
        lexicon_surface_index,
    )
    hurtlex_lemma_matches = find_phrase_matches_from_tokens(
        list(preprocessed["hurtlex_tokens"]),
        lexicon_index,
    )
    hurtlex_matches = hurtlex_surface_matches or hurtlex_lemma_matches
    target_indicator_matches = find_phrase_matches_from_tokens(
        list(preprocessed["target_tokens"]),
        target_index,
    )
    target_matches = unique_in_order(target_indicator_matches + list(preprocessed["username_mentions"]))
    label = 1 if hurtlex_matches and target_matches else 0
    return label, hurtlex_matches, target_matches


def prepare_training_rows(
    rows: Sequence[Dict[str, str]],
    lexicon_index: Dict[int, Set[str]],
    lexicon_surface_index: Dict[int, Set[str]],
    target_index: Dict[int, Set[str]],
) -> Tuple[List[Dict[str, object]], str]:
    if not rows:
        raise PipelineConfigError("The dataset is empty, so the model cannot be trained.")

    text_column = detect_text_column(rows[0].keys())
    if not text_column:
        raise PipelineConfigError(
            "The dataset must include a text column such as comment, tweet_text, tweet, text, content, or message."
        )

    prepared: List[Dict[str, object]] = []
    for row in rows:
        text = str(row.get(text_column, "") or "").strip()
        if not text:
            continue
        preprocessed = preprocess_text(text)
        cleaned_text = str(preprocessed["cleaned_text"]).strip()
        if not cleaned_text:
            continue
        label, hurtlex_matches, target_matches = build_rule_label(
            text,
            lexicon_index,
            lexicon_surface_index,
            target_index,
        )
        prepared.append(
            {
                "comment": text,
                "cleaned_text": cleaned_text,
                "label": label,
                "hurtlex_matches": hurtlex_matches,
                "target_matches": target_matches,
            }
        )

    if len(prepared) < 10:
        raise PipelineConfigError("The dataset does not contain enough usable text rows to train the model.")

    positives = sum(int(item["label"]) for item in prepared)
    negatives = len(prepared) - positives
    if positives == 0 or negatives == 0:
        raise PipelineConfigError(
            "Pseudo-labeling produced only one class. Check the dataset content and supporting lexicon files."
        )

    return prepared, text_column


class TfidfVectorizer:
    def __init__(self, max_features: int = 8000, min_df: int = 2):
        self.max_features = max_features
        self.min_df = min_df
        self.vocabulary: Dict[str, int] = {}
        self.idf: List[float] = []

    def fit(self, documents: Sequence[str]) -> None:
        document_frequency: Counter = Counter()
        term_frequency: Counter = Counter()
        total_documents = len(documents)

        for document in documents:
            tokens = tokenize_feature_text(document)
            if not tokens:
                continue
            unique_tokens = set(tokens)
            document_frequency.update(unique_tokens)
            term_frequency.update(tokens)

        items = [
            (term, df, term_frequency[term])
            for term, df in document_frequency.items()
            if df >= self.min_df
        ]
        items.sort(key=lambda item: (-item[1], -item[2], item[0]))
        if self.max_features > 0:
            items = items[: self.max_features]

        self.vocabulary = {term: index for index, (term, _, _) in enumerate(items)}
        self.idf = [0.0] * len(self.vocabulary)
        for term, index in self.vocabulary.items():
            df = document_frequency[term]
            self.idf[index] = math.log((1.0 + total_documents) / (1.0 + df)) + 1.0

    def transform_one(self, document: str) -> Dict[int, float]:
        counts: Dict[int, int] = {}
        for token in tokenize_feature_text(document):
            index = self.vocabulary.get(token)
            if index is None:
                continue
            counts[index] = counts.get(index, 0) + 1

        if not counts:
            return {}

        vector: Dict[int, float] = {}
        norm = 0.0
        for index, count in counts.items():
            value = (1.0 + math.log(count)) * self.idf[index]
            vector[index] = value
            norm += value * value

        if norm > 0.0:
            scale = math.sqrt(norm)
            for index in list(vector):
                vector[index] = vector[index] / scale

        return vector

    def transform(self, documents: Sequence[str]) -> List[Dict[int, float]]:
        return [self.transform_one(document) for document in documents]

    def to_dict(self) -> Dict[str, object]:
        return {
            "max_features": self.max_features,
            "min_df": self.min_df,
            "vocabulary": self.vocabulary,
            "idf": self.idf,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "TfidfVectorizer":
        instance = cls(
            max_features=int(payload.get("max_features", 8000)),
            min_df=int(payload.get("min_df", 2)),
        )
        instance.vocabulary = {
            str(term): int(index)
            for term, index in dict(payload.get("vocabulary", {})).items()
        }
        instance.idf = [float(value) for value in list(payload.get("idf", []))]
        return instance


class LogisticRegressionClassifier:
    def __init__(
        self,
        epochs: int = 6,
        learning_rate: float = 0.35,
        l2_penalty: float = 0.0005,
        seed: int = 42,
    ):
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.l2_penalty = l2_penalty
        self.seed = seed
        self.weights: List[float] = []
        self.bias: float = 0.0

    def fit(self, vectors: Sequence[Dict[int, float]], labels: Sequence[int], feature_count: int) -> None:
        self.weights = [0.0] * feature_count
        self.bias = 0.0
        indices = list(range(len(vectors)))

        for epoch in range(self.epochs):
            learning_rate = self.learning_rate / (1.0 + (epoch * 0.35))
            random.Random(self.seed + epoch).shuffle(indices)
            for row_index in indices:
                vector = vectors[row_index]
                label = labels[row_index]
                probability = self.predict_probability(vector)
                error = probability - label
                self.bias -= learning_rate * error
                for feature_index, value in vector.items():
                    gradient = (error * value) + (self.l2_penalty * self.weights[feature_index])
                    self.weights[feature_index] -= learning_rate * gradient

    def predict_probability(self, vector: Dict[int, float]) -> float:
        score = self.bias
        for feature_index, value in vector.items():
            score += self.weights[feature_index] * value
        return sigmoid(score)

    def to_dict(self) -> Dict[str, object]:
        return {
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "l2_penalty": self.l2_penalty,
            "seed": self.seed,
            "weights": self.weights,
            "bias": self.bias,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "LogisticRegressionClassifier":
        instance = cls(
            epochs=int(payload.get("epochs", 6)),
            learning_rate=float(payload.get("learning_rate", 0.35)),
            l2_penalty=float(payload.get("l2_penalty", 0.0005)),
            seed=int(payload.get("seed", 42)),
        )
        instance.weights = [float(value) for value in list(payload.get("weights", []))]
        instance.bias = float(payload.get("bias", 0.0))
        return instance


def split_dataset(
    rows: Sequence[Dict[str, object]],
    test_ratio: float = 0.2,
    seed: int = 42,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    test_size = max(1, int(len(rows) * test_ratio))
    test_indices = set(indices[:test_size])

    train_rows = [rows[index] for index in indices if index not in test_indices]
    test_rows = [rows[index] for index in indices if index in test_indices]
    return train_rows, test_rows


def evaluate_predictions(labels: Sequence[int], probabilities: Sequence[float]) -> Dict[str, float]:
    if not labels:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    correct = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0

    for label, probability in zip(labels, probabilities):
        prediction = 1 if probability >= 0.5 else 0
        if prediction == label:
            correct += 1
        if prediction == 1 and label == 1:
            true_positive += 1
        elif prediction == 1 and label == 0:
            false_positive += 1
        elif prediction == 0 and label == 1:
            false_negative += 1

    accuracy = correct / len(labels)
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


class CyberbullyingPipeline:
    def __init__(self, dataset_path: Path, hurtlex_path: Path, target_path: Path):
        self.dataset_path = Path(dataset_path)
        self.hurtlex_path = Path(hurtlex_path)
        self.target_path = Path(target_path)
        self.model_cache_path = self.dataset_path.parent / "tfidf_logreg_model.json"
        self.vectorizer = TfidfVectorizer()
        self.classifier = LogisticRegressionClassifier()
        self.lexicon_words: Set[str] = set()
        self.target_words: Set[str] = set()
        self.lexicon_index: Dict[int, Set[str]] = {}
        self.lexicon_surface_index: Dict[int, Set[str]] = {}
        self.target_index: Dict[int, Set[str]] = {}
        self.hurtlex_categories: Dict[str, Set[str]] = {}
        self.status: Dict[str, object] = {}
        self.trained = False

    def _validate_required_file(self, path: Path, label: str) -> None:
        if path.exists() and path.is_file():
            return
        raise PipelineConfigError(f"Missing required {label} file.")

    def _dataset_signature(self) -> Dict[str, object]:
        # Read in universal-newline text mode so the signature is identical
        # whether the file has CRLF (Windows checkout) or LF (Linux/Vercel
        # checkout) line endings - git's autocrlf otherwise makes the raw
        # byte size differ across platforms and invalidates the cache.
        with self.dataset_path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            content = handle.read()
        return {
            "size": len(content),
        }

    def _load_rule_resources(self) -> None:
        if self.lexicon_words and self.target_words:
            return

        self._validate_required_file(self.hurtlex_path, "HurtLex")
        self._validate_required_file(self.target_path, "target indicator")

        self.lexicon_words = read_hurtlex(self.hurtlex_path)
        self.target_words = read_target_words(self.target_path)
        self.lexicon_index = build_phrase_index(sorted(self.lexicon_words), lemmatize=True)
        self.lexicon_surface_index = build_phrase_index(sorted(self.lexicon_words), lemmatize=False)
        self.target_index = build_phrase_index(sorted(self.target_words), lemmatize=False)
        self.hurtlex_categories = read_hurtlex_categories(self.hurtlex_path)

    def _load_cache(self) -> bool:
        if not self.model_cache_path.exists():
            return False

        try:
            payload = json.loads(self.model_cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        signature = payload.get("dataset_signature", {})
        current_signature = self._dataset_signature() if self.dataset_path.exists() else None
        if payload.get("model_version") != MODEL_VERSION or signature != current_signature:
            return False

        self.vectorizer = TfidfVectorizer.from_dict(dict(payload.get("vectorizer", {})))
        self.classifier = LogisticRegressionClassifier.from_dict(dict(payload.get("classifier", {})))
        self.status = dict(payload.get("status", {}))
        self.status["model_cached"] = True
        self.trained = True
        return True

    def _save_cache(self) -> None:
        payload = {
            "model_version": MODEL_VERSION,
            "dataset_signature": self._dataset_signature(),
            "vectorizer": self.vectorizer.to_dict(),
            "classifier": self.classifier.to_dict(),
            "status": self.status,
        }
        try:
            self.model_cache_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            # Serverless runtimes (e.g. Vercel) mount the deployment
            # read-only; keep the freshly trained in-memory model and
            # just skip persisting the cache to disk.
            pass

    def _train_model(self) -> None:
        self._validate_required_file(self.dataset_path, "dataset")
        self._load_rule_resources()

        rows = read_dataset_rows(self.dataset_path)
        prepared, text_column = prepare_training_rows(
            rows,
            self.lexicon_index,
            self.lexicon_surface_index,
            self.target_index,
        )
        train_rows, test_rows = split_dataset(prepared)

        train_texts = [str(row["cleaned_text"]) for row in train_rows]
        train_labels = [int(row["label"]) for row in train_rows]
        test_texts = [str(row["cleaned_text"]) for row in test_rows]
        test_labels = [int(row["label"]) for row in test_rows]

        self.vectorizer.fit(train_texts)
        train_vectors = self.vectorizer.transform(train_texts)
        test_vectors = self.vectorizer.transform(test_texts)
        self.classifier.fit(train_vectors, train_labels, len(self.vectorizer.vocabulary))

        train_probabilities = [self.classifier.predict_probability(vector) for vector in train_vectors]
        test_probabilities = [self.classifier.predict_probability(vector) for vector in test_vectors]
        train_metrics = evaluate_predictions(train_labels, train_probabilities)
        test_metrics = evaluate_predictions(test_labels, test_probabilities)

        positive_rows = sum(int(row["label"]) for row in prepared)
        negative_rows = len(prepared) - positive_rows

        self.status = {
            "model_name": "TF-IDF + Logistic Regression",
            "rule": "Cyberbullying = HurtLex match AND target indicator or @username.",
            "text_column": text_column,
            "training_rows": len(train_rows),
            "test_rows": len(test_rows),
            "pseudo_labeled_cyberbullying": positive_rows,
            "pseudo_labeled_safe": negative_rows,
            "vocabulary_size": len(self.vectorizer.vocabulary),
            "training_accuracy": train_metrics["accuracy"],
            "test_accuracy": test_metrics["accuracy"],
            "precision": test_metrics["precision"],
            "recall": test_metrics["recall"],
            "f1_score": test_metrics["f1"],
            "model_cached": False,
        }
        self._save_cache()
        self.trained = True

    def load(self) -> None:
        if self.trained:
            return
        self._load_rule_resources()
        if self._load_cache():
            return
        self._train_model()

    def analyze_text(self, text: str) -> Dict[str, object]:
        self.load()
        preprocessed = preprocess_text(text)

        hurtlex_surface_matches_normalized = find_phrase_matches_from_tokens(
            list(preprocessed["surface_tokens"]),
            self.lexicon_surface_index,
        )
        hurtlex_lemma_matches_normalized = find_phrase_matches_from_tokens(
            list(preprocessed["hurtlex_tokens"]),
            self.lexicon_index,
        )
        hurtlex_matches_normalized = hurtlex_surface_matches_normalized or hurtlex_lemma_matches_normalized
        target_indicator_matches_normalized = find_phrase_matches_from_tokens(
            list(preprocessed["target_tokens"]),
            self.target_index,
        )
        target_matches_normalized = unique_in_order(
            target_indicator_matches_normalized + list(preprocessed["username_mentions"])
        )
        rule_triggered = bool(hurtlex_matches_normalized and target_matches_normalized)

        hurtlex_matches = recover_surface_phrase_matches(
            text,
            hurtlex_surface_matches_normalized,
            lemmatize=False,
        ) or recover_surface_phrase_matches(
            text,
            hurtlex_lemma_matches_normalized,
            lemmatize=True,
        )
        target_matches = recover_surface_phrase_matches(
            text,
            target_indicator_matches_normalized,
            lemmatize=False,
        )
        target_matches = unique_in_order(target_matches + list(preprocessed["username_mentions"]))

        cleaned_text = str(preprocessed["cleaned_text"])
        vector = self.vectorizer.transform_one(cleaned_text)
        probability = self.classifier.predict_probability(vector) if vector else 0.0

        # The Logistic Regression Class-1 probability is the single source of
        # truth for the predicted class, the displayed probability, the
        # confidence score, and the risk level - so these four values can
        # never contradict each other. HurtLex/target matches (rule_triggered
        # above) remain supporting, informational indicators only; they are
        # never used to override this prediction.
        is_cyberbullying = probability >= 0.5
        risk_score = round(probability * 100, 2)
        confidence_score = round(max(probability, 1.0 - probability), 2)

        if probability < 0.3:
            risk_level = "Low"
        elif probability < 0.7:
            risk_level = "Moderate"
        else:
            risk_level = "High"

        threshold_note = ""
        if is_cyberbullying and risk_level == "Moderate":
            threshold_note = (
                "Prediction and risk level use different thresholds: this message is "
                "classified as Cyberbullying because the probability is 0.50 or higher, "
                "while the risk level shows Moderate because the probability is below 0.70."
            )

        safer_text = (
            build_safer_rewrite(hurtlex_matches, self.hurtlex_categories)
            if is_cyberbullying
            else ""
        )

        return {
            "comment": text,
            "cleaned_text": cleaned_text,
            "label": 1 if is_cyberbullying else 0,
            "probability": probability,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "hurtlex_matches": hurtlex_matches,
            "target_matches": target_matches,
            "hurtlex_display": format_match_text(hurtlex_matches, "No offensive word detected"),
            "target_display": format_match_text(target_matches, "No target indicator detected"),
            "rule_triggered": rule_triggered,
            "threshold_note": threshold_note,
            "warning_message": "This message may be harmful. Please revise before posting." if is_cyberbullying else "",
            "safer_text": safer_text,
            "model_disclaimer": MODEL_DISCLAIMER,
            "result_text": "Potential Cyberbullying" if is_cyberbullying else "Predicted as Non-Cyberbullying",
        }

    def predict(self, comment: str) -> Dict[str, object]:
        return self.analyze_text(comment)

    def summary_text(self) -> str:
        self.load()
        return "\n".join(
            [
                f"Model: {self.status['model_name']}",
                f"Rule: {self.status['rule']}",
                f"Training rows: {self.status['training_rows']}",
                f"Test rows: {self.status['test_rows']}",
                f"Pseudo-labeled cyberbullying: {self.status['pseudo_labeled_cyberbullying']}",
                f"Pseudo-labeled safe: {self.status['pseudo_labeled_safe']}",
                f"Vocabulary size: {self.status['vocabulary_size']}",
                f"Training accuracy: {self.status['training_accuracy'] * 100:.2f}%",
                f"Test accuracy: {self.status['test_accuracy'] * 100:.2f}%",
                f"Precision: {self.status['precision'] * 100:.2f}%",
                f"Recall: {self.status['recall'] * 100:.2f}%",
                f"F1 score: {self.status['f1_score'] * 100:.2f}%",
            ]
        )
