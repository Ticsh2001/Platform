# backend/src/utils/plugin_api.py
import inspect
from typing import Any, Callable
from backend.src.Core.ElementProxy import ElementIO

def call_user_func(func: Callable, in_ports, out_ports, parameters) -> Any:
    """
    Унифицированный вызов пользовательских функций (calculate/setup):
    - новая сигнатура: func(io: ElementIO)
    - legacy-сигнатура: func(in_ports, out_ports, parameters)
    - гибрид: func(io=..., in_ports=..., out_ports=..., parameters=...)
    """
    io = ElementIO(in_ports, out_ports, parameters)
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # 1) Ровно один позиционный параметр → считаем, что это io
    if len(params) == 1 and params[0].kind in (inspect.Parameter.POSITIONAL_ONLY,
                                               inspect.Parameter.POSITIONAL_OR_KEYWORD):
        return func(io)

    # 2) Три позиционных → считаем, что это legacy
    if len(params) == 3 and all(p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                           inspect.Parameter.POSITIONAL_OR_KEYWORD)
                                for p in params):
        return func(in_ports, out_ports, parameters)

    # 3) Именованные параметры: подставим то, что доступно
    kwargs = {}
    if 'io' in sig.parameters:
        kwargs['io'] = io
    if 'in_ports' in sig.parameters:
        kwargs['in_ports'] = in_ports
    if 'out_ports' in sig.parameters:
        kwargs['out_ports'] = out_ports
    if 'parameters' in sig.parameters or 'params' in sig.parameters:
        if 'parameters' in sig.parameters:
            kwargs['parameters'] = parameters
        else:
            kwargs['params'] = parameters

    return func(**kwargs)