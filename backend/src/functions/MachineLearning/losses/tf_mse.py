from backend.src.Core.Port import Port
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import Value, ValueClass, ValueStatus
from backend.src.utils.core_elements import repos_test_condition
from backend.src.Core.ElementProxy import ElementIO
import tensorflow as tf

def calculate(io: ElementIO):
    if io.require(params=['reduction'], raise_exception=False):
        io.set()
    if parameters['reduction'].status != ValueStatus.UNKNOWN:
        out_ports['LossFunction'].LossFuncObject = (tf.keras.losses.MeanSquaredError(parameters['reduction'].value), 'calculated')
    else:
        out_ports['LossFunction'].LossFuncObject = (tf.keras.losses.MeanSquaredError(), 'calculated')
        