from backend.src.Core.Value import Value, ValueClass, ValueStatus
import tensorflow as tf

def loss_function(func_name: Value, func_options=None):
    registered_funcs = {"binary_cross_entropy": ["from_logits", "label_smoothing", "axis", "reduction"],
                       

    }
    if func_name.status == ValueStatus.UNKNOWN or func_name.value not in registered_funcs:
        return None
    if func_name.value == "binary_cross_entropy":
        

