import uuid
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from Core.Value import ValueStatus
import re

class Element:
    def __init__(self, 
                 name: str,
                 in_ports: List['Port'],
                 out_ports: List['Port'],
                 parameters: List['Value'],
                 connections: Dict[str, List[str]],
                 description: str = '',
                 calculate_func: Optional[Callable[['Element'], None]] = None,
                 update_int_conn_func: Optional[Callable[['Element'], None]] = None,
                 setup_func: Optional[Callable[['Element'], None]] = None):
        """
        Базовый конструктор элемента
        
        :param name: Имя элемента
        :param in_ports: Словарь входных портов {имя: Port}
        :param out_ports: Словарь выходных портов {имя: Port}
        :param parameters: Словарь параметров {имя: Value}
        :param connections: Словарь внутренних связей {выходной_порт: [входные_порты]}
        :param calculate_func: Функция для расчета
        :param update_int_conn_func: Функция обновления связей
        :param setup_func: Функция настройки элемента
        """
        # Проверка имен на отсутствие подчеркиваний
        self._validate_names(in_ports, out_ports, parameters)
        
        self.id = uuid.uuid4()
        self.name = name
        self.description = description
        self.in_ports = in_ports
        self.out_ports = out_ports
        self.parameters = parameters
        self.connections = connections
        
        # Функции элемента
        self._calculate_func = calculate_func
        self._update_int_conn_func = update_int_conn_func
        self._setup_func = setup_func
        
        # Вызов функции настройки
        if self._setup_func:
            self._setup_func(self)

    def calculate(self):
        """Выполнение расчета элемента"""
        if self._calculate_func:
            self._calculate_func(self)
        else:
            raise NotImplementedError("Calculate function not implemented")

    def update_internal_connections(self):
        """Обновление внутренних связей"""
        if self._update_int_conn_func:
            self._update_int_conn_func(self)
        else:
            raise NotImplementedError("Update internal conncetions function not implemented")
        
    def __getitem__(self, index: Union[int, Tuple[int, int]]) -> 'Port':
        """
        Доступ к портам по индексу
        
        Поддерживает два формата:
        1. Одиночный индекс: (port_type, port_index)
        2. Два индекса: port_type, port_index
        
        :param index: Индекс(ы) для доступа к порту
        :return: Экземпляр Port
        """
        # Обработка разных форматов индекса
        if isinstance(index, tuple) and len(index) == 2:
            port_type, port_index = index
        elif isinstance(index, int):
            port_type = index
            port_index = 0  # По умолчанию первый порт
        else:
            raise TypeError("Неподдерживаемый тип индекса. Используйте (port_type, port_index) или port_type")
        
        # Получение порта
        if port_type == 0:  # Входные порты
            if port_index < 0 or port_index >= len(self.in_ports):
                raise IndexError(f"Недопустимый индекс входного порта: {port_index}")
            return self.in_ports[port_index]
        elif port_type == 1:  # Выходные порты
            if port_index < 0 or port_index >= len(self.out_ports):
                raise IndexError(f"Недопустимый индекс выходного порта: {port_index}")
            return self.out_ports[port_index]
        else:
            raise ValueError("Тип порта должен быть 0 (входной) или 1 (выходной)")
        
    def get_port(self, port_type: int, port_index: int) -> 'Port':
        """Альтернативный способ получения порта (для совместимости)"""
        return self[(port_type, port_index)]

    def find_port_by_name(self, name: str) -> Optional[Tuple[int, int, 'Port']]:
        """
        Поиск порта по имени
        
        :param name: Имя порта
        :return: Кортеж (тип_порта, индекс, порт) или None
        """
        # Поиск во входных портах
        for i, port in enumerate(self.in_ports):
            if port.name == name:
                return (0, i, port)
        
        # Поиск в выходных портах
        for i, port in enumerate(self.out_ports):
            if port.name == name:
                return (1, i, port)
        
        return None

    def setup(self):
        """Дополнительная настройка элемента"""
        if self._setup_func:
            self._setup_func(self)
            
    def _validate_names(self, in_ports: List['Port'], out_ports: List['Port'], 
                        parameters: Dict[str, 'Value']):
        """Проверка имен на отсутствие подчеркиваний"""
        # Проверка параметров
        for param_name in parameters:
            if '_' in param_name:
                raise ValueError(f"Имя параметра '{param_name}' содержит подчеркивание, что недопустимо")
        
        # Проверка портов и величин
        all_ports = in_ports + out_ports
        for port in all_ports:
            if '_' in port.name:
                raise ValueError(f"Имя порта '{port.name}' содержит подчеркивание, что недопустимо")
            
            for value in port:
                if '_' in value.name:
                    raise ValueError(f"Имя величины '{value.name}' в порте '{port.name}' содержит подчеркивание, что недопустимо")
                
    def find_port_by_id(self, port_id: uuid.UUID) -> Optional[Tuple[int, int, 'Port']]:
        """
        Поиск порта по UUID
        
        :param port_id: UUID порта
        :return: Кортеж (тип_порта, индекс, порт) или None
        """
        # Поиск во входных портах
        for i, port in enumerate(self.in_ports):
            if port.id == port_id:
                return (0, i, port)
        
        # Поиск в выходных портах
        for i, port in enumerate(self.out_ports):
            if port.id == port_id:
                return (1, i, port)
        
        return None
    
    def __getattr__(self, name: str) -> Tuple[Any, 'ValueStatus']:
        """
        Доступ к величинам и параметрам через атрибуты
        
        Форматы:
        - Параметры: element.param_name -> (value, status)
        - Величины входных портов: element.value_name_0_port_index
        - Величины выходных портов: element.value_name_1_port_index
        """
        # Пытаемся найти параметр
        if name in self.parameters:
            value_obj = self.parameters[name]
            return (value_obj.value, value_obj.status)
        
        # Пытаемся разобрать имя величины
        match = re.match(r'^(.+)_(\d)_(\d+)$', name)
        if match:
            value_name = match.group(1)
            port_type = int(match.group(2))
            port_index = int(match.group(3))
            
            # Получаем порт
            port = self.get_port(port_type, port_index)
            if port:
                # Получаем величину
                value_obj = port.get_value(value_name)
                if value_obj:
                    return (value_obj.value, value_obj.status)
        
        # Если ничего не найдено
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Tuple[Any, Union['ValueStatus', str]]):
    # Стандартные атрибуты устанавливаем обычным способом
        if name in ['id', 'name', 'description', 'in_ports', 'out_ports', 
                    'parameters', 'connections', '_calculate_func', 
                '_update_int_conn_func', '_setup_func']:
            super().__setattr__(name, value)
            
            return
    
    # Пытаемся найти параметр
        if 'parameters' in self.__dict__ and name in self.parameters:
            value_obj = self.parameters[name]
            self._set_value(value_obj, value)
            return
        
        # Пытаемся разобрать имя величины
        match = re.match(r'^(.+)_(\d)_(\d+)$', name)
        if match:
            value_name = match.group(1)
            port_type = int(match.group(2))
            port_index = int(match.group(3))
            
            # Получаем порт
            port = self.get_port(port_type, port_index)
            if port:
                # Получаем величину
                value_obj = port.get_value(value_name)
                if value_obj:
                    self._set_value(value_obj, value)
                    return
        
        # Если ничего не найдено, устанавливаем как обычный атрибут
        super().__setattr__(name, value)

    def _set_value(self, value_obj: 'Value', value: Tuple[Any, Union['ValueStatus', str]]):
        """Установка значения с обработкой статуса"""
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("Value must be a tuple (value, status)")
        
        new_value, status = value
        
        # Преобразование строкового статуса в enum
        if isinstance(status, str):
            status = ValueStatus.from_input(status)
        
        # Обновляем значение
        value_obj.update(new_value, status)

   