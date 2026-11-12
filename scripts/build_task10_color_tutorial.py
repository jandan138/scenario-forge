"""Inline the verified task10 images into one offline HTML teaching document."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/task10_color_tutorial_20261010'
TEMPLATE = ROOT / 'docs/task10-liquid-color-tutorial/tutorial.html.in'
IMAGES = ROOT / 'outputs/task10_real_liquid_vr_r1_20261009/preview_replay'


def build(out=OUT, images_root=IMAGES, template=TEMPLATE):
    html = template.read_text(encoding="utf-8")
    images = {}
    for key, name in [('INITIAL', 'frame_00000.png'), ('ENDPOINT', 'frame_00003.png'), ('OVERSHOOT', 'frame_00005.png')]:
        data = (images_root / name).read_bytes()
        html = html.replace('__' + key + '_IMAGE__', 'data:image/png;base64,' + base64.b64encode(data).decode())
        images[name] = hashlib.sha256(data).hexdigest()
    out.mkdir(exist_ok=True, parents=True)
    target = out / 'task10-liquid-color-tutorial.html'
    target.write_text(html, encoding="utf-8")
    (out / 'build.json').write_text(json.dumps({'html': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'image_sha256': images, 'template': str(template),
        'template_sha256': hashlib.sha256(template.read_bytes()).hexdigest(),
        'logic_sha256': {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                         for name in ('task10_pbd_policy.py', 'task10_pbd_runtime.py')}, 'date': '2026-10-10', 'offline': True}, indent=2))
    print(target)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--images',type=Path,default=IMAGES)
    parser.add_argument('--template',type=Path,default=TEMPLATE)
    args=parser.parse_args()
    build(args.out,args.images,args.template)
