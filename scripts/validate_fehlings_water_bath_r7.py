"""Isaac 4.5 r7: glass body, rack extraction/reinsertion and eight-mL reaction."""
from scripts.validate_fehlings_water_bath_r3 import main


if __name__=='__main__':
    raise SystemExit(main(five_layers=True,glass_tube=True))
