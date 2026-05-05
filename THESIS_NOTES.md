# Thesis Notes For Cyberbullying Detection Project

## Current project status

- The system is using Python right now.
- The interface is launched by [run_dashboard.ps1](/c:/xampp/htdocs/cyberbullying/run_dashboard.ps1).
- The main app is [app.py](/c:/xampp/htdocs/cyberbullying/app.py).
- The detection logic is in [pipeline.py](/c:/xampp/htdocs/cyberbullying/cyberbullying_app/pipeline.py).
- The current method is rule-based:
  - detect at least one HurtLex word
  - detect at least one target indicator
  - only then label the text as cyberbullying

## What is already good

- Clear problem domain: cyberbullying detection on Twitter comments.
- Clear rule for classification.
- Uses a known offensive lexicon: HurtLex.
- Uses target indicators to reduce false positives.
- Has a working interface for demonstration.

## What is still missing in the thesis

### 1. Clear research objectives

You should state 2-4 objectives clearly. Example:

1. To identify offensive words in Twitter text using the HurtLex lexicon.
2. To identify whether abusive language is directed at a target using target indicators.
3. To develop a Python-based interface for cyberbullying detection.
4. To evaluate the effectiveness of the proposed rule-based approach.

### 2. Research questions

You should include questions such as:

1. Can HurtLex and target indicators be combined to detect cyberbullying in Twitter comments?
2. Does checking both offensive words and target indicators reduce false detection?
3. How effective is the proposed rule-based method for cyberbullying detection?

### 3. System architecture / framework

You should add a figure or flow like this:

1. User enters tweet text.
2. Text is cleaned and normalized.
3. System checks HurtLex matches.
4. System checks target indicator matches.
5. If both are found, label = cyberbullying.
6. Result is displayed in the interface.

### 4. Methodology details

This part is important and often missing. Explain:

- Data source:
  - Andrew Tate Twitter cyberbullying dataset
- Lexicon source:
  - HurtLex English TSV file
- Target indicators source:
  - manually prepared target indicator list
- Text preprocessing:
  - lowercase conversion
  - URL removal
  - mention normalization
  - symbol and number removal
  - whitespace normalization
- Detection rule:
  - cyberbullying = offensive term + directed target

### 5. Pseudocode or algorithm

Add a simple algorithm in the thesis:

```text
Input: tweet text
Clean the text
Check whether any HurtLex word exists
Check whether any target indicator exists
If HurtLex match = true and target indicator match = true
    Label as Cyberbullying
Else
    Label as Not Cyberbullying
End If
Output: classification result
```

### 6. Evaluation section

Right now your app is rule-based, but your thesis still needs evaluation.
You should report:

- total dataset size
- number of cyberbullying tweets
- number of non-cyberbullying tweets
- several correct detection examples
- several incorrect detection examples
- limitations of the method

If your supervisor expects classification metrics, you should also report:

- accuracy
- precision
- recall
- F1-score

### 7. Discussion of limitations

This is usually missing in student theses. You should include:

- The method depends on the quality of HurtLex.
- Some offensive tweets may not contain explicit HurtLex words.
- Some target indicators may be ambiguous.
- Sarcasm and context are difficult to detect.
- The method may miss indirect cyberbullying.

### 8. Future work

Add a short future work section:

- combine lexicon rules with machine learning
- use larger Twitter datasets
- support multilingual detection
- add severity scoring
- detect implicit harassment and sarcasm

## What is still missing in the system

These are the most useful things to add next:

1. A small explanation section showing why the tweet was detected.
   Status: already added in the interface.
2. A results history table so you can show multiple tested tweets during demo.
3. Export results to CSV for thesis evidence.
4. A flowchart image in the report.
5. A test case table in the thesis.

## Ready-to-use methodology paragraph

You can adapt this in your Chapter 3:

> This project uses a rule-based approach to detect cyberbullying in Twitter text. First, the input text is normalized through lowercasing, URL removal, mention normalization, and punctuation cleaning. Next, the system checks whether the text contains any offensive word listed in the HurtLex English lexicon. The system also checks whether the tweet contains a target indicator such as second-person pronouns or direct user mentions. A tweet is classified as cyberbullying only when both conditions are satisfied: the presence of an offensive expression and the presence of a directed target. This rule is intended to reduce false positives by distinguishing general profanity from targeted abusive language.

## Ready-to-use system description paragraph

> The developed system is implemented in Python and provides a simple user interface for tweet analysis. Users enter a tweet into the text area, and the system processes the text to determine whether it contains cyberbullying. The output shows the final classification result together with the matched HurtLex word and the matched target indicator. This makes the decision process more transparent and easier to explain during system demonstration.

## Ready-to-use limitation paragraph

> Although the proposed rule-based method is simple and interpretable, it has several limitations. The detection performance depends heavily on the completeness of the HurtLex lexicon and the target indicator list. Tweets containing sarcasm, indirect insults, or context-dependent harassment may not be detected correctly. In addition, some words may be offensive in one context but harmless in another, which can affect classification accuracy.

## Best next additions for your thesis submission

If you want the strongest improvement fast, do these next:

1. Add a results history table in the interface.
2. Add export-to-CSV for tested tweets.
3. Add a flowchart and architecture diagram to the thesis.
4. Add a small evaluation table with sample true positives, false positives, true negatives, and false negatives.
