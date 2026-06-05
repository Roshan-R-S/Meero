#!/usr/bin/env python3
"""Generate intent training augmentations from local GGUF teacher models."""
from __future__ import annotations

import copy
import json
import logging
import os
import re
from pathlib import Path
from typing import Callable, Iterable

logger = logging.getLogger(__name__)

DEFAULT_EXAMPLES_PER_MODEL = 2
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0.2


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().strip("\"'`")


def _unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        normalized = _normalize_text(item).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(_normalize_text(item))
    return unique


def _strip_wrapping_markdown(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return cleaned.strip()


def _parse_generated_examples(raw_text: str) -> list[str]:
    cleaned = _strip_wrapping_markdown(raw_text)
    if not cleaned:
        return []

    parsed_candidates: list[str] = []
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            parsed_candidates = [str(item) for item in parsed if isinstance(item, str)]
    except Exception:
        parsed_candidates = []

    if not parsed_candidates:
        for line in re.split(r"[\r\n;]+", cleaned):
            line = line.strip().lstrip("-•*")
            line = re.sub(r"^\d+[\).:-]\s*", "", line)
            if line:
                parsed_candidates.append(line)

    return _unique_preserve_order(parsed_candidates)


def _build_teacher_prompt(tag: str, seed_patterns: list[str], examples_per_model: int) -> str:
    seeds = "\n".join(f"- {pattern}" for pattern in seed_patterns)
    return (
        "You create training examples for a user-intent classifier.\n"
        "Return only a JSON array of short user utterances.\n"
        "Do not add commentary, numbering, or markdown.\n"
        "Keep the meaning aligned to the intent and make the phrasing natural.\n\n"
        f"Intent tag: {tag}\n"
        f"Examples to generate: {examples_per_model}\n"
        f"Seed utterances:\n{seeds}\n"
    )


def _load_teacher_model(model_path: Path):
    # Prefer GPT4All when available (keeps prior behavior), but fall back to
    # llama_cpp (llama-cpp-python) for model architectures that GPT4All does
    # not support (for example: qwen3). Return an object with `.generate(prompt, max_tokens, temp)`.
    if not model_path.exists():
        raise FileNotFoundError(f"Teacher model not found: {model_path}")

    model_dir = str(model_path.parent)
    model_name = model_path.name

    # Try GPT4All first
    try:
        from gpt4all import GPT4All  # type: ignore
    except Exception:
        GPT4All = None

    if GPT4All is not None:
        try:
            logger.info("Trying GPT4All for teacher model: %s", model_path)
            g = GPT4All(model_name=model_name, model_path=model_dir, allow_download=False)

            class _G4W:
                def __init__(self, impl):
                    self.impl = impl

                def generate(self, prompt, max_tokens=None, temp=None):
                    try:
                        return self.impl.generate(prompt, max_tokens=max_tokens or 256, temp=temp or 0.7)
                    except TypeError:
                        # Some GPT4All versions accept different args
                        return self.impl.generate(prompt)

            return _G4W(g)
        except Exception:
            logger.info("GPT4All could not load model %s; falling back to llama_cpp", model_name)

    # Fall back to llama_cpp
    try:
        from llama_cpp import Llama  # type: ignore
    except Exception as exc:
        raise RuntimeError("Neither gpt4all nor llama_cpp are available to run teacher models") from exc

    logger.info("Loading GGUF teacher model via llama_cpp: %s", model_path)
    llm = Llama(model_path=str(model_path))

    class _LlamaW:
        def __init__(self, impl):
            self.impl = impl

        def generate(self, prompt, max_tokens=None, temp=None):
            # llama_cpp Llama is callable and returns a dict with 'choices'
            try:
                resp = self.impl(prompt=prompt, max_tokens=(max_tokens or 256), temperature=(temp or 0.7))
                # Newer versions return {'choices': [{'text': ...}]}
                if isinstance(resp, dict) and resp.get('choices'):
                    return resp['choices'][0].get('text', '')
                # Older interfaces may return a string
                return str(resp)
            except Exception:
                # As a last resort, try a simple call
                out = self.impl(prompt)
                if isinstance(out, dict) and out.get('choices'):
                    return out['choices'][0].get('text', '')
                return str(out)

    return _LlamaW(llm)


def augment_intents_with_teachers(
    intents_obj: dict,
    teacher_model_paths: Iterable[str | os.PathLike[str]],
    examples_per_model: int = DEFAULT_EXAMPLES_PER_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    teacher_factory: Callable[[Path], object] | None = None,
) -> tuple[dict, dict]:
    """Return an augmented intents object and a small provenance manifest."""
    teacher_paths = [Path(path) for path in teacher_model_paths]
    if not teacher_paths:
        return copy.deepcopy(intents_obj), {
            "enabled": False,
            "teacher_models": [],
            "examples_added": 0,
        }

    teacher_factory = teacher_factory or _load_teacher_model
    teachers = {path: teacher_factory(path) for path in teacher_paths}

    augmented = copy.deepcopy(intents_obj)
    examples_added = 0
    intent_records = []

    for intent in augmented.get("intents", []):
        tag = intent.get("tag")
        original_patterns = _unique_preserve_order(intent.get("patterns", []))
        if not original_patterns:
            intent["patterns"] = original_patterns
            intent_records.append({"tag": tag, "added": 0, "total": len(original_patterns)})
            continue

        patterns = list(original_patterns)
        seen = {pattern.lower() for pattern in patterns}
        per_intent_added = 0
        seed_patterns = original_patterns[: min(3, len(original_patterns))]

        for teacher_path, teacher in teachers.items():
            prompt = _build_teacher_prompt(tag, seed_patterns, examples_per_model)
            try:
                raw = teacher.generate(prompt, max_tokens=max_tokens, temp=temperature)
            except TypeError:
                raw = teacher.generate(prompt)
            except Exception:
                logger.exception("Teacher generation failed for %s on tag %s", teacher_path, tag)
                continue

            for candidate in _parse_generated_examples(raw):
                normalized = candidate.lower()
                if normalized in seen:
                    continue
                if len(candidate) < 2 or len(candidate) > 160:
                    continue
                patterns.append(candidate)
                seen.add(normalized)
                per_intent_added += 1
                examples_added += 1

        intent["patterns"] = patterns
        intent_records.append({"tag": tag, "added": per_intent_added, "total": len(patterns)})

    manifest = {
        "enabled": True,
        "teacher_models": [str(path) for path in teacher_paths],
        "examples_per_model": examples_per_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "examples_added": examples_added,
        "intents": intent_records,
    }
    return augmented, manifest


def write_augmented_intents(output_path: str | os.PathLike[str], intents_obj: dict, manifest: dict) -> tuple[str, str]:
    output_path = str(output_path)
    manifest_path = f"{output_path}.manifest.json"
    Path(output_path).write_text(json.dumps(intents_obj, indent=2), encoding="utf-8")
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output_path, manifest_path