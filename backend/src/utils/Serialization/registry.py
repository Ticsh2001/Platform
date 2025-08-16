# backend/src/utils/persistence/registry.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Type, Iterable
import threading

class Serializer(Protocol):
    name: str                   # уникальный идентификатор ("keras", "numpy", "scipy_interp1d")
    handles: tuple[Type, ...]   # какие типы сериализуем
    format_version: str         # версия формата внешнего представления

    def save(self, obj: Any, dst_dir, basename: str) -> Dict[str, Any]: ...
    def load(self, meta: Dict[str, Any], src_dir) -> Any: ...

@dataclass
class ExternalRef:
    type_name: str
    version: str
    meta: Dict[str, Any]
    def to_dict(self) -> Dict[str, Any]:
        return {"__external__": {"type": self.type_name, "version": self.version, "meta": self.meta}}
    @staticmethod
    def is_external(obj: Any) -> bool:
        return isinstance(obj, dict) and "__external__" in obj
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ExternalRef":
        e = d["__external__"]
        return ExternalRef(e["type"], e.get("version", "1"), e["meta"])

class SerializerRegistry:
    def __init__(self):
        self._by_name: Dict[str, Serializer] = {}
        self._by_type: Dict[Type, Serializer] = {}
        self._frozen = False
        self._lock = threading.RLock()

    def register(self, s: Serializer, override: bool = False):
        with self._lock:
            if self._frozen and not override:
                raise RuntimeError("Registry is frozen; cannot register new serializers")
            if not override and s.name in self._by_name:
                raise ValueError(f"Serializer with name '{s.name}' already registered")
            self._by_name[s.name] = s
            # по типам
            for t in s.handles:
                self._by_type[t] = s

    def get_by_name(self, name: str) -> Optional[Serializer]:
        return self._by_name.get(name)

    def find_for_object(self, obj: Any) -> Optional[Serializer]:
        t = type(obj)
        if t in self._by_type:
            return self._by_type[t]
        for base in t.__mro__[1:]:
            if base in self._by_type:
                return self._by_type[base]
        return None

    def freeze(self):
        with self._lock:
            self._frozen = True

    def list_serializers(self) -> Iterable[str]:
        return tuple(self._by_name.keys())

DEFAULT_REGISTRY = SerializerRegistry()