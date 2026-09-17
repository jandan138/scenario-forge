"""Isaac 4.5 r8: same glass/rack/bath fixtures as r7, clear visual water."""
from scripts.validate_fehlings_water_bath_r3 import main


if __name__ == '__main__':
    raise SystemExit(main(five_layers=True, glass_tube=True))
