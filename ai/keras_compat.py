import logging

logger = logging.getLogger(__name__)


def _patch_layer_from_config(layer_cls):
    if getattr(layer_cls, "_meero_quantization_config_patch", False):
        return

    original_from_config = layer_cls.from_config

    @classmethod
    def from_config_without_quantization(cls, config):
        cleaned = dict(config)
        cleaned.pop("quantization_config", None)
        return original_from_config(cleaned)

    layer_cls.from_config = from_config_without_quantization
    layer_cls._meero_quantization_config_patch = True


def _patch_quantization_config_layers():
    try:
        from tensorflow.keras.layers import Dense, Embedding
    except Exception:
        logger.exception("Unable to import Keras layers for compatibility patch")
        return

    for layer_cls in (Dense, Embedding):
        _patch_layer_from_config(layer_cls)


def load_model_compat(model_path):
    from tensorflow.keras.models import load_model

    try:
        return load_model(model_path)
    except TypeError as exc:
        if "quantization_config" not in str(exc):
            raise
        logger.warning(
            "Retrying Keras model load after applying legacy quantization_config patch"
        )
        _patch_quantization_config_layers()
        return load_model(model_path)
