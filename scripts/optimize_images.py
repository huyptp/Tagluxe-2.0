import os, sys
from PIL import Image, ImageOps

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOADS = os.path.join(BASE_DIR, 'static', 'uploads')
MAX_SIZE = 1200
QUALITY = 82

def optimize(filepath):
    try:
        with Image.open(filepath) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            w, h = img.size
            if max(w, h) > MAX_SIZE:
                ratio = MAX_SIZE / max(w, h)
                img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
            old_kb = os.path.getsize(filepath) // 1024
            img.save(filepath, 'JPEG', quality=QUALITY, optimize=True)
            new_kb = os.path.getsize(filepath) // 1024
            sys.stdout.buffer.write(f"OK {os.path.basename(filepath)}: {old_kb}KB -> {new_kb}KB\n".encode('utf-8'))
    except Exception as e:
        sys.stdout.buffer.write(f"ERR {os.path.basename(filepath)}: {e}\n".encode('utf-8'))

files = [f for f in os.listdir(UPLOADS) if f.lower().endswith('.jpg')]
sys.stdout.buffer.write(f"Optimizing {len(files)} images...\n".encode('utf-8'))
for f in sorted(files):
    optimize(os.path.join(UPLOADS, f))
sys.stdout.buffer.write(b"Done!\n")
