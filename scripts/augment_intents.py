#!/usr/bin/env python3
import json
import random
import copy
import pathlib
import sys
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config


SYNONYMS = {
    "hi": ["hello", "hey", "hiya"],
    "hello": ["hi", "hey"],
    "thanks": ["thank you", "thx"],
    "thank": ["thanks"],
    "bye": ["goodbye", "see you"],
    "shutdown": ["power off", "turn off"],
    "time": ["what time is it", "current time"],
    "date": ["what is the date", "today's date"],
    "who": ["identify", "who are you"],
    "help": ["assist", "what can you do"],
}


def augment_pattern(pattern, rng):
    words = pattern.split()
    variants = []

    # simple replacements
    for i, w in enumerate(words):
        lw = w.strip('?,.!').lower()
        if lw in SYNONYMS:
            for syn in SYNONYMS[lw]:
                new = words.copy()
                new[i] = syn
                variants.append(' '.join(new))

    # small paraphrases: add polite prefix/suffix
    variants.append(pattern)
    variants.append(pattern + '?')
    variants.append('please ' + pattern.lower())
    variants.append(pattern.lower() + ', please')

    # dedupe and choose one random variant
    variants = [v for v in dict.fromkeys(variants) if v]
    rng.shuffle(variants)
    return variants


def augment_intents(intents, target_per_class=30, seed=42):
    rng = random.Random(seed)
    new_intents = copy.deepcopy(intents)
    for intent in new_intents['intents']:
        patterns = intent.get('patterns', [])
        if not patterns:
            # skip augmentation for empty-pattern intents (fallbacks)
            continue
        generated = set(patterns)
        i = 0
        # cycle existing patterns and make variants until target reached
        while len(generated) < target_per_class and i < target_per_class * 5:
            base = patterns[i % len(patterns)]
            for v in augment_pattern(base, rng):
                if len(generated) >= target_per_class:
                    break
                generated.add(v)
            i += 1
        intent['patterns'] = list(generated)
    return new_intents


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=30, help='Target patterns per class')
    parser.add_argument('--out', type=str, default='intents.augmented.json')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    with open(config.INTENTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    aug = augment_intents(data, target_per_class=args.target, seed=args.seed)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(aug, f, indent=2)
    print('Wrote augmented intents to', args.out)


if __name__ == '__main__':
    main()
