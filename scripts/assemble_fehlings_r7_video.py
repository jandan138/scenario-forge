"""Assemble r7 demo MP4 from the finalized replay keyframes only; no new physics."""
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7'
SCENE = PACKAGE / 'evidence/initial_scene'
OUT_DIR = Path('/tmp/opencode/fehlings-r7-video')
OUT_MP4 = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912/r7_demo.mp4'

SEGMENTS = [
    ('initial_tube_full.png', '1 架内初始 | in rack', 6),
    ('rack_extracted_tube_full.png', '2 取管 | extract', 6),
    ('rack_reinserted_tube_full.png', '3 放回架中 | reinsert', 4),
    ('shallow_contact_closeup.png', '4 放入水浴 | into bath', 5),
    ('t3_withdrawn_closeup.png', '5 显色 3 s | greening', 4),
    ('t15_withdrawn_closeup.png', '6 显色 15 s | yellowing', 4),
    ('t21_withdrawn_closeup.png', '7 显色 21 s | reddening', 4),
    ('t27_withdrawn_closeup.png', '8 显色 27 s | converging', 4),
    ('t30_closeup.png', '9 30 s 完成 | complete', 4),
    ('t30_withdrawn_closeup.png', '10 完成态 | developed', 3),
    ('observed_closeup.png', '11 取出观察 | observation', 4),
]

frames_dir = OUT_DIR / 'frames'
frames_dir.mkdir(parents=True, exist_ok=True)
title_font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 44)
small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
header = 'Fehling r7 | 18x150 mm glass test tube | 8 mL | 30 s reaction | prescribed-fixture replay'
concat_lines = []
for index, (name, label, seconds) in enumerate(SEGMENTS, 1):
    source = SCENE / name
    if not source.is_file():
        raise FileNotFoundError(source)
    image = Image.open(source).convert('RGB')
    if image.size != (1920, 1080):
        raise ValueError(f'unexpected frame size: {name} {image.size}')
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.rectangle((0, 0, 1920, 118), fill=(18, 25, 32, 225))
    draw.text((32, 14), label, font=title_font, fill='white')
    draw.text((32, 70), header, font=small_font, fill=(200, 210, 220))
    frame_path = frames_dir / f'{index:02d}.png'
    image.save(frame_path)
    concat_lines.append(f"file '{frame_path}'\nduration {seconds}")
concat_lines.append(f"file '{frames_dir}/{len(SEGMENTS):02d}.png'")
concat_file = OUT_DIR / 'concat.txt'
concat_file.write_text('\n'.join(concat_lines) + '\n')

subprocess.run([
    'ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
    '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-movflags', '+faststart', '-an', str(OUT_MP4),
], check=True)

probe = json.loads(subprocess.run([
    'ffprobe', '-v', 'error', '-show_entries',
    'format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,nb_frames',
    '-of', 'json', str(OUT_MP4),
], check=True, capture_output=True, text=True).stdout)
subprocess.run(['ffmpeg', '-v', 'error', '-i', str(OUT_MP4), '-f', 'null', '-'], check=True)
result = {'status': 'pass', 'mp4': str(OUT_MP4), 'segments': len(SEGMENTS), 'probe': probe}
(OUT_DIR / 'video_manifest.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
