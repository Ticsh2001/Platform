from backend.src.Core.Port import Port
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import Value, ValueClass, ValueStatus
from backend.src.utils.core_elements import repos_test_condition
from backend.src.utils.core_elements import get_values
from backend.src.utils.NeuralTools.Block_Struct import BlockStruct, create_neural_model
import tensorflow as tf
import json

def create_model(name: str, x_shape: int, structure: str, options: dict):
    return create_neural_model(BlockStruct(name, structure, options=options), tf.keras.Input(shape=(x_shape)))


def setup_element(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    pass


def calculate(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    if repos_test_condition([in_ports, out_ports, parameters], ['X_Train', 'Y_Train', 'Arhitecture', 'ModelOptions', 
                                                                'LossFuncObject_LossFunction', 'OptimizerObject_Optimizer', 'epochs']):
        main_data = get_values([in_ports, parameters], ['X_Train', 'Y_Train', 'Arhitecture', 'ModelOptions'])

        model = create_model(in_ports.prefics, main_data['X_Train'].shape[1], 
                             main_data['Arhitecture'], 
                             json.loads(main_data['ModelOptions']))
        loss = in_ports['LossFunction'].LossFuncObject.value
        optimizer = in_ports['Optimizer'].OptimizerObject.value
        compile_params = get_values([in_ports], ['CallBackObject_Callbacks', 'MetricsObjects_Metrics'])
        model.compile(optimzer=optimizer, loss=loss)
        if repos_test_condition([in_ports], ['X_Val', 'y_Val']):
            val = (in_ports['Val'].X[0], in_ports['Val'].y[0])
        else:
            val = None
        model.fit(main_data['X_Train'], main_data['Y_Train'], epochs=main_data['epochs'], validation_data=val)
        out_ports['Model'].NeuralModel = (model, 'calculated')    

