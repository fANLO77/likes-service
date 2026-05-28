from pathlib import Path
from coursekit.koan import need
from coursekit.variant import load_variant

ROOT = Path(__file__).resolve().parents[3]
ARCH = ROOT / 'weeks' / 'week-17' / 'ARCHITECTURE.md'


def test_capstone_arch():
    need(ARCH.exists(), f"Создайте ARCHITECTURE.md: {ARCH}")
    v = load_variant("17")
    text = ARCH.read_text()
    need(v['project_code'] in text, "В архитектуре укажите project_code из варианта.")
