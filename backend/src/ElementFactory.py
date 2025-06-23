import json
import importlib.util
import os
from typing import Dict, Type, Any
from .Core.Port import Port
from .Core.Element import Element
from .Core.Value import Value

class ElementFactory:
    def __init__(self, config_dir: str):
        """
        Инициализация фабрики элементов
        
        :param config_dir: Путь к директории с конфигурациями
        """
        self.config_dir = config_dir
        self.templates: Dict[str, dict] = {}
        self.loaded_scripts: Dict[str, Any] = {}  # Кэш загруженных модулей
        
        # Загрузка всех конфигураций при инициализации
        self.load_all_configs()

    def load_all_configs(self):
        """Загрузка всех JSON-конфигураций из директории"""
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                try:
                    element_type = filename[:-5]  # Убираем .json
                    with open(os.path.join(self.config_dir, filename)) as f:
                        self.templates[element_type] = json.load(f)
                except Exception as e:
                    print(f"Ошибка загрузки конфигурации {filename}: {str(e)}")

    def _load_functions(self, script_path: str) -> dict:
        """Загрузка функций из скрипта"""
        if not script_path or not os.path.exists(script_path):
            return {}
            
        # Проверка кэша
        if script_path in self.loaded_scripts:
            return self.loaded_scripts[script_path]
            
        try:
            # Динамическая загрузка модуля
            module_name = os.path.splitext(os.path.basename(script_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Извлечение функций
            functions = {
                'calculate': getattr(module, 'calculate', None),
                'update_internal_connections': getattr(module, 'update_internal_connections', None),
                'setup_element': getattr(module, 'setup_element', None)
            }
            
            # Сохранение в кэш
            self.loaded_scripts[script_path] = functions
            return functions
        except Exception as e:
            print(f"Ошибка загрузки скрипта {script_path}: {str(e)}")
            return {}

    def create_element(self, element_type: str, name: str, **kwargs) -> Element:
        """
        Создание элемента по типу
        
        :param element_type: Тип элемента (соответствует имени JSON-файла)
        :param name: Имя создаваемого элемента
        :param kwargs: Дополнительные параметры для переопределения конфигурации
        :return: Экземпляр Element
        """
        if element_type not in self.templates:
            raise ValueError(f"Unknown element type: {element_type}")
            
        config = self.templates[element_type].copy()
        
        # Обновление конфигурации пользовательскими параметрами
        config.update(kwargs)
        
        # Загрузка функций из скрипта
        script_path = config.get('script_path', '')
        functions = self._load_functions(script_path) if script_path else {}
        
        # Создание портов
        in_ports = self._create_ports(config.get('in_ports', []))
        out_ports = self._create_ports(config.get('out_ports', []))
        
        # Создание параметров
        parameters = self._create_parameters(config.get('parameters', {}))
        
        # Создание элемента
        return Element(
            name=name,
            in_ports=in_ports,
            out_ports=out_ports,
            parameters=parameters,
            connections=config.get('connections', {}),
            calculate_func=functions.get('calculate'),
            update_int_conn_func=functions.get('update_internal_connections'),
            setup_func=functions.get('setup_element')
        )

    def _create_ports(self, ports_config: List[Dict]) -> Dict[str, Port]:
        """Создание портов из конфигурации"""
        ports = {}
        for port_config in ports_config:
            port = Port(port_config['name'])
            for value_config in port_config.get('values', []):
                value = Value.from_dict(value_config)
                port.add_value(value)
            ports[port.name] = port
        return ports

    def _create_parameters(self, params_config: Dict) -> Dict[str, Value]:
        """Создание параметров из конфигурации"""
        parameters = {}
        for name, value_config in params_config.items():
            parameters[name] = Value.from_dict(value_config)
        return parameters