from backend.src.Core.Element import Element
from backend.src.Core.Port import Port

class Thermodynamic(Element):
    def __init__(self, name, descritption, **kwargs):
        in_ports = [kwargs['factory']]
        