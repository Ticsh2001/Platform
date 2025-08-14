from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Port import Port
from backend.src.Core.Element import Element
from backend.src.Core.Value import Value, ValueClass, ValueStatus
import uuid

from typing import Dict, Iterator, List, Optional, Tuple, Union, Any, Collection, Type, Callable

def rep_list_values_by_status(repository: ObjectRepository, status: Union[List[Union[str, ValueStatus]], Union[str, ValueStatus]]):
    """
    Выдает список величин по статусу из репозиториев, хранящих величины
    :param repository: Репозиторий
    :param status: список или одно значение из запрашиваемых статусов
    """
    if not isinstance(status, list):
        status = [status]
    status = [ValueStatus.from_input(st) for st in status]
    values_list = []
    if not repository.repository_type in ['value', 'port']:
        return values_list
    elif repository.repository_type == 'port':
        for _, port in repository:
            values_list.extend([f'{val}_{port.name}' for val in port.list_by_status(status)])
    elif repository.repository_type == 'value':
        values_list = [value.name for _, value in  repository if value.status in status]
    return values_list

def rep_list_values_unknown(repository: ObjectRepository):
    return rep_list_values_by_status(repository, ValueStatus.UNKNOWN)

def rep_list_values_known(repository: ObjectRepository):
    return rep_list_values_by_status(repository, [ValueStatus.CALCULATED, ValueStatus.FIXED, ValueStatus.DEPEND])

def rep_test_condition(repository: ObjectRepository, known_names: Optional[List[str]]=None, unknown_names: Optional[List[str]]=None):
    known_values = rep_list_values_known(repository)
    unknown_values = rep_list_values_unknown(repository)
    return all([name in known_values for name in known_names]) and all([name in unknown_values for name in unknown_names])

def repos_test_condition(repositories: List[ObjectRepository], known_names: Optional[List[str]]=None, unknown_names: Optional[List[str]]=None):
    if known_names:
        known_values = []
        for repository in repositories:
            known_values.extend(rep_list_values_known(repository))
        res_known = all([name in known_values for name in known_names])
    else:
        res_known = True
    if unknown_names:
        unknown_values = []
        for repository in repositories:
            unknown_values.extend(rep_list_values_unknown(repository))
        res_unknown = all([name in known_values for name in known_names])
    else:
        res_unknown = True
    return res_known and res_unknown

def get_values(repositories: Union[List[ObjectRepository], ObjectRepository], values_names: List[str]):
    res = dict()
    if isinstance(repositories, ObjectRepository):
        repositories = [repositories]
    for name in values_names:
        if '_' in name:
            val, port = tuple(name.split('_'))
        else:
            val, port = name, None
        if port is not None:
            for rep in repositories:
                if rep.repository_type == 'port' and port in rep:
                    value, status = rep.get_by_name(port).get_value_state(val)
                    if status != ValueStatus.UNKNOWN:
                        res[name] = value
                    else:
                        res[name] = None
                        break
        else:
            for rep in repositories:
                if rep.repository_type == 'value' and val in rep:
                    value, status = rep.get_by_name(val).get_state()
                    if status != ValueStatus.UNKNOWN:
                        res[val] = value
                    else:
                        res[val] = None
                        break
        if val not in res:
            res[val] = None
    return res
                


    

    
            




