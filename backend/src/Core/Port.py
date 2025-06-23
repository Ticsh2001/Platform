from Core.Value import Value, ValueStatus
import uuid
from typing import Dict, Iterator, List, Optional, Tuple, Union, Any, Collection
from enum import Enum, auto


class Port:
    def __init__(self, name: str, *values: Value):
        """
        Инициализация порта

        :param name: Имя порта (неизменяемое)
        :param values: Объекты Value, принадлежащие порту
        """
        self._id = uuid.uuid4()
        self._name = name
        self._values: List[Value] = []
        self._values_by_name: Dict[str, Value] = {}
        self._values_by_id: Dict[uuid.UUID, Value] = {}

        for value in values:
            self.add_value(value)

    def add_value(self, value: Value):
        """Добавление величины в порт с проверкой уникальности"""
        if not isinstance(value, Value):
            raise TypeError("Можно добавлять только объекты типа Value")

        if value.name in self._values_by_name:
            raise ValueError(f"Величина с именем '{value.name}' уже существует в порте")

        self._values.append(value)
        self._values_by_name[value.name] = value
        self._values_by_id[value.id] = value

    @property
    def id(self) -> uuid.UUID:
        """Уникальный идентификатор порта"""
        return self._id

    @property
    def name(self) -> str:
        """Имя порта (только для чтения)"""
        return self._name

    def __iter__(self) -> Iterator[Value]:
        """Итерация по величинам порта"""
        return iter(self._values)

    def __getitem__(self, key: Union[int, uuid.UUID, str]) -> Value:
        """Доступ к величинам по индексу, id или имени"""
        if isinstance(key, int):
            return self._values[key]
        elif isinstance(key, uuid.UUID):
            return self._values_by_id[key]
        elif isinstance(key, str):
            return self._values_by_name[key]
        else:
            raise TypeError("Ключ должен быть int, uuid.UUID или str")

    def __getattr__(self, name: str) -> Tuple[Any, ValueStatus]:
        """Доступ к величине по имени атрибута: val, status = port.G"""
        if name in self._values_by_name:
            value_obj = self._values_by_name[name]
            return (value_obj.value, value_obj.status)
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
        if isinstance(identifier, str):
            return self._values_by_name.get(identifier)
        elif isinstance(identifier, uuid.UUID):
            return self._values_by_id.get(identifier)
        return None

    def get_value_state(self, name: str) -> Optional[Tuple[Any, ValueStatus]]:
        """Получение состояния величины (значение и статус) по имени"""
        if name in self._values_by_name:
            value_obj = self._values_by_name[name]
            return (value_obj.value, value_obj.status)
        return None

    def set_value_state(self, name: str, value: Any, status: Union[ValueStatus, str]):
        """Установка состояния величины по имени"""
        if name not in self._values_by_name:
            raise AttributeError(f"Порт '{self.name}' не содержит величины '{name}'")

        # Преобразование строкового статуса в enum
        if isinstance(status, str):
            try:
                status = ValueStatus[status.upper()]
            except KeyError:
                raise ValueError(f"Неизвестный статус: {status}") from None

        self._values_by_name[name].update(value, status)


    def __contains__(self, value: Union[str, uuid.UUID, Value]) -> bool:
        """Проверка наличия величины в порте"""
        if isinstance(value, Value):
            return value.id in self._values_by_id
        elif isinstance(value, str):
            return value in self._values_by_name
        elif isinstance(value, uuid.UUID):
            return value in self._values_by_id
        return False


    def __len__(self) -> int:
        """Количество величин в порте"""
        return len(self._values)


    def __repr__(self) -> str:
        """Строковое представление порта"""
        return (f"Port(name={self.name}, id={self.id}, "
                f"values={[v.name for v in self._values]})")

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