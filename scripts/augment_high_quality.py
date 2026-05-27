#!/usr/bin/env python3
"""Generate higher-quality paraphrases using handcrafted templates and conservative substitutions.

This is deterministic and conservative — meant to improve semantic variety without noisy artifacts.
"""
import json
import random
import copy
import pathlib
import sys
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config


TEMPLATES = {
    'greeting': [
        'Hello', 'Hi', 'Hey there', 'Good to see you', 'Greetings', 'Hi, how are you?'
    ],
    'goodbye': [
        'Goodbye', 'Bye', 'See you later', 'I am signing off', 'Talk to you later', 'Shutting down'
    ],
    'thanks': [
        'Thanks', 'Thank you', 'Much appreciated', 'Thanks a lot', 'I appreciate it'
    ],
    'jokes': [
        'Tell me a joke', 'Do you know any jokes?', 'Make me laugh', 'Say something funny'
    ],
    'Identity': [
        'Who are you', 'What are you', 'Identify yourself', 'Tell me who you are'
    ],
    'datetime': [
        'What time is it', 'Tell me the time', 'What is the date today', 'What day is it'
    ],
    'whatsup': [
        'What\'s up', 'How are you doing', 'Status report', 'How is it going'
    ],
    'haha': ['Haha', 'That\'s funny', 'LOL', 'That made me laugh'],
    'programmer': ['Who made you', 'Who built you', 'Who is your creator'],
    'insult': ['That\'s rude', 'You are stupid', 'Idiot', 'Useless'],
    'activity': ['What are you doing', 'What are you up to', 'What is the system doing'],
    'exclaim': ['Awesome', 'Great', 'Nice', 'Fantastic'],
    'appreciate': ['Good bot', 'You are awesome', 'Well done'],
    'nicetty': ['Nice talking to you', 'Pleasure talking to you'],
    'no': ['No', 'Nope', 'Negative', 'Not now'],
    'greetreply': ['I am fine', 'I am good', 'Doing well, thanks'],
    'age': ['How old are you', 'What is your age', 'When were you created'],
    'capabilities': ['What can you do', 'How can you help me', 'What are your capabilities']
}


def enrich_patterns(tag, existing_patterns, target=50, rng=None):
    rng = rng or random.Random(42)
    base_templates = TEMPLATES.get(tag, [])
    generated = list(dict.fromkeys(existing_patterns)) if existing_patterns else []

    # Add template-based paraphrases first
    for t in base_templates:
        if len(generated) >= target:
            break
        generated.append(t)

    # For each existing pattern, create conservative variants
    i = 0
    while len(generated) < target and i < max(200, target * 5):
        if existing_patterns:
            base = existing_patterns[i % len(existing_patterns)]
        else:
            # fallback to template
            base = base_templates[i % len(base_templates)] if base_templates else ''
        candidates = []
        text = base.strip()

        # polite variants
        candidates.append(text)
        if not text.endswith('?'):
            candidates.append(text + '?')
        candidates.append('Please ' + text.lower())
        candidates.append(text + ', please')

        # prefix/suffix small rephrases
        if 'what time' in text.lower() or 'time' == text.lower():
            candidates += ['Could you tell me the time?', 'Do you know the current time?']
        if 'who are you' in text.lower() or 'identify' in text.lower():
            candidates += ['Tell me who you are', 'Who am I speaking to?']
        if 'help' in text.lower() or 'what can you do' in text.lower():
            candidates += ['How can you help me?', 'What are your features?']

        # small contractions / case variants
        candidates.append(text.lower())
        candidates.append(text.capitalize())

        # dedupe preserve order
        for c in candidates:
            if not c:
                continue
            if c not in generated:
                generated.append(c)
            if len(generated) >= target:
                break

        i += 1

    # Trim to target
    return generated[:target]


def augment_high_quality(intents_obj, target_per_class=50, seed=1234):
    rng = random.Random(seed)
    out = copy = copy = None
    out = {'intents': []}
    for intent in intents_obj.get('intents', []):
        tag = intent.get('tag')
        patterns = intent.get('patterns', [])
        if not patterns:
            # keep as-is (fallback/noanswer)
            out['intents'].append({
                'tag': tag,
                'patterns': patterns,
                'responses': intent.get('responses', []),
                'context': intent.get('context', [])
            })
            continue

        new_patterns = enrich_patterns(tag, patterns, target=target_per_class, rng=rng)
        out['intents'].append({
            'tag': tag,
            'patterns': new_patterns,
            'responses': intent.get('responses', []),
            'context': intent.get('context', [])
        })
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=50)
    parser.add_argument('--out', type=str, default='intents.hq_augmented.json')
    parser.add_argument('--seed', type=int, default=1234)
    args = parser.parse_args()

    with open(config.INTENTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    aug = augment_high_quality(data, target_per_class=args.target, seed=args.seed)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(aug, f, indent=2)
    print('Wrote high-quality augmented intents to', args.out)


if __name__ == '__main__':
    main()
