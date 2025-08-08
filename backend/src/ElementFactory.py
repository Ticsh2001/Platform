import json
import importlib
from typing import Callable, Optional, Dict, Any, List
from Value import Value, ValueClass, ValueStatus
from Port import Port
from Element import Element

class ElementFactory:
    def __init__(self, value_classes_path: str, ports_path: str, elements_path: str):
        self.value_classes = self._load_json(value_classes_path)
        self.ports_def = self._load_json(ports_path)
        self.element_defs = self._load_json(elements_path)

        self.value_classes_cache: Dict[str, ValueClass] = {
            k: ValueClass(**v) for k, v in self.value_classes.items()
        }

    def _load_json(self, path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _import_func(self, full_path: Optional[str]) -> Optional[Callable]:
        if not full_path:
            return None
        module_path, func_name = full_path.rsplit('.', 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, func_name)

    def _build_value(self, val_spec: Dict[str, Any]) -> Value:
        """Создание Value из описания параметра"""
        vc_name = val_spec["value_class"]
        if vc_name not in self.value_classes_cache:
            raise ValueError(f"ValueClass '{vc_name}' не зарегистрирован")
        vc = self.value_classes_cache[vc_name]
        return Value(
            name=val_spec["param_name"],
            value_spec=vc,
            value=val_spec.get("value"),
            description=val_spec.get("description", ""),
            status=ValueStatus.from_input(val_spec.get("status", "unknown")),
            min_value=val_spec.get("min_value"),
            max_value=val_spec.get("max_value")
        )

    def _build_port(self, port_spec: Dict[str, Any]) -> Port:
        """Создаёт порт — из шаблона или вручную"""
        values = []
        if "use_port" in port_spec:
            template_name = port_spec["use_port"]
            if template_name not in self.ports_def:
                raise ValueError(f"Шаблон порта '{template_name}' не найден")
            for v in self.ports_def[template_name]["values"]:
                values.append(self._build_value(v))
        elif "values" in port_spec:
            for v in port_spec["values"]:
                values.append(self._build_value(v))
        else:
            raise ValueError("В порт не добавлены параметры и не указан use_port")
        return Port(port_spec["name"], *values)

    def _build_ports(self, ports_def: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._build_port(p).as_dict() for p in ports_def]

    def _build_parameters(self, params_def: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._build_value(p).to_dict() for p in params_def]

    def create_element(self, element_name: str) -> Element:
        if element_name not in self.element_defs:
            raise ValueError(f"Элемент '{element_name}' не зарегистрирован")

        cfg = self.element_defs[element_name]
        element_cls = Element

        if "class_path" in cfg and cfg["class_path"]:
            module_path, cls_name = cfg["class_path"].rsplit('.', 1)
            mod = importlib.import_module(module_path)
            element_cls = getattr(mod, cls_name)

        in_ports = self._build_ports(cfg.get("in_ports", []))
        out_ports = self._build_ports(cfg.get("out_ports", []))
        parameters = self._build_parameters(cfg.get("parameters", []))

        calc_func = self._import_func(cfg.get("functions", {}).get("calculate_func"))
        update_func = self._import_func(cfg.get("functions", {}).get("update_int_conn_func"))
        setup_func = self._import_func(cfg.get("functions", {}).get("setup_func"))

        return element_cls(
            name=element_name,
            description=cfg.get("description", ""),
            in_ports=in_ports,
            out_ports=out_ports,
            parameters=parameters,
            calculate_func=calc_func,
            update_int_conn_func=update_func,
            setup_func=setup_func
        )