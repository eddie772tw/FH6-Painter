import sys
from PIL import Image

def pad_to_square(img_path):
    pil_img = Image.open(img_path).convert('RGB')
    orig_w, orig_h = pil_img.size
    max_dim = max(orig_w, orig_h)
    
    # Create new square image with background color
    mean_color = pil_img.resize((1, 1)).getpixel((0, 0))
    square_img = Image.new('RGB', (max_dim, max_dim), mean_color)
    
    # Paste original image in the center
    offset_x = (max_dim - orig_w) // 2
    offset_y = (max_dim - orig_h) // 2
    square_img.paste(pil_img, (offset_x, offset_y))
    
    print(f"Original: {orig_w}x{orig_h}, Square: {max_dim}x{max_dim}, Offset: {offset_x}, {offset_y}")

pad_to_square("d:/FH6-Painter/crossover.png")
