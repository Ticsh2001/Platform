class Element:
    PROTECTED_ATTRS = [
        '_name', '_description',
        '_in_ports', '_out_ports', '_parameters',
        '_calculate_func', '_update_int_conn_func', '_setup_func',
        'PROTECTED_ATTRS'
    ]

    def __init__(self, 
                 name: str,
                 description: str,
                 in_ports: List[Union[dict, Port]],
                 out_ports: List[Union[dict, Port]],
                 parameters: List[Union[dict, Value]],
                 calculate_func: Optional[Callable[['Element'], None]] = None,
                 update_int_conn_func: Optional[Callable[['Element'], None]] = None,
                 setup_func: Optional[Callable[['Element'], None]] = None):

        super().__setattr__('_name', name)
        super().__setattr__('_description', description)
        super().__setattr__('_in_ports', ObjectRepository(rep_type='port', postfix=name))
        super().__setattr__('_out_ports', ObjectRepository(rep_type='port', postfix=name))
        super().__setattr__('_parameters', ObjectRepository(rep_type='value', postfix=name))

        for port in in_ports:
            self._add_port(port, is_input=True)
        for port in out_ports:
            self._add_port(port, is_input=False)
        for param in parameters:
            self._add_parameter(param)

        self._validate_and_set_func('_calculate_func', calculate_func)
        self._validate_and_set_func('_update_int_conn_func', update_int_conn_func)
        self._validate_and_set_func('_setup_func', setup_func)

        if self._setup_func:
            self._setup_func(self)

    def _add_port(self, port_data: Union[dict, Port], is_input: bool):
        port = port_data if isinstance(port_data, Port) else Port.from_dict(port_data)
        repo = self._in_ports if is_input else self._out_ports
        repo.register(port)

    def _add_parameter(self, param_data: Union[dict, Value]):
        param = param_data if isinstance(param_data, Value) else Value.from_dict(param_data)
        self._parameters.register(param)

    def _validate_and_set_func(self, attr_name: str, func: Optional[Callable]):
        if func is not None and not callable(func):
            raise TypeError(f"{attr_name[1:]} must be callable or None")
        super().__setattr__(attr_name, func)

    # ---------------------------
    # Универсальный поиск Value
    # ---------------------------
    def _resolve_target(self, attr_name: str) -> Optional[Value]:
        # 1. Параметры элемента
        if attr_name in self._parameters:
            return self._parameters[attr_name]

        # 2. value_name_portIndex
        m_index = re.match(r"^(.+)_(\d)_(\d+)$", attr_name)
        if m_index:
            v_name, port_type, port_index = m_index[1], int(m_index[2]), int(m_index[3])
            repo = self._in_ports if port_type == 0 else self._out_ports
            if 0 <= port_index < len(repo):
                port = repo[port_index]
                return port.get_value(v_name)

        # 3. value_name_portName
        m_name = re.match(r"^(.+)_([A-Za-z0-9]+)$", attr_name)
        if m_name:
            v_name, port_name = m_name[1], m_name[2]
            port = self._in_ports.get_by_name(port_name) or self._out_ports.get_by_name(port_name)
            if port:
                return port.get_value(v_name)

        return None

    # ---------------------------
    # Доступ к данным
    # ---------------------------
    def __getattr__(self, name: str) -> Any:
        if name in self.PROTECTED_ATTRS:
            return super().__getattribute__(name)

        value_obj = self._resolve_target(name)
        if value_obj:
            return (value_obj.value, value_obj.status)

        raise AttributeError(f"{self.__class__.__name__} has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name in self.PROTECTED_ATTRS:
            super().__setattr__(name, value)
            return

        value_obj = self._resolve_target(name)
        if value_obj:
            self._set_value(value_obj, value)
            return

        super().__setattr__(name, value)

    def _set_value(self, value_obj: Value, value: Any):
        if isinstance(value, tuple) and len(value) == 2:
            v, status = value
            if isinstance(status, str):
                status = ValueStatus.from_input(status)
            value_obj.update(v, status)
        else:
            value_obj.update(value)

    # ---------------------------
    # API
    # ---------------------------
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def in_ports(self) -> ObjectRepository:
        return self._in_ports

    @property
    def out_ports(self) -> ObjectRepository:
        return self._out_ports

    @property
    def parameters(self) -> ObjectRepository:
        return self._parameters

    def get_port(self, identifier: Union[str, uuid.UUID, int]) -> Port:
        if isinstance(identifier, uuid.UUID):
            return self._in_ports.get_by_id(identifier) or self._out_ports.get_by_id(identifier)
        if isinstance(identifier, str):
            return self._in_ports.get_by_name(identifier) or self._out_ports.get_by_name(identifier)
        if isinstance(identifier, int):
            if identifier < len(self._in_ports):
                return self._in_ports[identifier]
            return self._out_ports[identifier - len(self._in_ports)]
        raise KeyError(f"Port not found: {identifier}")

    def calculate(self):
        if self._calculate_func:
            self._calculate_func(self)
        else:
            raise NotImplementedError("Calculate function not implemented")

    def update_internal_connections(self):
        if self._update_int_conn_func:
            self._update_int_conn_func(self)
        else:
            raise NotImplementedError("Update internal connections function not implemented")

    # ---------------------------
    # Сериализация
    # ---------------------------
    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "in_ports": [p.as_dict() for _, p in self._in_ports.items()],
            "out_ports": [p.as_dict() for _, p in self._out_ports.items()],
            "parameters": [p.to_dict() for _, p in self._parameters.items()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Element":
        return cls(
            name=data["name"],
            description=data["description"],
            in_ports=data["in_ports"],
            out_ports=data["out_ports"],
            parameters=data["parameters"]
        )

    def __repr__(self) -> str:
        return f"Element({self.name}, in={len(self._in_ports)}, out={len(self._out_ports)}, params={len(self._parameters)})"
    
    def __getitem__(self, key: Union[Tuple[int, int], int, str, uuid.UUID]) -> Port:
        """
        Варианты использования:
        - elem[0, 1] → входной порт (0=in|1=out, index)
        - elem[4] → общий индекс по всем портам
        - elem['portname'] → поиск по имени
        - elem[uuid] → поиск по ID
        """
        if isinstance(key, tuple) and len(key) == 2:
            port_type, port_index = key
            if port_type == 0:
                return self._in_ports[port_index]
            elif port_type == 1:
                return self._out_ports[port_index]
            else:
                raise IndexError("Неверный тип порта (0=in, 1=out)")

        if isinstance(key, int):
            if key < len(self._in_ports):
                return self._in_ports[key]
            key -= len(self._in_ports)
            if key < len(self._out_ports):
                return self._out_ports[key]
            raise IndexError("Порт с таким индексом не найден")

        if isinstance(key, str):
            port = self._in_ports.get_by_name(key)
            if port:
                return port
            port = self._out_ports.get_by_name(key)
            if port:
                return port
            raise KeyError(f"Порт '{key}' не найден")

        if isinstance(key, uuid.UUID):
            port = self._in_ports.get_by_id(key)
            if port:
                return port
            port = self._out_ports.get_by_id(key)
            if port:
                return port
            raise KeyError(f"Порт с ID {key} не найден")

        raise TypeError(f"Неверный тип аргумента для __getitem__: {type(key).__name__}")

    # ------------------- Методы доступа через ID -------------------

    def get_port_by_id(self, port_id: uuid.UUID) -> Port:
        return self._in_ports.get_by_id(port_id) or self._out_ports.get_by_id(port_id)

    def get_parameter_by_id(self, param_id: uuid.UUID) -> Optional[Value]:
        return self._parameters.get_by_id(param_id)

    def get_value_from_port_by_id(self, port_id: uuid.UUID, value_name: str) -> Optional[Value]:
        port = self.get_port_by_id(port_id)
        if not port:
            return None
        return port.get_value(value_name)

    def get_all_port_ids(self) -> list:
        return self._in_ports.registered_ids + self._out_ports.registered_ids

    def get_all_parameter_ids(self) -> list:
        return self._parameters.registered_ids

    def get_all_value_ids_in_ports(self) -> list:
        """Возвращает список (port_id, value_name) для всех значений портов"""
        result = []
        for port_id, port in self._in_ports.items():
            for val_name in port._values.registered_base_names:
                result.append((port_id, val_name))
        for port_id, port in self._out_ports.items():
            for val_name in port._values.registered_base_names:
                result.append((port_id, val_name))
        return result