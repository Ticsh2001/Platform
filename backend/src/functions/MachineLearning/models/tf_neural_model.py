from backend.src.Core.Value import ValueStatus
from backend.src.Core.ElementProxy import ElementIO, requires
from backend.src.utils.NeuralTools.Block_Struct import BlockStruct, create_neural_model
from typing import Any
import tensorflow as tf
import json

def setup_element(io: ElementIO):
    pass

@requires(inputs=['val.x', 'val.y'])
def validation_data(io: ElementIO) -> Any:
    return (io.inputs.val.x.get(), io.inputs.val.y.get())

@requires(inputs=['callbacks.callback_object'])
def callback_functions(io: ElementIO) -> Any:
    return io.inputs.callbacks.callback_object.get()

def create_model(name: str, x_shape: int, structure: str, options: dict):
    model_options = json.loads(options) if isinstance(options, str) and options.strip() else (options or {})
    return create_neural_model(BlockStruct(name, structure,
                                           options=model_options),
                               tf.keras.Input(shape=(x_shape,)))

@requires(inputs=['train.x', 'train.y',
                  'loss_function.loss_function_object',
                  'optimizer.optimizer_object'],
          params=['epochs', 'architecture', 'model_options'])
def calculate(io: ElementIO):
    train_data =  io.get_mul(['train.x', 'train.y'])
    model = create_model(name=io.name, x_shape=train_data['train.x'].shape[1],
                         structure=io.get('architecture'),
                         options=io.get('model_options'))
    loss_func = io.inputs.loss_function.loss_function_object.get()
    optimizer = io.inputs.optimizer.optimizer_object.get()
    callback_funcs = callback_functions(io)
    model.compile(optimzer=optimizer, loss=loss_func)
    model.fit(train_data['train.x'], train_data['train.y'],
              epochs=io.get('epochs'), validation_data=validation_data(io),
              callbacks=callback_funcs)
    io.set('model.neural_model', model, ValueStatus.CALCULATED)