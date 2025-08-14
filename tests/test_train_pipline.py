from backend.src.Factory.ElementFactory import ElementFactory
from backend.src.Scheme.Scheme import Scheme
from backend.src.Core.Value import ValueStatus

def run():
    ef = ElementFactory(
        'backend/configs/value_classes.json',
        'backend/configs/ports.json',
        'backend/configs/elements'
    )
    sch = Scheme("ML pipeline")

    # создаём элементы
    ds = ef.create_element("Dataset")
    nn = ef.create_element("NeuralModel")
    lf = ef.create_element("TF MSE Loss Function")
    opt = ef.create_element("TF Adam Optimizer")

    # регистрируем в схеме и получаем их id
    ds_id = sch.add_element(ds)
    nn_id = sch.add_element(nn)
    lf_id = sch.add_element(lf)
    opt_id = sch.add_element(opt)

    # найдём id портов по именам (для id-first сценария)
    ds_train_port_id = sch.resolve_port_id_by_name(ds_id, "Train")
    ds_val_port_id   = sch.resolve_port_id_by_name(ds_id, "Val")
    nn_train_port_id = sch.resolve_port_id_by_name(nn_id, "Train")
    nn_val_port_id   = sch.resolve_port_id_by_name(nn_id, "Val")
    lf_out_port_id   = sch.resolve_port_id_by_name(lf_id, "LossFunction")
    nn_loss_in_id    = sch.resolve_port_id_by_name(nn_id, "LossFunction")
    opt_out_port_id  = sch.resolve_port_id_by_name(opt_id, "Optimizer")
    nn_opt_in_id     = sch.resolve_port_id_by_name(nn_id, "Optimizer")

    # внешние связи (по id)
    sch.connect_ids(ds_id, ds_train_port_id, nn_id, nn_train_port_id)
    sch.connect_ids(ds_id, ds_val_port_id,   nn_id, nn_val_port_id)
    sch.connect_ids(lf_id, lf_out_port_id,   nn_id, nn_loss_in_id)
    sch.connect_ids(opt_id, opt_out_port_id, nn_id, nn_opt_in_id)

    # вход и параметры — по id
    ds_raw_port_id = sch.resolve_port_id_by_name(ds_id, "RawData")
    sch.set_port_value_by_port_id(ds_raw_port_id, "data", "test.xlsx", ValueStatus.CALCULATED)

    sch.set_param_by_element_id(ds_id, "Seed", 42, ValueStatus.FIXED)
    sch.set_param_by_element_id(ds_id, "SplitRatio", 0.2, ValueStatus.FIXED)
    sch.set_param_by_element_id(ds_id, "XFields", [0, 1], ValueStatus.FIXED)
    sch.set_param_by_element_id(ds_id, "YFields", [2], ValueStatus.FIXED)

    sch.set_param_by_element_id(opt_id, "LearningRate", 1e-3, ValueStatus.FIXED)

    # В конфиге параметр у модели назван "Arhitecture" (как у вас). Используем точное имя.
    sch.set_param_by_element_id(nn_id, "Arhitecture", "den_den_den", ValueStatus.FIXED)
    sch.set_param_by_element_id(nn_id, "ModelOptions", "{0: {'units': 10}, 1: {'units': 20}, 2:{'units': 1}}",
                                ValueStatus.FIXED)

    print(sch.describe())
    sch.run_calculations()
    sch.run_calculations()
    # Проверка результатов
    model_port = sch.get_port_by_id(sch.resolve_port_id_by_name(nn_id, "Model"))
    model_val = model_port.get_value("NeuralModel")
    print("Model:", model_val.status.name, type(model_val.value).__name__)

if __name__ == "__main__":
    run()