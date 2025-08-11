import os
import glob
import json
import importlib
from typing import Optional, Callable, Dict, Any, List

from backend.src.Core.Element import Element
from backend.src.Core.Value import ValueClass, Value, ValueStatus
from backend.src.Core.Port import Port



class ElementFactory:
    def __init__(self, value_classes_path: str, ports_path: str, elements_dir: str):
        # Счётчики для уникальных имён
        self._element_counters: Dict[str, int] = {}

        # Загружаем ValueClass
        self.value_classes_json = self._load_json(value_classes_path)
        self.value_classes_cache = self._load_value_classes(self.value_classes_json)

        # Загружаем шаблонные порты
        self.ports_def = self._load_json(ports_path)

        # Загружаем элементы (каждый из отдельного JSON)
        self.element_defs = self._load_all_elements(elements_dir)

        # Запоминаем метаданные отдельно
        self.metadata_cache = {
            name: {k: v for k, v in cfg.items() if k in ["name", "author", "version", "description", "category"]}
            for name, cfg in self.element_defs.items()
        }

    def _load_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_all_elements(self, directory: str):
        elements = {}
        for file_path in glob.glob(os.path.join(directory, "**/*.json"), recursive=True):
            name = os.path.splitext(os.path.basename(file_path))[0]
            with open(file_path, "r", encoding="utf-8") as f:
                elements[name] = json.load(f)
        return elements

    def _load_value_classes(self, data: dict):
        """Собираем ValueClass с уникальным ключом PhysicsType.ShortName."""
        cache = {}
        for group_name, group_data in data.items():
            physics_type = group_data.get("physics_type", group_name)
            for short_name, vinfo in group_data["values"].items():
                key = f"{physics_type}.{short_name}"
                cache[key] = ValueClass(
                    value_name=vinfo["value_name"],
                    physics_type=physics_type,
                    dimension=vinfo["dimension"]
                )
        return cache

    def _import_func(self, full_path: Optional[str]) -> Optional[Callable]:
        if not full_path:
            return None
        module_path, func_name = full_path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, func_name)

    def _build_value(self, spec: Dict[str, Any]) -> Value:
        key = spec["value_class"]
        if key not in self.value_classes_cache:
            raise ValueError(f"ValueClass '{key}' не найден")
        vc = self.value_classes_cache[key]
        return Value(
            name=spec["param_name"],
            value_spec=vc,
            value=spec.get("value"),
            status=ValueStatus.from_input(spec.get("status", "unknown")),
            min_value=spec.get("min_value"),
            max_value=spec.get("max_value")
        )

    def _build_port(self, port_spec: Dict[str, Any]) -> Port:
        values = []
        if "use_port" in port_spec:
            if port_spec["use_port"] not in self.ports_def:
                raise ValueError(f"Шаблон порта '{port_spec['use_port']}' не найден")
            for v in self.ports_def[port_spec["use_port"]]["values"]:
                values.append(self._build_value(v))
        elif "values" in port_spec:
            for v in port_spec["values"]:
                values.append(self._build_value(v))
        else:
            raise ValueError("Порт должен содержать либо 'use_port', либо 'values'")
        return Port(port_spec["name"], *values)

    def _build_ports(self, ports_def: Any) -> List[Dict[str, Any]]:
        # Если число — создаст конструктор наследника
        if isinstance(ports_def, int):
            return ports_def
        return [self._build_port(p).as_dict() for p in ports_def]

    def _build_parameters(self, params_def: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._build_value(p).to_dict() for p in params_def]

    def create_element(self, element_name: str) -> Element:
        """Создаёт экземпляр элемента по имени из конфигурации"""
        if element_name not in self.element_defs:
            raise ValueError(f"Элемент '{element_name}' не зарегистрирован")

        cfg = self.element_defs[element_name]
        element_cls = Element

        # Делаем уникальное имя
        self._element_counters[element_name] = self._element_counters.get(element_name, 0) + 1
        unique_name = f"{cfg['name']} #{self._element_counters[element_name]}"

        # Наследник от Element
        if cfg.get("class_path"):
            module_path, cls_name = cfg["class_path"].rsplit(".", 1)
            mod = importlib.import_module(module_path)
            element_cls = getattr(mod, cls_name)

            in_ports = cfg.get("in_ports", 0)
            out_ports = cfg.get("out_ports", 0)
            parameters = self._build_parameters(cfg.get("parameters", []))
        else:
            in_ports = self._build_ports(cfg.get("in_ports", []))
            out_ports = self._build_ports(cfg.get("out_ports", []))
            parameters = self._build_parameters(cfg.get("parameters", []))

        calc_func = self._import_func(cfg.get("functions", {}).get("calculate_func"))
        update_func = self._import_func(cfg.get("functions", {}).get("update_int_conn_func"))
        setup_func = self._import_func(cfg.get("functions", {}).get("setup_func"))

        return element_cls(
            name=unique_name,
            description=cfg.get("description", ""),
            in_ports=in_ports,
            out_ports=out_ports,
            parameters=parameters,
            calculate_func=calc_func,
            update_int_conn_func=update_func,
            setup_func=setup_func
        )

    # -------------------
    # Информационные методы
    # -------------------
    def list_elements(self) -> List[str]:
        return list(self.element_defs.keys())

    def list_ports(self) -> List[str]:
        return list(self.ports_def.keys())

    def list_values(self) -> List[str]:
        return list(self.value_classes_cache.keys())

    def get_metadata(self, element_name: str) -> Dict[str, Any]:
        return self.metadata_cache.get(element_name, {})

    def summary(self) -> str:
        lines = []
        lines.append("=== Value Classes ===")
        for vc in self.value_classes_cache:
            lines.append(f"  {vc}")
        lines.append("\n=== Ports ===")
        for p in self.ports_def:
            lines.append(f"  {p}")
        lines.append("\n=== Elements ===")
        for e in self.element_defs:
            meta = self.metadata_cache[e]
            lines.append(f"  {meta['name']} (v{meta['version']} by {meta['author']})")
        return "\n".join(lines)