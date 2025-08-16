# backend/src/utils/persistence/serializers.py
from __future__ import annotations
from typing import Any, Dict, Tuple
from .registry import Serializer, DEFAULT_REGISTRY
import pathlib
import json

# Numpy
try:
    import numpy as np
except Exception:
    np = None

class NumpyArraySerializer:
    name = "numpy"
    handles = (np.ndarray,) if np is not None else tuple()

    def save(self, obj: Any, dst_dir: pathlib.Path, basename: str) -> Dict[str, Any]:
        dst_dir.mkdir(parents=True, exist_ok=True)
        npy_path = dst_dir / f"{basename}.npy"
        np.save(npy_path, obj, allow_pickle=False)
        return {"relpath": f"{basename}.npy"}

    def load(self, meta: Dict[str, Any], src_dir: pathlib.Path) -> Any:
        arr_path = src_dir / meta["relpath"]
        return np.load(arr_path, allow_pickle=False)

# TensorFlow Keras
class KerasModelSerializer:
    name = "keras"
    handles = tuple()  # зарегистрируем динамически, если TF доступен

    def __init__(self):
        try:
            import tensorflow as tf  # noqa
            self._tf = tf
            self.handles = (tf.keras.Model,)
        except Exception:
            self._tf = None
            self.handles = tuple()

    def save(self, obj: Any, dst_dir: pathlib.Path, basename: str) -> Dict[str, Any]:
        if self._tf is None:
            raise RuntimeError("TensorFlow недоступен для сохранения keras-модели")
        dst_dir.mkdir(parents=True, exist_ok=True)
        model_dir = dst_dir / basename
        obj.save(model_dir, include_optimizer=True)  # SavedModel формат
        return {"relpath": basename}

    def load(self, meta: Dict[str, Any], src_dir: pathlib.Path) -> Any:
        if self._tf is None:
            raise RuntimeError("TensorFlow недоступен для загрузки keras-модели")
        model_dir = src_dir / meta["relpath"]
        return self._tf.keras.models.load_model(model_dir)

def register_default_serializers():
    # Регистрируем, если доступны зависимости
    if np is not None:
        DEFAULT_REGISTRY.register(NumpyArraySerializer())
    # Keras — зарегистрируется, только если TF импортируется
    DEFAULT_REGISTRY.register(KerasModelSerializer())