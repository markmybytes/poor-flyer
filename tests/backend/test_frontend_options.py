"""Guard the frontend filter options against the backend filter enums.

Drift here is silent the other way: the backend rejects unknown values at
save, but a backend enum value the select lacks is simply unpickable. This
test fails on either mismatch.
"""

import re
from pathlib import Path

from src.utils.filters import CabinClass, MaxStops

OPTIONS_TS = Path(__file__).parents[2] / 'src' / 'frontend' / 'options.ts'


def _option_values(name: str) -> list[str]:
    block = re.search(
        rf'export const {name} = \[(.*?)\] as const',
        OPTIONS_TS.read_text(encoding='utf-8'),
        re.DOTALL,
    )
    assert block, f'{name} not found in {OPTIONS_TS}'
    return re.findall(r"value: '([^']+)'", block.group(1))


def test_cabin_class_options_match_backend_enum():
    assert _option_values('CABIN_CLASS_OPTIONS') == [c.value for c in CabinClass]


def test_max_stops_options_match_backend_enum():
    assert _option_values('MAX_STOPS_OPTIONS') == [s.value for s in MaxStops]
