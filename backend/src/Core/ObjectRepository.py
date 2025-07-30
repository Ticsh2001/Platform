from typing import Dict, List, Optional, Callable, Any, Union, Tuple
import uuid
#from Value import Value



class ObjectRepository:
    def __init__(self, rep_type: str, prefix: Optional[str]=None):
        self.repository = dict()
        self._name_rep = dict()
        if rep_type.lower() in ['value', 'port', 'element']:
            self._repository_type = rep_type.lower()
        else:
            raise ValueError('Некорректно задан тип хранилища')
        self._prefix = prefix
        
    def _validate_object(self, obj: Union['Value', 'Port', 'Element']) -> bool:
        if self.rep_type == 'value' and type(obj).__name__ == 'Value':
            return True
        elif self.rep_type == 'port' and type(obj).__name__ == 'Port':
            return True
        elif self.rep_type == 'element' and type(obj).__name__ == 'Element':
            return True
        else:
            return False
        
    def _validate_name(self, obj: Union['Value', 'Port', 'Element']) -> bool:
        if '_' not in obj.name:
            if obj.name not in self._name_rep:
                return True
            else:
                 raise ValueError(f"Имя параметра '{obj.name}' уже зарегестрировано в порте")
        else:
             raise ValueError(f"Имя параметра '{obj.name}' содержит подчеркивание, что недопустимо")
        
    def register_element(self, obj: Union['Value', 'Port', 'Element'], obj_id: Optional[uuid.UUID]=None):
        if not self._validate_name(obj):
            return
        if self._validate_object(obj):
            if obj_id is None:
                _obj_id = uuid.uuid4()
            else:
                _obj_id = obj_id
            self.repository[_obj_id] = obj
            self._name_rep[obj.name] = (_obj_id, obj)

    @property
    def repository_type(self) -> str:
        return self._repository_type
    
    @property
    def prefix(self) -> str:
        return self._prefix
    
    @property
    def num(self) -> int:
        return len(self.repository)
    
    @property
    def registered_ids(self) -> List[uuid.UUID]:
        return list(self.repository.keys())
    
    @property
    def registered_names(self, prefix=False) -> List[str]:
        return list(self._name_rep.keys())
    
    def get_object(self, val: Union[uuid.UUID, str]) -> Union['Value', 'Port', 'Element', None]:
        if isinstance(val, uuid.UUID):
            return self.repository.get(idx, None)
        else:
           if self._prefix is not None and '_' in val:
                obj_name = val.split('_')[0]
           else:
                obj_name = val
           try:
               return self._name_rep.get(obj_name, None)[1]
           except TypeError:
               return None
    
    def __contains__ (self, val: Union[uuid.UUID, str, Union['Value', 'Port', 'Element']]) -> bool:
        if isinstance(val, uuid.UUID):
            return val in self.repository
        elif isinstance(val, str):
            if self._prefix is not None and '_' in val:
                obj_name = val.split('_')[0]
            else:
                obj_name = val
            return obj_name in self._name_rep
        else:
            if self._validate_object(val):
                for obj in self.repository.values():
                    if obj == val:
                        return True
        return False
        
    def __getitem__(self, val: Union[uuid.UUID, str]) -> Union['Value', 'Port', 'Element', None]:
        return get_object(val)
           
    def __iter__(self):
        return iter(self.repository)
    
    def __len__(self):
        return self.num
    
    def to_list(self):
        return list(self._name_rep.values())
    
   
if __name__ == '__main__':
    rep = ObjectRepository('element', prefix='1_1')
    rep.register_element(Value(10, 'zz', 'val3'))
    rep.register_element(Value(10, 'zz', 'val4'))
    rep.register_element(Value(10, 'zz', 'val5'))
    for ui in rep:
        print(rep[ui].name)
    print('val3_1_2' in rep)
    



    