from Core.Element import Element

class ElementWrapper:
    def __init__(self, element: Element):
        self.element = element
        self._parents = dict()
        self._childs = dict()

    def _validate_port(name, element, inlet=True):
        


    def add_parent(self, port_name, parent, parent_port_name):

        self._parents[port_name] = (parent.element, parent_port_name)



