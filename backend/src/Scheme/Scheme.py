import uuid

from backend.src.Core.Element import Element
from backend.src.Core.Value import ValueClass, Value, ValueStatus
from backend.src.Core.Port import Port
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Factory.ElementFactory import ElementFactory



class Scheme:
    def __init__(self, value_classes_path: str, ports_path: str, elements_dir: str):
        self.elements_repo = ObjectRepository(rep_type="element")
        self.connections_repo = ObjectRepository(rep_type="connection")
        self.factory = ElementFactory(value_classes_path, ports_path, elements_dir)

    def add_element(self, element_name: str) -> uuid.UUID:
        element = self.factory.create_element(element_name)
        return self.elements_repo.register(element)

    def connect(self, out_elem_id: uuid.UUID, out_port_name: str,
                in_elem_id: uuid.UUID, in_port_name: str):
        out_elem = self.elements_repo.get_by_id(out_elem_id)
        in_elem = self.elements_repo.get_by_id(in_elem_id)
        out_port = out_elem[out_port_name]
        in_port = in_elem[in_port_name]
        conn = Connection(out_elem.id, out_port.id, in_elem.id, in_port.id)
        conn.validate(self.elements_repo)
        self.connections_repo.register(conn)

    def propagate(self):
        for _, conn in self.connections_repo.items():
            conn.propagate(self.elements_repo)

    def calculate_all(self):
        for _, elem in self.elements_repo.items():
            try:
                elem.calculate()
            except NotImplementedError:
                pass

    def scheme_info(self) -> str:
        lines = ["=== Scheme Elements ==="]
        for _, elem in self.elements_repo.items():
            lines.append(f"  {elem.name}")
        lines.append("\n=== Connections ===")
        for _, conn in self.connections_repo.items():
            lines.append(str(conn))
        return "\n".join(lines)