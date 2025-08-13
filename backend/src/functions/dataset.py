from backend.src.Core.Port import Port
from backend.src.Core.ObjectRepository import ObjectRepository
from backend.src.Core.Value import Value, ValueClass, ValueStatus
from backend.src.utils.core_elements import repos_test_condition
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd

def setup_element(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    if in_ports[0][1].is_calculated:
        data = in_ports[0][1]['data']
        if data.value_type == 'str':
            if data.value.endswith('.xlsx'):
                df = pd.read_excel(data.value)
                X_fields = [i for i in range(len(df.columns) - 1)]
                Y_fields = [len(df.columns)-1]
                if parameters['KeepData'].value == 1:
                    parameters['RawData'].update(df.to_numpy(), 'calculated')
        else:
            pass
        parameters['XFields'].update(X_fields, 'calculated')
        parameters['YFields'].update(Y_fields, 'calculated')

def calculate(in_ports: ObjectRepository, out_ports: ObjectRepository, parameters: ObjectRepository):
    known_values = ['data_RawData', 'XFields', 'YFields']
    if repos_test_condition([in_ports, out_ports, parameters], known_names=known_values):
        if parameters['RawData'].status != ValueStatus.CALCULATED:
            parameters['RawData'].update(pd.read_excel(in_ports[0][1]['data'].value).to_numpy(), 'calculated')
        if parameters['SplitRatio'].status == ValueStatus.UNKNOWN:
            parameters['SplitRatio'].update(None, 'calculated')
        if parameters['Seed'].status == ValueStatus.UNKNOWN:
            parameters['Seed'].update(None, 'calculated')
        X_train, X_val, y_train, y_val = train_test_split(parameters['RawData'].value[:, parameters['XFields'].value],
                                                            parameters['RawData'].value[:, parameters['YFields'].value],
                                                            test_size=parameters['SplitRatio'].value,
                                                            random_state=parameters['Seed'].value)
        out_ports['Train'].X = (X_train, 'calculated')
        out_ports['Train'].y = (y_train, 'calculated')
        out_ports['Val'].X = (X_val, 'calculated')
        out_ports['Val'].y = (y_val, 'calculated')
        if parameters['KeepData'].value == 0:
            parameters.RawData = (None, ValueStatus.UNKNOWN)





