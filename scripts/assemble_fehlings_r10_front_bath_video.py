"""Assemble r10 in-bath MP4 from deep front_bath replay frames; tube stays in the water."""
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10_20260914/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10'
SCENE = PACKAGE / 'evidence/initial_scene'
OUT_DIR = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10_20260914/video'
OUT_MP4 = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10_20260914/r10_front_bath.mp4'

SEGMENTS = [
    ('t3_front_bath.png', '3 s | 蓝色 | blue', 3),
    ('t9_front_bath.png', '9 s | 青绿 | green', 3),
    ('t15_front_bath.png', '15 s | 黄绿 | yellow-green', 3),
    ('t21_front_bath.png', '21 s | 橙 | orange', 3),
    ('t27_front_bath.png', '27 s | 橙红 | orange-red', 3),
    ('t30_front_bath.png', '30 s | 砖红 | brick-red', 5),
]


def main():
    frames_dir = OUT_DIR / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    title_font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 44)
    small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
    header = 'Fehling r10 | 正对隔杯 | deep immerse | 8 mL | prescribed-fixture replay'
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
    subprocess.run(
        [
            'ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-movflags', '+faststart', '-an', str(OUT_MP4),
        ],
        check=True,
    )
    probe = json.loads(
        subprocess.run(
            [
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,nb_frames',
                '-of', 'json', str(OUT_MP4),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(OUT_MP4), '-f', 'null', '-'], check=True)
    result = {
        'status': 'pass',
        'mp4': str(OUT_MP4),
        'sha256': __import__('hashlib').sha256(OUT_MP4.read_bytes()).hexdigest(),
        'segments': SEGMENTS,
        'probe': probe,
    }
    (OUT_DIR / 'video_manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'mp4': result['mp4'], 'sha256': result['sha256']}, indent=2))


if __name__ == '__main__':
    main()
