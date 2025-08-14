import uuid
from typing import Dict, Optional, List, Tuple
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import ValueStatus, Value, ValueClass

class Connection:
    """
    Внешняя связь out_elem.out_port -> in_elem.in_port.
    Имя должен назначать Scheme. При прямом создании — безопасный уникальный fallback.
    """
    def __init__(self,
                 out_elem_id: uuid.UUID,
                 out_port_id: uuid.UUID,
                 in_elem_id: uuid.UUID,
                 in_port_id: uuid.UUID,
                 name: Optional[str] = None):
        self.name = name or f"c{uuid.uuid4().hex[:8]}"
        self.out_elem_id = out_elem_id
        self.out_port_id = out_port_id
        self.in_elem_id = in_elem_id
        self.in_port_id = in_port_id

    @staticmethod
    def _collect_by_spec(port) -> Dict[ValueClass, List[Value]]:
        """
        Группирует значения порта по спецификации ValueClass.
        Порядок в списке — порядок регистрации значений в порту.
        """
        grouped: Dict[ValueClass, List[Value]] = {}
        for _, val in port:                    # предполагается: for (value_id, value) in port
            spec = val.value_spec              # требует property value_spec в Value
            grouped.setdefault(spec, []).append(val)
        return grouped

    def validate(self, element_repo: ObjectRepository, raise_error: bool = True) -> bool:
        """
        Проверка совместимости портов по спецификациям значений:
        - одинаковые наборы ValueClass,
        - совпадает кратность каждой спецификации (число значений данного типа).
        Имена значений могут отличаться.
        """
        out_elem = element_repo.get_by_id(self.out_elem_id)
        in_elem = element_repo.get_by_id(self.in_elem_id)

        if out_elem is None or in_elem is None:
            if raise_error:
                raise ValueError("Элемент(ы) связи не найдены в репозитории")
            return False

        out_port = out_elem.out_ports.get_by_id(self.out_port_id)
        in_port = in_elem.in_ports.get_by_id(self.in_port_id)

        # направление
        if out_port is None:
            if raise_error:
                raise ValueError("Выходной порт не найден в out_ports указанного элемента")
            return False
        if in_port is None:
            if raise_error:
                raise ValueError("Входной порт не найден в in_ports указанного элемента")
            return False

        out_specs = self._collect_by_spec(out_port)
        in_specs = self._collect_by_spec(in_port)

        # Сравниваем наборы спецификаций
        if set(out_specs.keys()) != set(in_specs.keys()):
            if raise_error:
                missing_out = set(in_specs.keys()) - set(out_specs.keys())
                missing_in = set(out_specs.keys()) - set(in_specs.keys())
                raise ValueError(f"Порты несовместимы по спецификациям: "
                                 f"только у входа={list(missing_out)}, только у выхода={list(missing_in)}")
            return False

        # Сравниваем кратности по каждой спецификации
        for spec in out_specs.keys():
            if len(out_specs[spec]) != len(in_specs[spec]):
                if raise_error:
                    raise ValueError(f"Разная кратность спецификации {spec}: "
                                     f"выход={len(out_specs[spec])}, вход={len(in_specs[spec])}")
                return False

        return True

    def propagate(self, element_repo: ObjectRepository):
        """
        Передача значений по совпадающим спецификациям:
        - если у источника CALCULATED/FIXED, а у приёмника DEPEND, копируем;
        - иначе, если наоборот, копируем в обратную сторону.
        Если кратность > 1 — копируем попарно по индексу регистрации.
        """
        out_elem = element_repo.get_by_id(self.out_elem_id)
        in_elem = element_repo.get_by_id(self.in_elem_id)
        out_port = out_elem.out_ports.get_by_id(self.out_port_id)
        in_port = in_elem.in_ports.get_by_id(self.in_port_id)

        out_specs = self._collect_by_spec(out_port)
        in_specs = self._collect_by_spec(in_port)

        # Идём по пересечению спецификаций (validate должен гарантировать полное соответствие)
        for spec in out_specs.keys() & in_specs.keys():
            out_list: List[Value] = out_specs[spec]
            in_list: List[Value] = in_specs[spec]
            # предполагается одинаковая длина списков
            for v_out, v_in in zip(out_list, in_list):
                if v_out.status in (ValueStatus.CALCULATED, ValueStatus.FIXED) and v_in.status == ValueStatus.DEPEND:
                    v_in.update(v_out.value, ValueStatus.DEPEND)
                    continue
                if v_in.status in (ValueStatus.CALCULATED, ValueStatus.FIXED) and v_out.status == ValueStatus.DEPEND:
                    v_out.update(v_in.value, ValueStatus.DEPEND)

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
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
            uuid.UUID(data["in_port"]),
            name=data.get("name")
        )