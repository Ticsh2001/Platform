# backend/src/utils/element_io.py
from typing import Any, Dict, List, Optional, Tuple, Union
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import ValueStatus, Value, ValueClass
from backend.src.Core.Port import Port
from contextlib import contextmanager

KNOWN_STATUSES = {ValueStatus.CALCULATED, ValueStatus.FIXED, ValueStatus.DEPEND}

class ValueProxy:
    def __init__(self, value_obj: Value):
        self._v = value_obj

    def get(self) -> Any:
        return self._v.value

    def set(self, value: Any, status: ValueStatus = ValueStatus.CALCULATED):
        self._v.update(value, status)
        return self

    def get_or(self, default: Any = None) -> Any:
        return self._v.value if self.is_known() else default

    def status(self) -> ValueStatus:
        return self._v.status

    def is_known(self) -> bool:
        return self._v.status in KNOWN_STATUSES

    def is_calculated(self) -> bool:
        return self._v.status == ValueStatus.CALCULATED

    def is_depend(self) -> bool:
        return self._v.status == ValueStatus.DEPEND

    def is_fixed(self) -> bool:
        return self._v.status == ValueStatus.FIXED

    def spec(self) -> ValueClass:
        return self._v.value_spec

    def meta(self):
        return self._v.to_dict(include_private=True)

    @property
    def raw(self) -> Value:
        return self._v


class PortProxy:
    def __init__(self, port_obj: Port):
        self._p = port_obj
        self._values_by_name: Dict[str, Value] = {}
        # Предполагается, что итерация по порту даёт (value_id, Value)
        for _, v in self._p:
            self._values_by_name[v.name] = v

    def __getattr__(self, value_name: str) -> ValueProxy:
        v = self._values_by_name.get(value_name)
        if v is None:
            raise AttributeError(f"Value '{value_name}' не найден в порту '{self._p.name}'")
        return ValueProxy(v)

    def __getitem__(self, value_name: str) -> ValueProxy:
        return self.__getattr__(value_name)

    def __contains__(self, item: str):
        return self.exists(item)

    def get(self, value_name: str) -> Any:
        return self[value_name].get()

    def set(self, value_name: str, value: Any, status: ValueStatus = ValueStatus.CALCULATED):
        return self[value_name].set(value, status)

    def is_known(self, value_name: str) -> bool:
        v = self._values_by_name.get(value_name)
        return v is not None and v.status in KNOWN_STATUSES

    def exists(self, value_name: str) -> bool:
        return value_name in self._values_by_name

    def by_spec(self, spec: ValueClass) -> List[ValueProxy]:
        return [ValueProxy(v) for v in self._values_by_name.values() if v.value_spec == spec]

    def values(self) -> Dict[str, ValueProxy]:
        return {name: ValueProxy(v) for name, v in self._values_by_name.items()}

    def add(self, val: Value, raise_exception: bool = False) -> bool:
        try:
            self._p.add_value(val)
        except (ValueError, TypeError) as e:
            if raise_exception:
                raise
            return False
        else:
            self._values_by_name[val.name] = val
            return True

    def refresh(self):
        self._values_by_name.clear()
        for _, v in self._p:
            self._values_by_name[v.name] = v
        return self

    def meta(self):
        return self._p.to_dict()


    @property
    def name(self) -> str:
        return self._p.name

    @property
    def raw(self) -> Port:
        return self._p


class PortsProxy:
    def __init__(self, repo: ObjectRepository):
        self._repo = repo
        self._ports: Dict[str, PortProxy] = {}
        # Предполагается, что итерация по репозиторию портов даёт (port_id, Port)
        for _, port in repo:
            self._ports[port.name] = PortProxy(port)

    def __getattr__(self, port_name: str) -> PortProxy:
        p = self._ports.get(port_name)
        if p is None:
            raise AttributeError(f"Порт '{port_name}' не найден")
        return p

    def __getitem__(self, port_name: str) -> PortProxy:
        return self.__getattr__(port_name)

    def __iter__(self):
        return iter(self._ports.values())

    def __contains__(self, path: str):
        return self.exists(path)

    def get(self, path: str) -> Any:
        # path: "Port.Value" or "Port"
        try:
            p_name, v_name = path.split(".", 1)
            return self[p_name].get(v_name)
        except ValueError:
            return self[path]

    def set(self, path: str, value: Any, status: ValueStatus = ValueStatus.CALCULATED):
        p_name, v_name = path.split(".", 1)
        return self[p_name].set(v_name, value, status)

    def exists(self, path: str) -> bool:
        try:
            p_name, v_name = path.split(".", 1)
            p = self._ports.get(p_name)
            return p is not None and p.exists(v_name)
        except ValueError:
            p_name = path
            p = self._ports.get(p_name)
            return p is not None

    def add(self, port: Port, raise_exception: bool = False) -> bool:
        try:
            self._repo.register(port)
        except (ValueError, TypeError) as e:
            if raise_exception:
                raise
            return False
        else:
            self._ports[port.name] = PortProxy(port)
            return True

    def is_known(self, path: str) -> bool:
        try:
            p_name, v_name = path.split(".", 1)
        except ValueError:
            return False
        p = self._ports.get(p_name)
        return p is not None and p.is_known(v_name)

    def refresh(self):
        self._ports.clear()
        for _, port in self._repo:
            self._ports[port.name] = PortProxy(port)
        return self

    @property
    def raw(self):
        return self._repo


class ParamsProxy:
    def __init__(self, repo: ObjectRepository):
        self._repo = repo
        self._values_by_name: Dict[str, Value] = {}
        for _, v in repo:
            self._values_by_name[v.name] = v

    def __getattr__(self, param_name: str) -> ValueProxy:
        v = self._values_by_name.get(param_name)
        if v is None:
            raise AttributeError(f"Параметр '{param_name}' не найден")
        return ValueProxy(v)

    def __getitem__(self, param_name: str) -> ValueProxy:
        return self.__getattr__(param_name)

    def add(self, val: Value, raise_exception: bool = False) -> bool:
        try:
            self._repo.register(val)
        except (TypeError, ValueError):
            if raise_exception:
                raise
            return False
        else:
            self._values_by_name[val.name] = val
            return True

    def get(self, name: str) -> Any:
        return self[name].get()

    def set(self, name: str, value: Any, status: ValueStatus = ValueStatus.CALCULATED):
        return self[name].set(value, status)

    def is_known(self, name: str) -> bool:
        v = self._values_by_name.get(name)
        return v is not None and v.status in KNOWN_STATUSES

    def exists(self, name: str) -> bool:
        return name in self._values_by_name

    def __contains__(self, item: str):
        return self.exists(item)

    def __iter__(self):
        return iter(self._values_by_name.values())

    def refresh(self):
        self._values_by_name.clear()
        for _, v in self._repo:
            self._values_by_name[v.name] = v
        return self

    @property
    def names(self):
        return list(self._values_by_name.keys())


def requires(*,
             inputs: Optional[List[str]] = None,
             outputs: Optional[List[str]] = None,
             params: Optional[List[str]] = None,
             any_groups: Optional[List[Dict[str, List[str]]]] = None,
             on_skip=None):
    """
    Если условия не выполнены — просто пропускает выполнение функции.
    """
    def decorator(func):
        def wrapper(io: "ElementIO", *args, **kwargs):
            ok = True
            if any_groups:
                ok = io.require_any(any_groups, raise_exception=False)
            else:
                ok = io.require(inputs=inputs, outputs=outputs, params=params, raise_exception=False)
            if not ok:
                if callable(on_skip):
                    on_skip(io)
                return  # мягкий пропуск
            return func(io, *args, **kwargs)
        return wrapper
    return decorator

class ElementIO:
    """
    Высокоуровневая обёртка над репозиториями элемента.
    Позволяет удобно обращаться к входам/выходам/параметрам
    и проверять готовность данных.
    """
    def __init__(self, in_ports: ObjectRepository, out_ports: ObjectRepository, params: ObjectRepository):
        self.inputs = PortsProxy(in_ports)
        self.outputs = PortsProxy(out_ports)
        self.params = ParamsProxy(params)

    def get(self, path: str) -> Any:
        for obj in [self.inputs, self.outputs, self.params]:
            if path in obj:
                return obj.get(path)
        raise KeyError(f"Не найден путь/параметр: {path}")

    def set(self, path: str, value: Any, status: ValueStatus = ValueStatus.CALCULATED):
        for obj in [self.inputs, self.outputs, self.params]:
            if path in obj:
                return obj.set(path, value, status)
        raise KeyError(f"Не найден путь/параметр: {path}")

    def get_mul(self, paths: List[str]) -> Dict[str, Any]:
        return {path: self.get(path) for path in paths}

    def set_mul(self, paths: List[str], values: List[Any],
                statuses: Union[List[Union[str, ValueStatus]], Union[str, ValueStatus], None]):
        if isinstance(statuses, list):
            stiter = iter(statuses)
        elif statuses is None:
            status = ValueStatus.CALCULATED
        else:
            status = statuses
        for path, value in zip(paths, values):
            try:
                self.set(path, value, next(stiter))
            except ValueError:
                self.set(path, value, status)

    # Внутренние помощники для require
    @staticmethod
    def _missing_port_values(ports: PortsProxy, paths: List[str]) -> List[str]:
        missing: List[str] = []
        for p in paths or []:
            if not (ports.exists(p) and ports.is_known(p)):
                missing.append(p)
        return missing

    def require(self,
                inputs: Optional[List[str]] = None,
                outputs: Optional[List[str]] = None,
                params: Optional[List[str]] = None,
                raise_exception: bool = True) -> bool:
        """
        Проверяет, что:
          - все указанные входные значения известны (CALCULATED/FIXED),
          - все указанные выходные значения известны (редко, но возможно),
          - все указанные параметры известны.
        Возвращает True/False. Если raise_exception=True и что-то не найдено/неизвестно — кидает ValueError.
        """
        missing: List[str] = []

        miss_in = self._missing_port_values(self.inputs, inputs or [])
        if miss_in:
            missing += [f"in:{p}" for p in miss_in]

        miss_out = self._missing_port_values(self.outputs, outputs or [])
        if miss_out:
            missing += [f"out:{p}" for p in miss_out]

        miss_params: List[str] = []
        for name in params or []:
            if not (self.params.exists(name) and self.params.is_known(name)):
                miss_params.append(name)
        if miss_params:
            missing += [f"param:{n}" for n in miss_params]

        ok = (len(missing) == 0)
        if not ok and raise_exception:
            raise ValueError("Требуемые значения недоступны: " + ", ".join(missing))
        return ok

    def require_any(self,
                    groups: List[Dict[str, List[str]]],
                    raise_exception: bool = True) -> bool:
        """
        Проверяет набор альтернативных условий. Каждая группа — словарь с ключами
          'inputs', 'outputs', 'params' (любой может отсутствовать).
        Группа считается выполненной, если ВСЕ перечисленные в ней пути/параметры известны.
        Возвращает True, если выполнена хотя бы одна группа.
        """
        reasons: List[Tuple[int, List[str]]] = []
        for idx, g in enumerate(groups, start=1):
            miss: List[str] = []
            miss += [f"in:{p}" for p in self._missing_port_values(self.inputs, g.get("inputs", []))]
            miss += [f"out:{p}" for p in self._missing_port_values(self.outputs, g.get("outputs", []))]
            if "params" in g:
                miss += [f"param:{n}" for n in g["params"]
                         if not (self.params.exists(n) and self.params.is_known(n))]
            if not miss:
                return True
            reasons.append((idx, miss))

        if raise_exception:
            detail = "; ".join(f"group {i}: missing {', '.join(m)}" for i, m in reasons)
            raise ValueError("Ни одно из альтернативных условий не выполнено: " + detail)
        return False

    def check_status(self,
                     inputs: Optional[List[str]] = None,
                     outputs: Optional[List[str]] = None,
                     params: Optional[List[str]] = None) -> Dict[str, Dict[str, ValueStatus]]:
        """Возвращает статусы всех указанных значений"""
        result = {'inputs': {}, 'outputs': {}, 'params': {}}

        for path in inputs or []:
            if self.inputs.exists(path):
                try:
                    p_name, v_name = path.split(".", 1)
                    result['inputs'][path] = self.inputs[p_name][v_name].status()
                except ValueError:
                    pass

        for path in outputs or []:
            if self.outputs.exists(path):
                try:
                    p_name, v_name = path.split(".", 1)
                    result['outputs'][path] = self.outputs[p_name][v_name].status()
                except ValueError:
                    pass

        for name in params or []:
            if self.params.exists(name):
                result['params'][name] = self.params[name].status()

        return result