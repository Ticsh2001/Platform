import uuid
import numpy as np
from enum import Enum, auto
from typing import Dict, Iterator, List, Optional, Tuple, Union, Any, Collection, Type, Callable
import copy
from dataclasses import dataclass


class ValueStatus(Enum):
    """Статусы значений для отслеживания состояния параметра"""
    UNKNOWN = auto()
    DEPEND = auto()  # Значение зависит от других параметров
    CALCULATED = auto()  # Рассчитано в процессе вычислений
    FIXED = auto()  # Фиксированное значение (не изменяется)

    @classmethod
    def from_input(cls, status_input: Union[str, 'ValueStatus']) -> 'ValueStatus':
        """Преобразует различные форматы в объект ValueStatus"""
        if isinstance(status_input, ValueStatus):
            return status_input
        elif isinstance(status_input, str):
            normalized = status_input.upper().strip()
            for status in cls:
                if status.name == normalized:
                    return status
            raise ValueError(f"Неизвестный статус: {status_input}. "
                             f"Допустимые значения: {', '.join([s.name for s in cls])}")
        else:
            raise TypeError(f"Неподдерживаемый тип статуса: {type(status_input)}")
        
@dataclass
class ValueClass:
    value_name: str             #Название величины (например, энтальпия, энтропия и т.д. - это не конкретное название параметра для данного элемента)
    physics_type: str = None    #Физическое направление, к которому относится параметр (например, термодинамика, механика и т.д.)
    dimension: str = None       #Размерность

    def __eq__(self, other: 'ValueClass'):
        if not isinstance(other, ValueClass):
            return NotImplemented
        elif self.physics_type == other.physics_type and self.value_name == other.value_name and self.dimension == other.dimension:
            return True
        else:
            return False
        
    def __ne__(self, other: 'ValueClass'):
        return not self.__eq__(other)






class Value:
    def __init__(self,
                 name: str,
                 value_spec: ValueClass,
                 value: Any,
                 description: str = "",
                 status: ValueStatus = ValueStatus.UNKNOWN,
                 store_prev: bool = True,
                 min_value: Optional[Any] = None,
                 max_value: Optional[Any] = None):
        """
        Инициализация параметра

        :param value: Значение параметра (любого типа)
        :param dimension: Физическая размерность (например, "m/s")
        :param name: Имя параметра (идентификатор) - например, имя параметра h1 (а )
        :param description: Описание параметра
        :param status: Исходный статус значения
        :param store_prev: Флаг сохранения предыдущих значений
        """
        self._name = name
        self._description = description
        self._status = ValueStatus.from_input(status)
        self._store_prev = store_prev
        self._prev_val = None
        self._prev_status = None
        self._min_value = min_value
        self._max_value = max_value
        self._value_spec = value_spec

        # Установка значения с валидацией
        self._val = None
        self.value = value  # Используем сеттер для валидации

        # Сохраняем исходное значение как предыдущее
        if self._store_prev:
            self._save_previous()

    def _save_previous(self):
        """Сохранение текущего состояния как предыдущего"""
        self._prev_val = self._try_copy(self._val)
        self._prev_status = self._status

    @property
    def value(self) -> Any:
        """Текущее значение параметра"""
        return self._val

    @value.setter
    def value(self, new_value: Any):
        """Установка нового значения без изменения статуса"""
        self.update(new_value)

    @property
    def dimension(self) -> Optional[str]:
        """Физическая размерность параметра"""
        return self._value_spec.dimension
    
    @property
    def physics_type(self) -> Optional[str]:
        """К какой физической группе относится"""
        return self._value_spec.physics_type
    
    @property
    def physics_value_name(self) -> str:
        """Физическое название величины"""
        return self._value_spec.value_name

    @property
    def name(self) -> str:
        """Имя параметра"""
        return self._name

    @property
    def description(self) -> str:
        """Описание параметра"""
        return self._description

    @property
    def status(self) -> ValueStatus:
        """Текущий статус значения (только для чтения)"""
        return self._status

    @property
    def value_type(self) -> Type:
        """Тип хранимого значения"""
        return type(self._val)

    @property
    def store_prev(self) -> bool:
        """Флаг сохранения предыдущих значений"""
        return self._store_prev

    @store_prev.setter
    def store_prev(self, flag: bool):
        """Изменение флага сохранения истории"""
        self._store_prev = flag
        if not flag:
            self._prev_val = None
            self._prev_status = None
        elif self._prev_val is None:
            self._save_previous()

    @property
    def previous_value(self) -> Optional[Any]:
        """Предыдущее значение параметра (если доступно)"""
        return self._prev_val

    @property
    def previous_status(self) -> Optional[ValueStatus]:
        """Предыдущий статус параметра (если доступен)"""
        return self._prev_status

    @property
    def min_value(self) -> Optional[Any]:
        """Минимально допустимое значение"""
        return self._min_value

    @property
    def max_value(self) -> Optional[Any]:
        """Максимально допустимое значение"""
        return self._max_value

    def _validate_value(self, value: Any):
        """Проверка значения на соответствие границам"""
        if value is None:
            return  # None всегда разрешен

        # Проверка минимального значения
        if self._min_value is not None:
            try:
                if np.any(value < self._min_value):
                    raise ValueError(f"Значение {value} меньше минимального {self._min_value}")
            except TypeError:
                # Для нестандартных типов используем оператор <
                if value < self._min_value:
                    raise ValueError(f"Значение {value} меньше минимального {self._min_value}")

        # Проверка максимального значения
        if self._max_value is not None:
            try:
                if np.any(value > self._max_value):
                    raise ValueError(f"Значение {value} больше максимального {self._max_value}")
            except TypeError:
                # Для нестандартных типов используем оператор >
                if value > self._max_value:
                    raise ValueError(f"Значение {value} больше максимального {self._max_value}")

    def update(self, new_value: Any, new_status: Optional[ValueStatus] = None):
        """
        Обновление значения и статуса с валидацией

        :param new_value: Новое значение
        :param new_status: Новый статус
        """
        # Валидация нового значения
        self._validate_value(new_value)

        # Сохраняем текущее состояние перед обновлением
        if self._store_prev:
            self._save_previous()

        # Устанавливаем новые значения
        self._val = new_value
        if new_status is not None:
            self._status = new_status

    def set_bounds(self, min_value: Optional[Any] = None, max_value: Optional[Any] = None):
        """
        Установка новых граничных значений с валидацией текущего значения

        :param min_value: Новое минимальное значение
        :param max_value: Новое максимальное значение
        """
        # Сохраняем текущие границы
        old_min = self._min_value
        old_max = self._max_value

        try:
            # Временно устанавливаем новые границы
            self._min_value = min_value
            self._max_value = max_value

            # Проверяем текущее значение на соответствие новым границам
            self._validate_value(self._val)
        except ValueError:
            # В случае ошибки восстанавливаем старые границы
            self._min_value = old_min
            self._max_value = old_max
            raise

    def get_residual(self) -> Optional[Any]:
        """
        Вычисление разницы между текущим и предыдущим значением

        :return: Разница значений или None, если:
                 - предыдущее значение недоступно
                 - предыдущий статус UNKNOWN
                 - операция вычитания не поддерживается
        """
        # Не вычисляем residual если предыдущее значение не сохранено
        if self._prev_val is None:
            return None

        # Не вычисляем residual для UNKNOWN статуса
        if self._prev_status == ValueStatus.UNKNOWN:
            return None

        try:
            # Для numpy-массивов
            if isinstance(self._val, np.ndarray):
                return self._val - self._prev_val

            # Для тензоров TensorFlow
            if hasattr(self._val, 'numpy') and hasattr(self._prev_val, 'numpy'):
                return self._val.numpy() - self._prev_val.numpy()

            # Для тензоров PyTorch
            if (hasattr(self._val, 'detach') and hasattr(self._prev_val, 'detach') and
                    hasattr(self._val, 'numpy') and hasattr(self._prev_val, 'numpy')):
                return self._val.detach().numpy() - self._prev_val.detach().numpy()

            # Общий случай для поддерживающих вычитание
            if hasattr(self._val, '__sub__'):
                return self._val - self._prev_val

        except (TypeError, ValueError):
            pass

        return None

    def reset_history(self):
        """Сброс истории предыдущих значений"""
        self._prev_val = None
        self._prev_status = None
        if self._store_prev:
            self._save_previous()

    def get_state(self) -> Tuple[Any, ValueStatus]:
        """Получение текущего состояния (значение + статус)"""
        return self._val, self._status

    @staticmethod
    def _try_copy(obj: Any) -> Any:
        """Попытка создания копии объекта"""
        try:
            # Для numpy-массивов
            if isinstance(obj, np.ndarray):
                return obj.copy()

            # Для тензоров TensorFlow/PyTorch
            if hasattr(obj, 'numpy'):
                return obj.numpy().copy()
            if hasattr(obj, 'detach'):
                return obj.detach().clone()

            # Общий случай
            return copy.deepcopy(obj)
        except:
            # Если копирование невозможно, возвращаем оригинал
            return obj

    # Добавляем логические операции сравнения
    def _check_comparable(self, other: 'Value') -> None:
        """Проверка возможности сравнения двух значений"""
        if self.dimension != other.dimension:
            raise ValueError(f"Несовместимые размерности: {self.dimension} vs {other.dimension}")
        if self.physics_type != other.physics_type:
            raise ValueError(f'Несовместимые физические направления: {self.physics_type} vs {other.physics_type}')
        if self.physics_value_name != other.physics_value_name:
            raise ValueError(f'Несовместимые физические величины: {self.physics_value_name} vs {other.physics_value_name}')

        if not hasattr(self._val, '__eq__') or not hasattr(other.value, '__eq__'):
            raise TypeError("Значения не поддерживают операции сравнения")

    def __eq__(self, other: 'Value') -> bool:
        """Оператор равенства == с проверкой размерности"""
        if not isinstance(other, Value):
            return NotImplemented
        self._check_comparable(other)
        return self._val == other.value

    def __ne__(self, other: 'Value') -> bool:
        """Оператор неравенства != с проверкой размерности"""
        if not isinstance(other, Value):
            return NotImplemented
        self._check_comparable(other)
        return self._val != other.value

    def __lt__(self, other: 'Value') -> bool:
        """Оператор меньше < с проверкой размерности"""
        if not isinstance(other, Value):
            return NotImplemented
        self._check_comparable(other)
        return self._val < other.value

    def __le__(self, other: 'Value') -> bool:
        """Оператор меньше или равно <= с проверкой размерности"""
        if not isinstance(other, Value):
            return NotImplemented
        self._check_comparable(other)
        return self._val <= other.value

    def __gt__(self, other: 'Value') -> bool:
        """Оператор больше > с проверкой размерности"""
        if not isinstance(other, Value):
            return NotImplemented
        self._check_comparable(other)
        return self._val > other.value

    def __ge__(self, other: 'Value') -> bool:
        """Оператор больше или равно >= с проверкой размерности"""
        if not isinstance(other, Value):
            return NotImplemented
        self._check_comparable(other)
        return self._val >= other.value

    def compare(self, other: 'Value', operator: str) -> bool:
        """
        Универсальный метод сравнения с указанием оператора

        :param other: Другой объект Value для сравнения
        :param operator: Оператор сравнения ('==', '!=', '<', '<=', '>', '>=')
        :return: Результат сравнения
        """
        operators = {
            '==': self.__eq__,
            '!=': self.__ne__,
            '<': self.__lt__,
            '<=': self.__le__,
            '>': self.__gt__,
            '>=': self.__ge__
        }

        if operator not in operators:
            raise ValueError(f"Неподдерживаемый оператор: {operator}")

        return operators[operator](other)

    def __repr__(self) -> str:
        """Обновленное строковое представление с информацией о вызываемости"""
        call_info = ""
        if callable(self._val):
            sig = self.callable_signature
            call_info = f", callable={sig}" if sig else ", callable=True"
        return (f"Value(name={self.name!r}, dimension={self.dimension!r}, "
                f"value={self.value}, status={self.status.name}{call_info})")

    def __iter__(self) -> Iterator[Union[Any, ValueStatus]]:
        """Позволяет распаковывать Value как (значение, статус)"""
        yield self.value
        yield self.status

    def __call__(self, *args, **kwargs) -> Any:
        """
        Универсальный вызов значения:
        - Если значение является вызываемым объектом, вызывает его с аргументами
        - Иначе возвращает само значение (игнорируя аргументы)

        :param args: Позиционные аргументы для вызываемого объекта
        :param kwargs: Именованные аргументы для вызываемого объекта
        :return: Результат вызова или само значение
        """
        if callable(self._val):
            try:
                # Пробуем вызвать объект
                return self._val(*args, **kwargs)
            except Exception as e:
                raise RuntimeError(f"Ошибка при вызове значения '{self.name}': {str(e)}") from e
        else:
            # Для не-функций просто возвращаем значение
            return self._val

    def is_callable(self) -> bool:
        """Проверяет, является ли хранимое значение вызываемым объектом"""
        return callable(self._val)

    @property
    def callable_signature(self) -> Optional[str]:
        """Возвращает строковое представление сигнатуры вызываемого объекта"""
        if not callable(self._val):
            return None
        try:
            # Для функций и методов
            if hasattr(self._val, '__name__'):
                name = self._val.__name__
            else:
                name = str(self._val)

            # Пытаемся получить информацию о параметрах
            import inspect
            sig = inspect.signature(self._val)
            return f"{name}{sig}"
        except:
            return f"Callable object: {type(self._val).__name__}"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Value':
        """
        Создает экземпляр Value из словаря

        :param data: Словарь с параметрами для создания объекта
        :return: Экземпляр класса Value

        Поддерживаемые ключи:
        - 'value' (обязательный): хранимое значение
        - 'dimension' (обязательный): размерность величины
        - 'name' (обязательный): имя величины
        - 'description': описание (по умолчанию "")
        - 'status': статус (строка или ValueStatus, по умолчанию UNKNOWN)
        - 'store_prev': флаг сохранения истории (по умолчанию True)
        - 'min_value': минимальное значение (по умолчанию None)
        - 'max_value': максимальное значение (по умолчанию None)
        """
        # Проверка обязательных параметров
        required_keys = ['value', 'name', 'value_spec']
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise ValueError(f"Отсутствуют обязательные ключи: {', '.join(missing)}")

        # Извлечение параметров с установкой значений по умолчанию
        value = data['value']
        value_spec = ValueClass(data['value_spec']['value_name'], 
                                data['value_spec'].get('physics_class', None),
                                data['value_spec'].get('dimension', None))
        name = data['name']
        description = data.get('description', "")
        store_prev = data.get('store_prev', True)
        min_value = data.get('min_value', None)
        max_value = data.get('max_value', None)

        # Обработка статуса
        status_data = data.get('status', ValueStatus.UNKNOWN)
        if isinstance(status_data, str):
            status = ValueStatus.from_input(status_data)
        elif isinstance(status_data, ValueStatus):
            status = status_data
        else:
            raise TypeError(f"Неподдерживаемый тип для статуса: {type(status_data)}")

        return Value(
            name=name,
            value_spec=value_spec,
            value=value,
            description=description,
            status=status,
            store_prev=store_prev,
            min_value=min_value,
            max_value=max_value
        )

    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        """
        Преобразует объект Value в словарь

        :param include_private: Включать ли приватные атрибуты (id, предыдущие значения)
        :return: Словарь с параметрами объекта
        """
        data = {
            'value': self._val,
            'dimension': self.dimension,
            'name': self.name,
            'description': self.description,
            'status': self.status.name,
            'store_prev': self.store_prev,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'is_callable': self.is_callable()
        }

        if include_private:
            data.update({
                'id': str(self.id),
                'previous_value': self.previous_value,
                'previous_status': self.previous_status.name if self.previous_status else None
            })
        return data
    
    
if __name__ == '__main__':
    print('hello')
