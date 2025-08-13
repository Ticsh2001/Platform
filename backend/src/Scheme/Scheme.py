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
        self._value_index: Dict[uuid.UUID, Value] = {}                     # все значения (параметры и значения портов)

    # ------------------------------
    # Регистрация элементов/связей
    # ------------------------------
    def add_element(self, element: Element) -> uuid.UUID:
        self._elements.register(element)
        # получим id добавленного элемента
        elem_id = self._elements.registered_ids[-1]

        # Индексация портов и значений
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

        # Параметры элемента → индекс значений
        for vid, val in element.parameters.items():
            self._value_index[vid] = val

        # Внутренние связи — группы id портов
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

    def connect(self,
                src: Tuple[Element, Union[str, uuid.UUID]],
                dst: Tuple[Element, Union[str, uuid.UUID]]) -> uuid.UUID:
        src_elem, src_port = src
        dst_elem, dst_port = dst
        src_pid = self._resolve_port_id(src_elem, src_port, expect_kind=1)
        dst_pid = self._resolve_port_id(dst_elem, dst_port, expect_kind=0)

        conn = Connection(src_elem, src_pid, dst_elem, dst_pid)
        self._connections.register(conn)
        conn_id = self._connections.registered_ids[-1]

        self.G.add_node(src_pid); self.G.add_node(dst_pid)
        self.G.add_edge(src_pid, dst_pid, internal=False, edge_id=conn_id, connection_id=conn_id)
        return conn_id

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

    # ------------------------------
    # Доступ по ID и словари id->obj
    # ------------------------------
    def get_object_by_id(self, obj_id: Union[uuid.UUID, str]) -> Optional[Any]:
        # порядок: порт -> значение -> элемент -> связь
        if isinstance(obj_id, uuid.UUID) and obj_id in self._port_index:
            return self._port_index[obj_id][1]
        if isinstance(obj_id, uuid.UUID) and obj_id in self._value_index:
            return self._value_index[obj_id]
        for eid, elem in self._elements.items():
            if eid == obj_id:
                return elem
        for cid, conn in self._connections.items():
            if cid == obj_id:
                return conn
        return None

    def ids_to_elements(self) -> Dict[uuid.UUID, Element]:
        return {eid: elem for eid, elem in self._elements.items()}

    def ids_to_ports(self) -> Dict[uuid.UUID, Port]:
        return {pid: port for pid, (_, port, _) in self._port_index.items()}

    def ids_to_values(self) -> Dict[uuid.UUID, Value]:
        return dict(self._value_index)

    # ------------------------------
    # Удобные операции
    # ------------------------------
    def set_value_by_id(self, value_id: uuid.UUID, value: Any, status: Union[ValueStatus, str] = ValueStatus.CALCULATED):
        val = self._value_index.get(value_id)
        if not val:
            raise KeyError(f"Value id {value_id} not found")
        val.update(value, ValueStatus.from_input(status))

    def set_param(self, element: Element, name: str, value: Any, status: Union[ValueStatus, str] = ValueStatus.CALCULATED):
        v = element.parameters.get_by_name(name)
        if not v:
            raise KeyError(f"Parameter '{name}' not found in element {element.name}")
        v.update(value, ValueStatus.from_input(status))
        # индекс уже хранит id -> объект, сам объект тот же

    def set_port_value(self, element: Element, port_name: str, value_name: str, value: Any,
                       status: Union[ValueStatus, str] = ValueStatus.CALCULATED):
        port = element.in_ports.get_by_name(port_name) or element.out_ports.get_by_name(port_name)
        if not port:
            raise KeyError(f"Port '{port_name}' not found in element {element.name}")
        v = port.get_value(value_name)
        if not v:
            raise KeyError(f"Value '{value_name}' not found in port {port_name} of element {element.name}")
        v.update(value, ValueStatus.from_input(status))

    def connect_by_names(self, src_element: Element, src_port: str, dst_element: Element, dst_port: str) -> uuid.UUID:
        return self.connect((src_element, src_port), (dst_element, dst_port))

    # ------------------------------
    # Аналитика/выполнение
    # ------------------------------
    def propagate_known_values(self, both_directions: bool = True) -> int:
        moved = 0
        for u, v, data in self.G.edges(data=True):
            if data.get("internal", False):
                continue
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

    # Вспомогательное
    def describe(self) -> str:
        ext = sum(1 for _, _, d in self.G.edges(data=True) if not d.get("internal", False))
        total = self.G.number_of_edges()
        return f"Scheme '{self._name}': elements={len(self._elements)}, ports={self.G.number_of_nodes()}, edges={total} (external={ext}, internal={total - ext})"