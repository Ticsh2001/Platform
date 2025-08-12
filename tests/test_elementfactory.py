from backend.src.Factory.ElementFactory import ElementFactory
from pathlib import Path

def test_element_factory_summary():
    root = Path(__file__).resolve().parents[1]
    ef = ElementFactory('backend/configs/value_classes.json',
                        'backend/configs/ports.json',
                        'backend/configs/elements')
    # Простой санити-чек
    for n in [name.lower() for name in ef.list_elements()]:
        print(n)
    assert "dummy" in [name.lower() for name in ef.list_elements()]

test_element_factory_summary()

