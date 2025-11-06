import sys
import os
from PIL import Image


def create_ico_from_image(src_path, dst_path, sizes=None):
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]
    os.makedirs(os.path.dirname(dst_path) or '.', exist_ok=True)
    img = Image.open(src_path).convert('RGBA')
    img.save(dst_path, format='ICO', sizes=[(s, s) for s in sizes])
    print('OK ->', dst_path)


def main():
    if len(sys.argv) < 2:
        print('Usage: python create_icon.py <input_image> [output_ico]')
        print('Example: python create_icon.py D:/item/unnamed.jpg pythonProject/assets/app.ico')
        return 1
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.ico'
    create_ico_from_image(src, dst)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


