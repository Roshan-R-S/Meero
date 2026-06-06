"""AI package public exports.

Keep package-level exports lazy so optional backends such as TensorFlow and
GPT4All do not break unrelated imports.
"""

from importlib import import_module

_EXPORTS = {
    "IntentCase": ("ai.intent_evaluator", "IntentCase"),
    "classify_action_intent": ("ai.intent_evaluator", "classify_action_intent"),
    "evaluate_cases": ("ai.intent_evaluator", "evaluate_cases"),
    "load_cases": ("ai.intent_evaluator", "load_cases"),
    "LLMEngine": ("ai.llm_engine", "LLMEngine"),
    "NeuralNet": ("ai.neural_net", "NeuralNet"),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
