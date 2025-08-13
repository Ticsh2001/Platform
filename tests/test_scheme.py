from backend.src.Scheme.Scheme import Scheme
from backend.src.Factory.ElementFactory import ElementFactory
from backend.src.Core.Value import ValueStatus

# 1) Создаём фабрику и схему
ef = ElementFactory('backend/configs/value_classes.json',
                    'backend/configs/ports.json',
                    'backend/configs/elements')
scheme = Scheme("ML pipeline")

# 2) Создаём элемент Dataset из конфигурации
dataset_elem = ef.create_element("Dataset")  # имя файла dataset.json в каталоге elements
scheme.add_element(dataset_elem)

# 3) Задаём вход и параметры
# На входной порт RawData -> значение 'test.xlsx'
scheme.set_port_value(dataset_elem, "RawData", "data", "test.xlsx", ValueStatus.FIXED)

# Параметры: Seed=42 (fixed), SplitRatio=0.2 (fixed), XFields=[0,1], YFields=[2]
scheme.set_param(dataset_elem, "Seed", 42, ValueStatus.FIXED)
scheme.set_param(dataset_elem, "SplitRatio", 0.2, ValueStatus.FIXED)
scheme.set_param(dataset_elem, "XFields", [0, 1], ValueStatus.FIXED)
scheme.set_param(dataset_elem, "YFields", [2], ValueStatus.FIXED)

# 4) Запускаем расчёт
scheme.run_calculations()

# 5) Смотрим результат
train_port = dataset_elem.out_ports.get_by_name("Train")
val_port = dataset_elem.out_ports.get_by_name("Val")
Xtr = train_port.get_value("X").value
ytr = train_port.get_value("y").value
Xv  = val_port.get_value("X").value
yv  = val_port.get_value("y").value
print("Train shapes:", getattr(Xtr, "shape", None), getattr(ytr, "shape", None))
print("Val shapes:", getattr(Xv, "shape", None), getattr(yv, "shape", None))