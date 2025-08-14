from backend.src.Core.Port import Port
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import Value, ValueClass, ValueStatus
from backend.src.utils.core_elements import repos_test_condition
import tensorflow as tf

def calculate(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    if parameters['reduction'].status != ValueStatus.UNKNOWN:
        out_ports['LossFunction'].LossFuncObject = (tf.keras.losses.MeanSquaredError(parameters['reduction'].value), 'calculated')
    else:
        out_ports['LossFunction'].LossFuncObject = (tf.keras.losses.MeanSquaredError(), 'calculated')
        