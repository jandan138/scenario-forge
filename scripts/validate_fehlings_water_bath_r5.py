"""Run the r3 contact/observation fixtures with r5 fixed-geometry/material assertions."""
from scripts.validate_fehlings_water_bath_r3 import main


if __name__ == '__main__':
    raise SystemExit(main(fixed_materials=True))
