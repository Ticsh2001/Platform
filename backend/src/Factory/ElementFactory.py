# backend/src/Factory/ElementFactory.py
import os
import glob
import json
import importlib
import inspect
from typing import Optional, Callable, Dict, Any, List, Union

from backend.src.Core.Element import Element
from backend.src.Core.Value import ValueClass, Value, ValueStatus
from backend.src.Core.Port import Port


class ElementFactory:
    """
    Фабрика элементов с явной семантикой:
    - class_path is None → создаем базовый Element, интерпретируем in_ports/out_ports/parameters по стандарту.
    - class_path задан → создаем наследника. Ничего не интерпретируем, кроме явных тегов:
        {"__value__": {...}} → Value
        {"__port__":  {...}} → Port
      Все остальные данные передаем «как есть» (включая числа, строки, произвольные словари).
    """

    # Теги-«подсветки»
    VALUE_TAG = "$value"
    PORT_TAG = "$port"

    REQUIRED_FIELDS = {
        "name", "author", "version", "description", "category",
        "class_path", "in_ports", "out_ports", "parameters", "functions"
    }

    def __init__(self, value_classes_path: str, ports_path: str, elements_dir: str):
        # Счетчики уникальных имен
        self._element_counters: Dict[str, int] = {}

        # Загружаем конфиги
        self.value_classes_json = self._load_json(value_classes_path)
        self.ports_def = self._load_json(ports_path)
        self.element_defs = self._load_all_elements(elements_dir)

        # Кэш ValueClass по ключу "PhysicsType.ShortName"
        self.value_classes_cache: Dict[str, ValueClass] = self._load_value_classes(self.value_classes_json)

        # Метаданные для справки
        self.metadata_cache = {
            name: {k: v for k, v in cfg.items()
                   if k in ["name", "author", "version", "description", "category"]}
            for name, cfg in self.element_defs.items()
        }

    # -----------------------
    # Загрузка конфигураций
    # -----------------------
    def _load_json(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_all_elements(self, directory: str) -> Dict[str, dict]:
        elements: Dict[str, dict] = {}
        for file_path in glob.glob(os.path.join(directory, "**/*.json"), recursive=True):
            name = os.path.splitext(os.path.basename(file_path))[0]
            with open(file_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Проверим наличие обязательных полей заранее (чтобы ловить ошибки на этапе старта)
            missing = self.REQUIRED_FIELDS - set(cfg.keys())
            if missing:
                raise ValueError(f"В конфиге '{name}.json' отсутствуют обязательные поля: {sorted(missing)}")
            elements[name] = cfg
        return elements

    def _load_value_classes(self, data: dict) -> Dict[str, ValueClass]:
        """
        Формируем кэш ValueClass с ключами вида 'Thermodynamics.G'
        """
        cache: Dict[str, ValueClass] = {}
        for group_name, group_data in data.items():
            physics_type = group_data.get("physics_type", group_name)
            values = group_data.get("values", {})
            for short_name, vinfo in values.items():
                key = f"{physics_type}.{short_name}"
                cache[key] = ValueClass(
                    value_name=vinfo["value_name"],
                    physics_type=physics_type,
                    dimension=vinfo.get("dimension")
                )
        return cache

    # -----------------------
    # Импорт по dotted-path
    # -----------------------
    def _import_attr(self, dotted: Optional[str]) -> Optional[Any]:
        """
        Импортирует функцию/класс/атрибут по dotted-строке 'package.module:attr' или 'package.module.attr'.
        Допускаем оба формата, двоеточие и точку.
        """
        if not dotted:
            return None
        dotted = dotted.strip()
        if ":" in dotted:
            module_path, attr_path = dotted.split(":", 1)
        else:
            module_path, attr_path = dotted.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        # поддержка цепочки attr1.attr2...
        obj = mod
        for part in attr_path.split("."):
            obj = getattr(obj, part)
        return obj

    # -----------------------
    # Сборщики Value/Port
    # -----------------------
    def _vclass_from_key(self, key: str) -> ValueClass:
        if key not in self.value_classes_cache:
            raise ValueError(f"ValueClass '{key}' не найден. Доступные: {sorted(self.value_classes_cache.keys())}")
        return self.value_classes_cache[key]

    def _value_dict_for_port(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Преобразует конфиг величины, где value_class: 'Thermodynamics.G',
        в словарь, совместимый с Value.from_dict (требуется 'value_spec', а не 'value_class').
        """
        # допускаем alias 'name' и 'param_name'
        name = spec.get("param_name") or spec.get("name")
        if not name:
            raise ValueError("У величины отсутствует 'param_name'/'name'")

        vc_key = spec["value_class"]
        vc = self._vclass_from_key(vc_key)

        return {
            "name": name,
            "value_spec": {
                "value_name": vc.value_name,
                "physics_type": vc.physics_type,
                "dimension": vc.dimension
            },
            "value": spec.get("value"),
            "description": spec.get("description", ""),
            "status": spec.get("status", "unknown"),
            "store_prev": spec.get("store_prev", True),
            "min_value": spec.get("min_value"),
            "max_value": spec.get("max_value")
        }

    def _build_value_object(self, spec: Dict[str, Any]) -> Value:
        """
        Создает объект Value из записи с 'value_class' (напр. {"param_name":"G", "value_class":"Thermodynamics.G"})
        """
        name = spec.get("param_name") or spec.get("name")
        if not name:
            raise ValueError("У величины отсутствует 'param_name'/'name'")
        vc = self._vclass_from_key(spec["value_class"])
        return Value(
            name=name,
            value_spec=vc,
            value=spec.get("value"),
            description=spec.get("description", ""),
            status=ValueStatus.from_input(spec.get("status", "unknown")),
            min_value=spec.get("min_value"),
            max_value=spec.get("max_value"),
        )

    def _port_dict_for_element(self, port_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Строит словарь порта для базового Element (Port.from_dict).
        Источники:
          - "use_port": имя шаблона из ports.json
          - "values": список величин с value_class
        """
        if "name" not in port_spec:
            raise ValueError("У порта отсутствует поле 'name'")

        values_cfg: List[Dict[str, Any]] = []

        if "use_port" in port_spec:
            tpl_name = port_spec["use_port"]
            if tpl_name not in self.ports_def:
                raise ValueError(f"Шаблон порта '{tpl_name}' не найден")
            for v in self.ports_def[tpl_name].get("values", []):
                values_cfg.append(self._value_dict_for_port(v))
        elif "values" in port_spec:
            for v in port_spec["values"]:
                values_cfg.append(self._value_dict_for_port(v))
        else:
            raise ValueError("Порт должен содержать 'use_port' или 'values'")

        return {
            "name": port_spec["name"],
            "values": values_cfg
        }

    def _port_object_for_descendant(self, port_spec: Dict[str, Any]) -> Port:
        """
        Создает объект Port для передачи в конструктор наследника по тем же правилам,
        что и _port_dict_for_element, но возвращает уже Port.
        """
        name = port_spec.get("name", "port")
        values: List[Value] = []
        if "use_port" in port_spec:
            tpl_name = port_spec["use_port"]
            if tpl_name not in self.ports_def:
                raise ValueError(f"Шаблон порта '{tpl_name}' не найден")
            for v in self.ports_def[tpl_name].get("values", []):
                values.append(self._build_value_object(v))
        elif "values" in port_spec:
            for v in port_spec["values"]:
                values.append(self._build_value_object(v))
        else:
            raise ValueError("Порт должен содержать 'use_port' или 'values'")
        return Port(name, *values)

    # -----------------------
    # Рекурсивный разбор структур с тегами
    # -----------------------
    def _transform_with_tags(self, node: Any, to_objects: bool) -> Any:
        """
        Рекурсивно обходит структуры и заменяет подписи-теги на реальные объекты.
        to_objects=True  → создаем Port/Value объекты (для наследников)
        to_objects=False → создаем словари для Port.from_dict/Value.from_dict (для базового Element)
        """
        if isinstance(node, dict):
            # Срабатывает при явной подсветке
            if self.VALUE_TAG in node and len(node) == 1:
                spec = node[self.VALUE_TAG]
                return self._build_value_object(spec) if to_objects else self._value_dict_for_port(spec)

            if self.PORT_TAG in node and len(node) == 1:
                spec = node[self.PORT_TAG]
                return self._port_object_for_descendant(spec) if to_objects else self._port_dict_for_element(spec)

            # Обычный словарь: обходим ключи
            return {k: self._transform_with_tags(v, to_objects) for k, v in node.items()}

        if isinstance(node, list):
            return [self._transform_with_tags(v, to_objects) for v in node]

        if isinstance(node, tuple):
            return tuple(self._transform_with_tags(v, to_objects) for v in node)

        # Базовые типы — как есть
        return node

    # -----------------------
    # Сборка аргументов и создание элементов
    # -----------------------
    def _unique_instance_name(self, base_name: str) -> str:
        self._element_counters[base_name] = self._element_counters.get(base_name, 0) + 1
        return f"{base_name} #{self._element_counters[base_name]}"

    def _filter_kwargs_for_constructor(self, cls, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Оставляет только те kwargs, которые реально есть в сигнатуре конструктора класса.
        """
        sig = inspect.signature(cls.__init__)
        accepted = set(sig.parameters.keys()) - {"self"}
        return {k: v for k, v in kwargs.items() if k in accepted}

    def create_element(self, element_key: str) -> Element:
        """
        Создает экземпляр по имени файла конфигурации (без .json).
        """
        if element_key not in self.element_defs:
            raise ValueError(f"Элемент '{element_key}' не зарегистрирован")
        cfg = self.element_defs[element_key]

        # Имя экземпляра
        unique_name = self._unique_instance_name(cfg["name"])

        # Функции
        funcs = cfg.get("functions", {}) or {}
        calc_func = self._import_attr(funcs.get("calculate_func"))
        upd_func = self._import_attr(funcs.get("update_int_conn_func"))
        setup_func = self._import_attr(funcs.get("setup_func"))

        # Базовый Element
        if cfg.get("class_path") is None:
            in_ports_cfg = cfg.get("in_ports", [])
            out_ports_cfg = cfg.get("out_ports", [])
            params_cfg = cfg.get("parameters", [])

            # Собираем словари для Port.from_dict/Value.from_dict
            in_ports = [self._port_dict_for_element(p) for p in in_ports_cfg]
            out_ports = [self._port_dict_for_element(p) for p in out_ports_cfg]
            parameters = [self._value_dict_for_port(p) for p in params_cfg]

            return Element(
                name=unique_name,
                description=cfg.get("description", ""),
                in_ports=in_ports,
                out_ports=out_ports,
                parameters=parameters,
                calculate_func=calc_func,
                update_int_conn_func=upd_func,
                setup_func=setup_func
            )

        # Наследник от Element
        # Импортируем класс
        element_cls = self._import_attr(cfg["class_path"])
        if not inspect.isclass(element_cls):
            raise TypeError(f"'class_path' должен указывать на класс. Получено: {element_cls}")

        # Базовые предлагаемые аргументы (многие наследники их поддерживают)
        raw_kwargs: Dict[str, Any] = {
            "name": unique_name,
            "description": cfg.get("description", ""),
        }

        # Поля, которые могут быть как «сырыми», так и с тэгами
        raw_kwargs["in_ports"] = self._transform_with_tags(cfg.get("in_ports", []), to_objects=True)
        raw_kwargs["out_ports"] = self._transform_with_tags(cfg.get("out_ports", []), to_objects=True)
        raw_kwargs["parameters"] = self._transform_with_tags(cfg.get("parameters", []), to_objects=True)

        # Передаем функции, если наследник их принимает
        raw_kwargs["calculate_func"] = calc_func
        raw_kwargs["update_int_conn_func"] = upd_func
        raw_kwargs["setup_func"] = setup_func

        # Передаем дополнительные поля (после преобразования тэгов)
        reserved = {
            "name", "author", "version", "description", "category",
            "class_path", "in_ports", "out_ports", "parameters", "functions"
        }
        for k, v in cfg.items():
            if k in reserved:
                continue
            raw_kwargs[k] = self._transform_with_tags(v, to_objects=True)

        # Оставляем только поддерживаемые конструктором аргументы
        ctor_kwargs = self._filter_kwargs_for_constructor(element_cls, raw_kwargs)

        return element_cls(**ctor_kwargs)

    # -----------------------
    # Инфо-методы
    # -----------------------
    def list_elements(self) -> List[str]:
        return list(self.element_defs.keys())

    def list_ports(self) -> List[str]:
        return list(self.ports_def.keys())

    def list_values(self) -> List[str]:
        return list(self.value_classes_cache.keys())

    def get_metadata(self, element_name: str) -> Dict[str, Any]:
        return self.metadata_cache.get(element_name, {})

    def summary(self) -> str:
        lines = ["=== Value Classes ==="]
        for vc in sorted(self.value_classes_cache.keys()):
            lines.append(f"  {vc}")
        lines.append("\n=== Ports ===")
        for p in sorted(self.ports_def.keys()):
            lines.append(f"  {p}")
        lines.append("\n=== Elements ===")
        for e in sorted(self.element_defs.keys()):
            meta = self.metadata_cache[e]
            lines.append(f"  {meta['name']} (v{meta['version']} by {meta['author']})")
        return "\n".join(lines)
    

