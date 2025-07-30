from Value import Value, ValueStatus
import uuid
from typing import Dict, Iterator, List, Optional, Tuple, Union, Any, Collection
from enum import Enum, auto
from ObjectRepository import ObjectRepository


class Port:
    def __init__(self, name: str, prefix=None, *values: Value):
        """
        Инициализация порта

        :param name: Имя порта (неизменяемое)
        :param values: Объекты Value, принадлежащие порту
        """
        self._name = name
        self._values = ObjectRepository(rep_type='value', prefix=prefix)
        for value in values:
            self.add_value(value)

    def add_value(self, value: Value):
        """Добавление величины в порт с проверкой уникальности"""
        if not isinstance(value, Value):
            raise TypeError("Можно добавлять только объекты типа Value")
        
        self._values.register_element(value)

    @property
    def name(self) -> str:
        """Имя порта (только для чтения)"""
        return self._name
    
    @property
    def port_prefix(self) -> str:
        return self._values.prefix

    def __iter__(self) -> Iterator[Value]:
        """Итерация по величинам порта"""
        return iter(self._values)

    def __getitem__(self, key: Union[uuid.UUID, str]) -> Value:
        """Доступ к величинам по индексу, id или имени"""
        return self._values[key]

    def __getattr__(self, name: str) -> Tuple[Any, ValueStatus]:
        """Доступ к величине по имени атрибута: val, status = port.G"""
        value = self._values[name]
        if value is not None:
            return value.value, value.status
        else:
            raise AttributeError(f"Порт '{self.name}' не содержит величины '{name}'")

    def __setattr__(self, name: str, value: Tuple[Any, Union[ValueStatus, str]]):
        """Установка значения и статуса величины: port.G = (50, 'calculated')"""
        if name.startswith('_') or name not in self.__dict__.get('_values_by_name', {}):
            # Стандартная установка атрибута
            super().__setattr__(name, value)
            return

        # Обработка установки значения величины
        value_obj = self._values_by_name[name]

        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("Требуется кортеж (значение, статус)")

        new_val, new_status = value

        # Преобразование строкового статуса в enum
        if isinstance(new_status, str):
            try:
                new_status = ValueStatus[new_status.upper()]
            except KeyError:
                raise ValueError(f"Неизвестный статус: {new_status}") from None

        value_obj.update(new_val, new_status)

    def get_value(self, identifier: Union[str, uuid.UUID]) -> Optional[Value]:
        """Получение объекта Value по имени или ID"""
        return self._values.get_object(identifier)

    def get_value_state(self, identifier: Union[str, uuid.UUID]) -> Optional[Tuple[Any, ValueStatus]]:
        """Получение состояния величины (значение и статус)"""
        value = self._values.get_object(identifier)
        if value is not None:
            return (value.value, value.status)
        else:
            return None

    def set_value_state(self, identifier: Union[str, uuid.UUID], value: Any, status: Union[ValueStatus, str]):
        """Установка состояния величины"""
        if identifier not in self._values:
            raise AttributeError(f"Порт '{self.name}' не содержит величины '{identifier}'")
        # Преобразование строкового статуса в enum
        if isinstance(status, str):
            try:
                status = ValueStatus[status.upper()]
            except KeyError:
                raise ValueError(f"Неизвестный статус: {status}") from None
        self.values[identifier].update(value, status)


    def __contains__(self, value: Union[str, uuid.UUID, Value]) -> bool:
        return value in self._values


    def __len__(self) -> int:
        """Количество величин в порте"""
        return len(self._values)

    def __repr__(self) -> str:
        """Строковое представление порта"""
        return (f"Port(name={self.name}, "
                f"values={[v.name for v in self._values.to_list()]})")

    def list_by_status(self, status: Union[ValueStatus, str, Collection[Union[ValueStatus, str]]]) -> List[str]:
        """
        Возвращает список имен величин с указанным статусом(ами)

        Поддерживает:
        - Одиночный статус (ValueStatus или строка)
        - Коллекцию статусов (список, кортеж, множество)

        :param status: Статус(ы) для фильтрации
        :return: Список имен величин
        """
        # Преобразуем входные данные в множество объектов ValueStatus
        if not isinstance(status, Collection) or isinstance(status, str):
            status = [status]

        status_set = {ValueStatus.from_input(s) for s in status}

        return [value.name for value in self._values if value.status in status_set]

    def list_known(self) -> List[str]:
        """
        Возвращает список имен величин со статусом, отличным от UNKNOWN

        :return: Список имен известных величин
        """
        return [value.name for value in self._values if value.status != ValueStatus.UNKNOWN]

    def list_unknown(self) -> List[str]:
        """
        Возвращает список имен величин со статусом UNKNOWN

        :return: Список имен неизвестных величин
        """
        return self.list_by_status(ValueStatus.UNKNOWN)

    @property
    def is_calculated(self) -> bool:
        """
        True если все величины в порте имеют статус отличный от UNKNOWN

        :return: Флаг полноты расчетов
        """
        return all(value.status != ValueStatus.UNKNOWN for value in self._values)

    def reset(self, reset_fixed: bool = False):
        """
        Сброс величин со статусами CALCULATED и DEPEND

        :param reset_fixed: Сбрасывать ли величины со статусом FIXED
        """
        for value in self._values:
            if value.status in (ValueStatus.CALCULATED, ValueStatus.DEPEND) or \
                    (reset_fixed and value.status == ValueStatus.FIXED):
                value.update(value.value, ValueStatus.UNKNOWN)

    def reset_by_names(self, names: List[str], reset_fixed: bool = False):
        """
        Сброс конкретных величин по именам

        :param names: Список имен величин для сброса
        :param reset_fixed: Сбрасывать ли FIXED величины
        """
        for name in names:
            if name in self._values_by_name:
                value = self._values_by_name[name]
                if value.status in (ValueStatus.CALCULATED, ValueStatus.DEPEND) or \
                        (reset_fixed and value.status == ValueStatus.FIXED):
                    value.update(None, ValueStatus.UNKNOWN)
                    
    def __eq__(self, other: object) -> bool:
        """
        Проверяет, эквивалентны ли два порта по количеству величин и их размерностям
        
        :param other: Другой объект для сравнения
        :return: True если порты эквивалентны, иначе False
        """
        if not isinstance(other, Port):
            return NotImplemented
        
        # Проверка количества величин
        if len(self) != len(other):
            return False
        
        # Создаем словари размерностей для быстрого сравнения
        self_dims = {value.name: value.dimension for value in self._values}
        other_dims = {value.name: value.dimension for value in other}
        
        # Сравниваем словари размерностей
        return self_dims == other_dims
    
    def __ne__(self, other: object) -> bool:
        """
        Проверяет, не эквивалентны ли два порта по количеству величин и их размерностям
        
        :param other: Другой объект для сравнения
        :return: True если порты не эквивалентны, иначе False
        """
        return not self.__eq__(other)