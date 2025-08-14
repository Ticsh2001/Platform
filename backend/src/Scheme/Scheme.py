from __future__ import annotations

import uuid
from typing import Dict, Tuple, Optional, List, Iterable, Set, Union, Any

import networkx as nx

from backend.src.Core.Element import Element
from backend.src.Core.Port import Port
from backend.src.Core.Value import Value, ValueStatus
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Connection import Connection

class Scheme:
    def __init__(self, name: str = "Scheme"):
        self._name = name
        self._elements = ObjectRepository[Element](rep_type="element")
        self._connections = ObjectRepository[Connection](rep_type="connection")

        self.G: nx.DiGraph = nx.DiGraph()
        self._port_index: Dict[uuid.UUID, Tuple[Element, Port, int]] = {}   # 0=in, 1=out
        self._value_index: Dict[uuid.UUID, Value] = {}                      # параметры и значения портов

        self._conn_name_counter: int = 0

    # --- генерация уникального имени соединения без '_' ---
    def _connection_name_taken(self, nm: str) -> bool:
        for _, c in self._connections.items():
            if getattr(c, "name", None) == nm:
                return True
        return False
    
    # ---------- служебное имя для Connection ----------
    def _gen_connection_name(self) -> str:
        # генерируем C1, C2, ... избегая коллизий
        while True:
            self._conn_name_counter += 1
            name = f"C{self._conn_name_counter}"
            if not self._connection_name_taken(name):
                return name

    # ------------------------------
    # Регистрация элементов
    # ------------------------------
    def add_element(self, element: Element) -> uuid.UUID:
        self._elements.register(element)
        elem_id = self._elements.registered_ids[-1]
        for pid, port in element.in_ports.items():
            self._port_index[pid] = (element, port, 0)
            self.G.add_node(pid)
            for vid, val in port:
                self._value_index[vid] = val
        for pid, port in element.out_ports.items():
            self._port_index[pid] = (element, port, 1)
            self.G.add_node(pid)
            for vid, val in port:
                self._value_index[vid] = val
        for vid, val in element.parameters.items():
            self._value_index[vid] = val
        for group in element.get_internal_connection_groups_ids():
            if not group:
                continue
            in_ids = [pid for pid in group if pid in element.in_ports.registered_ids]
            out_ids = [pid for pid in group if pid in element.out_ports.registered_ids]
            if not in_ids or not out_ids:
                continue
            for i_id in in_ids:
                for o_id in out_ids:
                    self.G.add_edge(i_id, o_id, internal=True, edge_id="internal", connection_id=None)
        return elem_id

    # ------------------------------
    # Создание внешних связей
    # ------------------------------
    def add_connection(self, conn: Connection) -> uuid.UUID:
        # назначаем имя до регистрации; без '_' и уникально
        conn.name = self._gen_connection_name()

        # проверяем валидность
        conn.validate(self._elements, raise_error=True)

        # регистрируем в репозитории
        self._connections.register(conn)
        conn_id = self._connections.registered_ids[-1]

        # отмечаем ребро в графе
        self.G.add_node(conn.out_port_id); self.G.add_node(conn.in_port_id)
        self.G.add_edge(conn.out_port_id, conn.in_port_id,
                        internal=False, edge_id=conn_id, connection_id=conn_id)
        return conn_id

    def connect_ids(self,
                    out_elem_id: uuid.UUID, out_port_id: uuid.UUID,
                    in_elem_id: uuid.UUID, in_port_id: uuid.UUID) -> uuid.UUID:
        conn = Connection(out_elem_id, out_port_id, in_elem_id, in_port_id)
        return self.add_connection(conn)

    # старый интерфейс по объектам — оставляем
    def connect(self,
                src: Tuple[Element, Union[str, uuid.UUID]],
                dst: Tuple[Element, Union[str, uuid.UUID]]) -> uuid.UUID:
        src_elem, src_port = src
        dst_elem, dst_port = dst
        src_pid = self._resolve_port_id(src_elem, src_port, expect_kind=1)
        dst_pid = self._resolve_port_id(dst_elem, dst_port, expect_kind=0)
        src_elem_id = self._find_element_id(src_elem)
        dst_elem_id = self._find_element_id(dst_elem)
        return self.connect_ids(src_elem_id, src_pid, dst_elem_id, dst_pid)

    def _find_element_id(self, element: Element) -> uuid.UUID:
        for eid, e in self._elements.items():
            if e is element:
                return eid
        raise KeyError(f"Элемент {getattr(element, 'name', '<unknown>')} не зарегистрирован в схеме")

    def _resolve_port_id(self, element: Element, port: Union[str, uuid.UUID], expect_kind: Optional[int]) -> uuid.UUID:
        if isinstance(port, uuid.UUID):
            pid = port
            is_in = element.in_ports.get_by_id(pid) is not None
            is_out = element.out_ports.get_by_id(pid) is not None
            if not (is_in or is_out):
                raise KeyError(f"Порт {pid} не принадлежит элементу {element.name}")
            actual = 0 if is_in else 1
            if expect_kind is not None and actual != expect_kind:
                raise ValueError("Тип порта не соответствует ожидаемому")
            return pid
        p = element.in_ports.get_by_name(port)
        if p:
            if expect_kind in (None, 0):
                for pid, pobj in element.in_ports.items():
                    if pobj is p:
                        return pid
            raise ValueError(f"Порт '{port}' — входной, ожидался выходной")
        p = element.out_ports.get_by_name(port)
        if p:
            if expect_kind in (None, 1):
                for pid, pobj in element.out_ports.items():
                    if pobj is p:
                        return pid
            raise ValueError(f"Порт '{port}' — выходной, ожидался входной")
        raise KeyError(f"Порт '{port}' не найден у элемента {element.name}")

    # Вариант резолва порта по element_id и имени (для верхнего уровня по ID)
    def resolve_port_id_by_name(self, element_id: uuid.UUID, port_name: str) -> uuid.UUID:
        elem = self._elements.get_by_id(element_id)
        if not elem:
            raise KeyError(f"Элемент с id {element_id} не найден")
        p = elem.in_ports.get_by_name(port_name) or elem.out_ports.get_by_name(port_name)
        if not p:
            raise KeyError(f"Порт '{port_name}' не найден у элемента {elem.name}")
        for pid, pobj in list(elem.in_ports.items()) + list(elem.out_ports.items()):
            if pobj is p:
                return pid
        raise KeyError("ID порта не найден (внутренняя ошибка)")

    # ------------------------------
    # Доступ по ID
    # ------------------------------
    def get_element_by_id(self, element_id: uuid.UUID) -> Optional[Element]:
        return self._elements.get_by_id(element_id)

    def get_connection_by_id(self, connection_id: uuid.UUID) -> Optional[Connection]:
        return self._connections.get_by_id(connection_id)

    def get_port_by_id(self, port_id: uuid.UUID) -> Optional[Port]:
        return self._port_index.get(port_id, (None, None, None))[1]

    def get_value_by_id(self, value_id: uuid.UUID) -> Optional[Value]:
        return self._value_index.get(value_id)

    def get_object_by_id(self, obj_id: Union[uuid.UUID, str]) -> Optional[Any]:
        if isinstance(obj_id, uuid.UUID) and obj_id in self._port_index:
            return self._port_index[obj_id][1]
        if isinstance(obj_id, uuid.UUID) and obj_id in self._value_index:
            return self._value_index[obj_id]
        e = self._elements.get_by_id(obj_id) if isinstance(obj_id, uuid.UUID) else None
        if e is not None:
            return e
        c = self._connections.get_by_id(obj_id) if isinstance(obj_id, uuid.UUID) else None
        return c

    def ids_to_elements(self) -> Dict[uuid.UUID, Element]:
        return {eid: elem for eid, elem in self._elements.items()}

    def ids_to_ports(self) -> Dict[uuid.UUID, Port]:
        return {pid: port for pid, (_, port, _) in self._port_index.items()}

    def ids_to_values(self) -> Dict[uuid.UUID, Value]:
        return dict(self._value_index)

    def ids_to_connections(self) -> Dict[uuid.UUID, Connection]:
        return {cid: c for cid, c in self._connections.items()}

    # ------------------------------
    # Удобные операции по ID
    # ------------------------------
    def set_param_by_element_id(self, element_id: uuid.UUID, name: str, value: Any,
                                status: Union[ValueStatus, str] = ValueStatus.CALCULATED):
        elem = self._elements.get_by_id(element_id)
        if not elem:
            raise KeyError(f"Element {element_id} not found")
        v = elem.parameters.get_by_name(name)
        if not v:
            raise KeyError(f"Parameter '{name}' not found in element {elem.name}")
        v.update(value, ValueStatus.from_input(status))

    def set_port_value_by_port_id(self, port_id: uuid.UUID, value_name: str, value: Any,
                                  status: Union[ValueStatus, str] = ValueStatus.CALCULATED):
        port = self.get_port_by_id(port_id)
        if not port:
            raise KeyError(f"Port {port_id} not found")
        v = port.get_value(value_name)
        if not v:
            raise KeyError(f"Value '{value_name}' not found in port")
        v.update(value, ValueStatus.from_input(status))

    def propagate_connection_by_id(self, connection_id: uuid.UUID):
        conn = self.get_connection_by_id(connection_id)
        if not conn:
            raise KeyError(f"Connection {connection_id} not found")
        conn.propagate(self._elements)

    def calculate_element_by_id(self, element_id: uuid.UUID):
        elem = self._elements.get_by_id(element_id)
        if not elem:
            raise KeyError(f"Element {element_id} not found")
        try:
            elem.calculate()
        except NotImplementedError:
            pass
        if getattr(elem, "update_internal_connections", None):
            elem.update_internal_connections()

    # ------------------------------
    # Распространение и расчёты
    # ------------------------------
    def propagate_known_values(self, both_directions: bool = True) -> int:
        moved = 0
        for u, v, data in self.G.edges(data=True):
            if data.get("internal", False):
                continue
            # используем Connection, если есть
            conn_id = data.get("connection_id")
            conn = self._connections.get_by_id(conn_id) if conn_id else None
            if conn:
                before = self.node_status_summary_for_edge(u, v)
                conn.propagate(self._elements)
                after = self.node_status_summary_for_edge(u, v)
                moved += 1 if before != after else 0
            else:
                moved += self._propagate_port_to_port(u, v)
                if both_directions:
                    moved += self._propagate_port_to_port(v, u)
        return moved

    def _propagate_port_to_port(self, pid_from: uuid.UUID, pid_to: uuid.UUID) -> int:
        port_from = self._port_index[pid_from][1]
        port_to = self._port_index[pid_to][1]
        cnt = 0
        for _, v_src in port_from:
            v_dst = port_to.get_value(v_src.name)
            if not v_dst:
                continue
            if v_src.status in (ValueStatus.CALCULATED, ValueStatus.FIXED) and v_dst.status == ValueStatus.DEPEND:
                v_dst.update(v_src.value, ValueStatus.DEPEND)
                cnt += 1
        return cnt

    def node_status_summary_for_edge(self, u: uuid.UUID, v: uuid.UUID) -> tuple:
        # небольшая утилита для оценки изменений (по именам и статусам)
        pf = self._port_index[u][1]; pt = self._port_index[v][1]
        return (tuple((n, pf.get_value(n).status.name) for n in pf._values.registered_base_names),
                tuple((n, pt.get_value(n).status.name) for n in pt._values.registered_base_names))

    def _elements_dag(self) -> nx.DiGraph:
        dag = nx.DiGraph()
        for _, e in self._elements.items():
            dag.add_node(e)
        for u, v, data in self.G.edges(data=True):
            if data.get("internal", False):
                continue
            elem_u = self._port_index[u][0]
            elem_v = self._port_index[v][0]
            if elem_u is not elem_v:
                dag.add_edge(elem_u, elem_v)
        return dag

    def run_calculations(self, propagate_each_step: bool = True) -> None:
        try:
            order = list(nx.topological_sort(self._elements_dag()))
        except nx.NetworkXUnfeasible:
            order = [e for _, e in self._elements.items()]
        for elem in order:
            try:
                elem.calculate()
            except NotImplementedError:
                pass
            if getattr(elem, "update_internal_connections", None):
                elem.update_internal_connections()
            if propagate_each_step:
                self.propagate_known_values(both_directions=True)

    # ------------------------------
    # Отчёты
    # ------------------------------
    def node_status_summary(self, external_only: bool = True):
        involved: Set[uuid.UUID]
        if external_only:
            involved = set()
            for u, v, d in self.G.edges(data=True):
                if not d.get("internal", False):
                    involved.add(u); involved.add(v)
        else:
            involved = set(self.G.nodes())
        summary = {}
        for pid in involved:
            _, port, _ = self._port_index[pid]
            summary[pid] = {
                "fixed": port.list_by_status(ValueStatus.FIXED),
                "calculated": port.list_by_status(ValueStatus.CALCULATED),
                "depend": port.list_by_status(ValueStatus.DEPEND),
                "unknown": port.list_by_status(ValueStatus.UNKNOWN)
            }
        return summary

    def describe(self) -> str:
        ext = sum(1 for _, _, d in self.G.edges(data=True) if not d.get("internal", False))
        total = self.G.number_of_edges()
        return f"Scheme '{self._name}': elements={len(self._elements)}, ports={self.G.number_of_nodes()}, edges={total} (external={ext}, internal={total - ext})"