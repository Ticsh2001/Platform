from backend.src.Core.Value import Value, ValueStatus
import uuid
from typing import Dict, Iterator, List, Optional, Tuple, Union, Any, Collection, Type
from backend.src.Core.ObjectRepository import ObjectRepository


class Port:
    # Защищенные атрибуты, которые нельзя перезаписать
    PROTECTED_ATTRS = ['_name', '_values', 'PROTECTED_ATTRS']

    def __init__(self, name: str, *values: Value):
        # Безопасная инициализация атрибутов
        super().__setattr__('_name', name)
        super().__setattr__('_values', ObjectRepository(rep_type='value', postfix=name))

        # Добавление начальных значений
        for value in values:
            self.add_value(value)

    def add_value(self, value: Value, type_check: Optional[Type] = None):
        """Добавление величины в порт с проверкой типа"""
        # Проверка типа значения
        if type_check and not isinstance(value.value, type_check):
            raise TypeError(f"Ожидается тип {type_check}, получен {type(value.value)}")

        # Регистрация величины (используется value.name как base_name)
        self._values.register(value)

    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, new_name: str):
        self._name = new_name

    def __iter__(self) -> Iterator[Tuple[uuid.UUID, Value]]:
        return iter(self._values.items())

    def __getitem__(self, key: Union[uuid.UUID, str, int]) -> Value:
        return self._values[key]

    def __getattr__(self, name: str) -> Tuple[Any, ValueStatus]:
        """Доступ к величине по имени атрибута"""
        # Защита системных атрибутов
        if name in self.PROTECTED_ATTRS:
            return super().__getattribute__(name)

        if name in self._values:
            value = self._values[name]
            return value.value, value.status
        raise AttributeError(f"Порт '{self.name}' не содержит величины '{name}'")

    def __setattr__(self, name: str, value: Tuple[Any, Union[ValueStatus, str]]):
        """Установка значения величины"""
        # Защита системных атрибутов
        if name in self.PROTECTED_ATTRS:
            super().__setattr__(name, value)
            return

        if name not in self._values:
            raise AttributeError(f"Величина '{name}' не найдена в порте")

        value_obj = self._values[name]
        new_val, new_status = value

        # Преобразование строкового статуса
        if isinstance(new_status, str):
            new_status = ValueStatus.from_input(new_status)

        value_obj.update(new_val, new_status)

    def get_value(self, identifier: Union[str, uuid.UUID]) -> Optional[Value]:
        return self._values.get_by_name(identifier) if isinstance(identifier, str) else self._values.get_by_id(
            identifier)
    
    def get_value_state(self, name: str) -> Tuple[Any, ValueStatus]:
        return self.__getattr__(name)

    def get_value_state(self, identifier: Union[str, uuid.UUID]) -> Optional[Tuple[Any, ValueStatus]]:
        value = self.get_value(identifier)
        return (value.value, value.status) if value else None

    def set_value_state(self, identifier: Union[str, uuid.UUID], value: Any, status: Union[ValueStatus, str]):
        value_obj = self.get_value(identifier)
        if not value_obj:
            raise AttributeError(f"Величина '{identifier}' не найдена")
        value_obj.update(value, ValueStatus.from_input(status))

    def __contains__(self, value: Union[str, uuid.UUID, Value]) -> bool:
        return value in self._values

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"Port(name={self.name}, values={list(self._values.registered_base_names)})"

    def list_by_status(self, status: Union[ValueStatus, str, Collection[Union[ValueStatus, str]]]) -> List[str]:
        # Преобразование в множество статусов
        statuses = {status} if not isinstance(status, Collection) or isinstance(status, str) else status
        status_set = {ValueStatus.from_input(s) for s in statuses}

        return [name for name in self._values.registered_base_names
                if self._values[name].status in status_set]

    def list_known(self) -> List[str]:
        return self.list_by_status([s for s in ValueStatus if s != ValueStatus.UNKNOWN])

    def list_unknown(self) -> List[str]:
        return self.list_by_status(ValueStatus.UNKNOWN)

    @property
    def is_calculated(self) -> bool:
        return all(value.status != ValueStatus.UNKNOWN for _, value in self._values.items())

    def reset(self, reset_fixed: bool = False):
        for _, value in self._values.items():
            if value.status in (ValueStatus.CALCULATED, ValueStatus.DEPEND) or \
                    (reset_fixed and value.status == ValueStatus.FIXED):
                value.update(None, ValueStatus.UNKNOWN)

    def reset_by_names(self, names: List[str], reset_fixed: bool = False):
        for name in names:
            if name in self._values:
                value = self._values[name]
                if value.status in (ValueStatus.CALCULATED, ValueStatus.DEPEND) or \
                        (reset_fixed and value.status == ValueStatus.FIXED):
                    value.update(None, ValueStatus.UNKNOWN)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Port):
            return NotImplemented
        return (self.name == other.name and
                {v.name: v.dimension for _, v in self._values.items()} ==
                {v.name: v.dimension for _, v in other._values.items()})

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    # Новые методы
    def update_bulk(self, updates: Dict[str, Tuple[Any, Union[ValueStatus, str]]]):
        """Массовое обновление значений"""
        for name, (val, status) in updates.items():
            self.set_value_state(name, val, status)

    def get_all(self) -> Dict[str, Tuple[Any, ValueStatus]]:
        """Получение всех значений порта"""
        return {name: self.__getattr__(name) for name in self._values.registered_base_names}

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация порта в словарь"""
        return {
            "name": self.name,
            "values": [value.to_dict() for _, value in self._values.items()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Port":
        """Десериализация порта из словаря"""
        port = cls(data["name"])
        for value_data in data["values"]:
            port.add_value(Value.from_dict(value_data))
        return port