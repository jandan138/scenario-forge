"""Isaac 4.5 r10: r9 scene, deep upright heating playback."""
from scripts.validate_fehlings_water_bath_r3 import main


if __name__ == '__main__':
    raise SystemExit(main(five_layers=True, glass_tube=True, heating_style='deep'))
