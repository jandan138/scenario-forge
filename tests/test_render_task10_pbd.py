"""A nominal particle count must not display different volumes from float noise."""
from scripts.render_task10_pbd import format_volume_ml


def test_volume_readout_uses_the_same_quantized_count():
    assert format_volume_ml(15.255000114,.003375) == '15.26'
    assert format_volume_ml(15.254999999,.003375) == '15.26'
