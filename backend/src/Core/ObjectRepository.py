from typing import (Dict, List, Optional, Callable, Any,
                    Union, Tuple, TypeVar, Generic, Iterator)
import uuid

T = TypeVar('T')
class ObjectRepository(Generic[T]):
    def __init__(self, rep_type: str, postfix: Optional[str] = None):
        self.repository: Dict[uuid.UUID, T] = {}
        self._base_name_to_id: Dict[str, uuid.UUID] = {}
        self._id_to_base_name: Dict[uuid.UUID, str] = {}
        self._obj_to_id: Dict[int, uuid.UUID] = {}
        self._obj_list: List[Tuple[uuid.UUID, T]] = []
        if rep_type.lower() in ['value', 'port', 'element']:
            self._repository_type = rep_type.lower()
        else:
            raise ValueError('Некорректно задан тип хранилища')

        self._postfix = postfix

    def _generate_full_name(self, base_name: str) -> str:
        if self._postfix is not None:
            return f'{base_name}_{self._postfix}'
        else:
            return base_name

    def _extract_base_name(self, name: str) -> str:
        if self._postfix and name.endswith(f"_{self._postfix}"):
            return name[:-(len(self._postfix) + 1)]
        return name

    def _validate_object_type(self, obj: T) -> bool:
        obj_type = type(obj).__name__.lower()
        return obj_type == self._repository_type

    def _validate_base_name(self, base_name: str) -> None:
        if '_' in base_name:
            raise ValueError(f"Базовое имя '{base_name}' содержит подчеркивание, что недопустимо")
        if base_name in self._base_name_to_id:
            raise ValueError(f"Базовое имя '{base_name}' уже зарегистрировано")

    def register(self, obj: T, obj_id: Optional[uuid.UUID] = None):
        if not self._validate_object_type(obj):
            raise TypeError(f"Объект типа {type(obj).__name__} не поддерживается")
        self._validate_base_name(obj.name)
        if obj_id is None:
            obj_id = uuid.uuid4()
        elif obj_id in self.repository:
            raise ValueError(f"UUID {obj_id} уже используется")
        self.repository[obj_id] = obj
        self._base_name_to_id[obj.name] = obj_id
        self._id_to_base_name[obj_id] = obj.name
        self._obj_to_id[id(obj)] = obj_id
        self._obj_list.append((obj_id, obj))

    def get_by_id(self, obj_id: uuid.UUID) -> Optional[T]:
        """Возвращает объект по UUID"""
        return self.repository.get(obj_id)

    def get_by_name(self, name: str) -> Optional[T]:
        """Возвращает объект по имени (полному или базовому)"""
        base_name = self._extract_base_name(name)
        obj_id = self._base_name_to_id.get(base_name)
        return self.repository.get(obj_id) if obj_id else None

    def get_by_object(self, obj: T) -> Optional[T]:
        """Возвращает зарегистрированную версию объекта"""
        obj_id = self._obj_to_id.get(id(obj))
        return self.repository.get(obj_id) if obj_id else None

    def get(self, identifier: Union[uuid.UUID, str]):
        return self[identifier]

    @property
    def repository_type(self) -> str:
        return self._repository_type

    @property
    def postfix(self) -> Optional[str]:
        return self._postfix

    @property
    def size(self) -> int:
        return len(self.repository)

    @property
    def registered_ids(self) -> List[uuid.UUID]:
        return list(self.repository.keys())

    @property
    def registered_base_names(self) -> List[str]:
        return list(self._base_name_to_id.keys())

    @property
    def registered_full_names(self) -> List[str]:
        return [self.get_full_name(name) for name in self.registered_base_names]
    
    def is_postfix(self, postfix: str):
        return postfix == self._postfix

    def remove(self, identifier: Union[uuid.UUID, str]) -> None:
        """Удаляет объект по UUID или имени"""
        if isinstance(identifier, uuid.UUID):
            obj_id = identifier
            base_name = self._id_to_base_name.get(obj_id)
        else:
            base_name = self._extract_base_name(identifier)
            obj_id = self._base_name_to_id.get(base_name)

        if not obj_id or not base_name:
            return

        # Удаление из всех индексов
        obj = self.repository.pop(obj_id)
        self._base_name_to_id.pop(base_name)
        self._id_to_base_name.pop(obj_id)
        self._obj_to_id.pop(id(obj))

    def __contains__(self, identifier: Union[uuid.UUID, str, T]) -> bool:
        if isinstance(identifier, uuid.UUID):
            return identifier in self.repository

        if isinstance(identifier, str):
            base_name = self._extract_base_name(identifier)
            return base_name in self._base_name_to_id

        return id(identifier) in self._obj_to_id

    def __getitem__(self, identifier: Union[uuid.UUID, str, int]) -> T:
        if isinstance(identifier, uuid.UUID):
            obj = self.get_by_id(identifier)
        elif isinstance(identifier, str):
            obj = self.get_by_name(identifier)
        else:
            try:
                obj = self._obj_list[identifier]
            except IndexError:
                obj = None
        if obj is None:
            raise KeyError(f"Объект не найден: {identifier}")
        return obj

    def __iter__(self) -> Iterator[Tuple[uuid.UUID, T]]:
        return iter(self.repository.items())

    def __len__(self) -> int:
        return self.size

    def values(self) -> List[T]:
        return list(self.repository.values())

    def items(self) -> List[Tuple[uuid.UUID, T]]:
        return list(self.repository.items())

    def find_by_value(self, value: Any) -> List[T]:
        """Находит объекты с указанным значением"""
        return [obj for obj in self.repository.values() if getattr(obj, 'value', None) == value]
    
   
if __name__ == '__main__':
    rep = ObjectRepository('element', prefix='1_1')
    rep.register_element(Value(10, 'zz', 'val3'))
    rep.register_element(Value(10, 'zz', 'val4'))
    rep.register_element(Value(10, 'zz', 'val5'))
    for ui in rep:
        print(rep[ui].name)
    print('val3_1_2' in rep)
    



    