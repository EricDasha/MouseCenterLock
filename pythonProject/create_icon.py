#!/usr/bin/env python3
"""
Helper script to generate a multi-size .ico file from an image (PNG/JPG).
Usage: python create_icon.py <input_image> <output.ico>
"""

import sys
from PIL import Image

def create_icon(input_path, output_path):
    """Create a multi-size .ico file from an input image."""
    try:
        img = Image.open(input_path)
        
        # Standard icon sizes for Windows
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create list of resized images
        images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)
        
        # Save as ICO
        images[0].save(
            output_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        
        print(f"Successfully created {output_path} with sizes: {[f'{w}x{h}' for w, h in sizes]}")
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_icon.py <input_image> <output.ico>", file=sys.stderr)
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not create_icon(input_path, output_path):
        sys.exit(1)

