import uuid
from typing import Dict
from backend.src.Core.Value import ValueStatus
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Element import Element

class Connection:
    def __init__(self,
                 out_elem_id: uuid.UUID,
                 out_port_id: uuid.UUID,
                 in_elem_id: uuid.UUID,
                 in_port_id: uuid.UUID):
        self.out_elem_id = out_elem_id
        self.out_port_id = out_port_id
        self.in_elem_id = in_elem_id
        self.in_port_id = in_port_id

    def validate(self, element_repo: ObjectRepository, raise_error: bool = True) -> bool:
        """Проверка совместимости портов + что они находятся в правильных направлениях"""
        out_elem = element_repo.get_by_id(self.out_elem_id)
        in_elem = element_repo.get_by_id(self.in_elem_id)

        out_port = out_elem.out_ports.get_by_id(self.out_port_id)
        in_port = in_elem.in_ports.get_by_id(self.in_port_id)

        # Проверка правильности направления
        if out_port is None:
            if raise_error:
                raise ValueError("Выходной порт не найден в out_ports")
            return False
        if in_port is None:
            if raise_error:
                raise ValueError("Входной порт не найден в in_ports")
            return False

        # Проверка совместимости по Value
        if out_port != in_port:
            if raise_error:
                raise ValueError("Порты несовместимы по структуре Value")
            return False
        return True

    def propagate(self, element_repo: ObjectRepository):
        """Передача значений между портами при расчёте"""
        out_elem = element_repo.get_by_id(self.out_elem_id)
        in_elem = element_repo.get_by_id(self.in_elem_id)

        out_port = out_elem.out_ports.get_by_id(self.out_port_id)
        in_port = in_elem.in_ports.get_by_id(self.in_port_id)

        for val_name in out_port._values.registered_base_names:
            v_out = out_port.get_value(val_name)
            v_in = in_port.get_value(val_name)
            if v_out.status == ValueStatus.CALCULATED or v_out.status == ValueStatus.FIXED:
                v_in.update(v_out.value, ValueStatus.DEPEND)
            elif v_in.status == ValueStatus.CALCULATED or v_in.status == ValueStatus.FIXED:
                v_out.update(v_in.value, ValueStatus.DEPEND)

    def as_dict(self) -> Dict:
        return {
            "out_elem": str(self.out_elem_id),
            "out_port": str(self.out_port_id),
            "in_elem": str(self.in_elem_id),
            "in_port": str(self.in_port_id)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Connection":
        return cls(
            uuid.UUID(data["out_elem"]),
            uuid.UUID(data["out_port"]),
            uuid.UUID(data["in_elem"]),
            uuid.UUID(data["in_port"])
        )