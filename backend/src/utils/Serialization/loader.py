# backend/src/utils/persistence/loader.py
from __future__ import annotations
from typing import Any, Dict, Iterable
import importlib
import inspect
import json
from importlib import metadata as importlib_metadata
from .registry import SerializerRegistry

def load_from_entry_points(registry: SerializerRegistry, group: str = "yourapp.serializers"):
    """
    Ожидается, что пакет-плагин объявит в setup.cfg/pyproject.toml:
    [project.entry-points."yourapp.serializers"]
    keras = mypkg.keras_serializer:KerasModelSerializer
    """
    try:
        eps = importlib_metadata.entry_points()
        # API разный у py3.10/3.11 — приводим к единому
        entries = eps.select(group=group) if hasattr(eps, "select") else eps.get(group, [])
    except Exception:
        entries = []
    for ep in entries:
        obj = ep.load()  # может быть класс или уже инстанс
        instance = obj() if inspect.isclass(obj) else obj
        registry.register(instance)

def load_from_config(registry: SerializerRegistry, config_path: str):
    """
    Формат JSON:
    {
      "serializers": [
        {"module": "mypkg.keras_serializer", "object": "KerasModelSerializer"},
        {"module": "mypkg.numpy_serializer", "object": "make_numpy_serializer"}  # может быть фабрика
      ]
    }
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for item in cfg.get("serializers", []):
        module = importlib.import_module(item["module"])
        obj = getattr(module, item["object"])
        instance = obj() if inspect.isclass(obj) else obj
        registry.register(instance)

def load_from_env(registry: SerializerRegistry, env_var: str = "YOURAPP_SERIALIZERS"):
    """
    Переменная окружения вида:
    YOURAPP_SERIALIZERS="pkg.mod:ObjA,other.mod:factory_func"
    """
    import os
    spec = os.getenv(env_var)
    if not spec:
        return
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        mod_name, obj_name = token.split(":", 1)
        module = importlib.import_module(mod_name)
        obj = getattr(module, obj_name)
        instance = obj() if inspect.isclass(obj) else obj
        registry.register(instance)

def init_serializers(registry: SerializerRegistry, *, config_path: str | None = None, use_entry_points: bool = True, use_env: bool = True):
    if use_entry_points:
        load_from_entry_points(registry)
    if config_path:
        load_from_config(registry, config_path)
    if use_env:
        load_from_env(registry)
    registry.freeze()  # фиксируем набор на время работы