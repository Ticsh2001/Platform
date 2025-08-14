from backend.src.Core.Port import Port
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import Value, ValueClass, ValueStatus
from backend.src.utils.core_elements import get_values
import tensorflow as tf

def setup_element(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    parameters.register(Value('AdamOptions', ValueClass(), 
                              value={'LearningRate': ("learning_rate", 0.001),
                                     'beta1': ('beta_1', 0.9),
                                     'beta2': ('beta_2', 0.999),
                                     'epsilon': ('epsilon', 1e-07),
                                     'amsgrad': ('amsgrad', False),
                                     'WeightDecay': ('weight_decay', None),
                                     'clipnorm': ('clipnorm', None),
                                     'clipvalue': ('clipvalue', None),
                                     'GlobalClipnorm': ('global_clipnorm', None),
                                     'UseEma': ('use_ema', False),
                                     'EmaMomentum': ('ema_momentum', 0.99),
                                     'EmaOverwriteFrequency': ('ema_overwrite_frequency', None),
                                     'LossScaleFactor': ('loss_scale_factor', None),
                                     'GradientAccumulationSteps': ('gradient_accumulation_steps', None)}, status=ValueStatus.FIXED))


def calculate(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    adam_options = parameters['AdamOptions'].value
    parameters = get_values(parameters, list(adam_options.keys()))
    out_ports['Optimizer'].OptimizerObject = (tf.keras.optimizers.Adam(**{adam_options[key][0]: val if val is not None else adam_options[key][1] for key, val in parameters.items()}), 'calculated')
        