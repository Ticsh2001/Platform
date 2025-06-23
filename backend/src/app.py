from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import uuid
import os
from ElementFactory import ElementFactory

app = Flask(__name__)
CORS(app)

# Инициализация фабрики элементов
config_dir = os.path.join(os.path.dirname(__file__), 'element_configs')
element_factory = ElementFactory(config_dir)

# Хранилище проекта
project = {
    'elements': {},
    'connections': []
}

class ElementWrapper:
    def __init__(self, element, x=100, y=100):
        self.element = element
        self.x = x
        self.y = y
        self.width = 200
        self.height = 150
        self.input_ports = self._generate_port_positions('in')
        self.output_ports = self._generate_port_positions('out')
    
    def _generate_port_positions(self, port_type):
        ports = self.element.in_ports if port_type == 'in' else self.element.out_ports
        return [{
            'id': str(port.id),
            'x': 0 if port_type == 'in' else self.width,
            'y': (i + 1) * self.height / (len(ports) + 1)
        } for i, port in enumerate(ports)]
    
    def get_ui_config(self):
        return {
            'id': str(self.element.id),
            'name': self.element.name,
            'type': type(self.element).__name__,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'input_ports': self.input_ports,
            'output_ports': self.output_ports,
            'parameters': [
                {
                    'name': name,
                    'value': value.value,
                    'dimension': value.dimension,
                    'status': value.status.name
                } for name, value in self.element.parameters.items()
            ]
        }

# API для работы с элементами
@app.route('/api/element-types', methods=['GET'])
def get_element_types():
    """Возвращает список доступных типов элементов"""
    return jsonify(list(element_factory.templates.keys()))

@app.route('/api/elements', methods=['POST'])
def create_element():
    data = request.json
    element_type = data['type']
    name = data.get('name', f'New {element_type}')
    x = data.get('x', 100)
    y = data.get('y', 100)
    
    try:
        element = element_factory.create_element(element_type, name)
        wrapper = ElementWrapper(element, x, y)
        element_id = str(element.id)
        project['elements'][element_id] = wrapper
        
        return jsonify(wrapper.get_ui_config()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/elements/<element_id>', methods=['PUT'])
def update_element(element_id):
    if element_id not in project['elements']:
        return jsonify({'error': 'Element not found'}), 404
    
    wrapper = project['elements'][element_id]
    data = request.json
    
    # Обновление позиции
    if 'x' in data: wrapper.x = data['x']
    if 'y' in data: wrapper.y = data['y']
    
    # Обновление параметров
    if 'parameters' in data:
        for param in data['parameters']:
            if param['name'] in wrapper.element.parameters:
                value_obj = wrapper.element.parameters[param['name']]
                value_obj.update(param['value'], param.get('status', 'FIXED'))
    
    return jsonify(wrapper.get_ui_config())

# API для работы со связями
@app.route('/api/connections', methods=['POST'])
def create_connection():
    data = request.json
    connection_id = str(uuid.uuid4())
    
    # Проверка существования элементов и портов
    source_element = project['elements'].get(data['source']['element_id'])
    target_element = project['elements'].get(data['target']['element_id'])
    
    if not source_element or not target_element:
        return jsonify({'error': 'Element not found'}), 404
    
    connection = {
        'id': connection_id,
        'source': data['source'],
        'target': data['target']
    }
    
    project['connections'].append(connection)
    return jsonify(connection), 201

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """Запуск расчета всей системы"""
    # TODO: Реализовать вычислительную логику
    return jsonify({'status': 'success', 'message': 'Calculation completed'})

if __name__ == '__main__':
    app.run(debug=True)