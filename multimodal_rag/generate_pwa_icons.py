"""
Simple PWA Icon Generator
Creates placeholder icons for Progressive Web App
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Path configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(SCRIPT_DIR, 'frontend', 'static', 'images')

# Required icon sizes for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def ensure_directory():
    """Ensure images directory exists"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"✅ Images directory: {IMAGES_DIR}")

def create_icon(size):
    """Create a single icon with gradient background"""
    # Create new image with gradient background
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)
    
    # Create gradient from indigo to purple
    for y in range(size):
        r = int(99 + (y / size) * (139 - 99))
        g = int(102 + (y / size) * (92 - 102))
        b = int(241 + (y / size) * (246 - 241))
        draw.rectangle([0, y, size, y + 1], fill=(r, g, b))
    
    # Draw brain/document symbols
    center = size // 2
    radius = size // 3
    
    # Draw brain outline (circle with lobes)
    lobe_radius = size // 8
    draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        outline='white',
        width=max(2, size // 64)
    )
    
    # Draw brain details (smaller circles for lobes)
    for angle_offset in [0, 60, 120, 180, 240, 300]:
        import math
        angle = math.radians(angle_offset)
        lobe_x = center + int((radius * 0.7) * math.cos(angle))
        lobe_y = center + int((radius * 0.7) * math.sin(angle))
        draw.ellipse(
            [lobe_x - lobe_radius//2, lobe_y - lobe_radius//2, 
             lobe_x + lobe_radius//2, lobe_y + lobe_radius//2],
            outline='white',
            width=max(1, size // 128)
        )
    
    # Draw document/database icon in center
    doc_width = size // 6
    doc_height = size // 5
    doc_x = center - doc_width // 2
    doc_y = center - doc_height // 2
    
    # Document rectangle
    draw.rectangle(
        [doc_x, doc_y, doc_x + doc_width, doc_y + doc_height],
        fill='white',
        outline='white',
        width=1
    )
    
    # Document lines
    line_spacing = doc_height // 4
    for i in range(1, 4):
        y = doc_y + i * line_spacing
        draw.line(
            [doc_x + 2, y, doc_x + doc_width - 2, y],
            fill=(99, 102, 241),
            width=max(1, size // 256)
        )
    
    return img

def generate_icons():
    """Generate all required icon sizes"""
    print("\n🎨 Creating PWA icons...")
    
    for size in ICON_SIZES:
        try:
            img = create_icon(size)
            output_path = os.path.join(IMAGES_DIR, f'icon-{size}x{size}.png')
            img.save(output_path, 'PNG', optimize=True)
            print(f"  ✅ Generated: icon-{size}x{size}.png")
        except Exception as e:
            print(f"  ❌ Error creating icon-{size}x{size}.png: {e}")
    
    print("✅ All icons generated!")

def create_favicon():
    """Create favicon.ico"""
    print("\n🔖 Creating favicon...")
    
    try:
        # Create favicon with multiple sizes
        favicon_path = os.path.join(SCRIPT_DIR, 'frontend', 'static', 'favicon.ico')
        favicon_sizes = [(16, 16), (32, 32), (48, 48)]
        
        favicon_images = []
        for size in favicon_sizes:
            img = create_icon(size[0])
            favicon_images.append(img)
        
        favicon_images[0].save(
            favicon_path,
            format='ICO',
            sizes=[(img.size[0], img.size[1]) for img in favicon_images],
            append_images=favicon_images[1:] if len(favicon_images) > 1 else []
        )
        print(f"  ✅ Created: favicon.ico")
    except Exception as e:
        print(f"  ⚠️  Could not create favicon: {e}")

def create_screenshots():
    """Create placeholder screenshots"""
    print("\n📸 Creating screenshots...")
    
    try:
        # Wide screenshot (desktop)
        wide_img = Image.new('RGB', (1280, 720))
        draw = ImageDraw.Draw(wide_img)
        
        # Gradient background
        for y in range(720):
            r = int(15 + (y / 720) * 20)
            g = int(15 + (y / 720) * 20)
            b = int(35 + (y / 720) * 40)
            draw.rectangle([0, y, 1280, y + 1], fill=(r, g, b))
        
        # Title
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        text = "Multimodal RAG System"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (1280 - text_width) // 2
        y = 300
        draw.text((x, y), text, fill='white', font=font)
        
        wide_path = os.path.join(IMAGES_DIR, 'screenshot-wide.png')
        wide_img.save(wide_path, 'PNG')
        print(f"  ✅ Created: screenshot-wide.png")
        
        # Narrow screenshot (mobile)
        narrow_img = Image.new('RGB', (750, 1334))
        draw = ImageDraw.Draw(narrow_img)
        
        for y in range(1334):
            r = int(15 + (y / 1334) * 20)
            g = int(15 + (y / 1334) * 20)
            b = int(35 + (y / 1334) * 40)
            draw.rectangle([0, y, 750, y + 1], fill=(r, g, b))
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        text1 = "Multimodal"
        text2 = "RAG System"
        bbox1 = draw.textbbox((0, 0), text1, font=font)
        bbox2 = draw.textbbox((0, 0), text2, font=font)
        
        x1 = (750 - (bbox1[2] - bbox1[0])) // 2
        x2 = (750 - (bbox2[2] - bbox2[0])) // 2
        y1 = 600
        y2 = 660
        
        draw.text((x1, y1), text1, fill='white', font=font)
        draw.text((x2, y2), text2, fill='white', font=font)
        
        narrow_path = os.path.join(IMAGES_DIR, 'screenshot-narrow.png')
        narrow_img.save(narrow_path, 'PNG')
        print(f"  ✅ Created: screenshot-narrow.png")
        
    except Exception as e:
        print(f"  ⚠️  Error creating screenshots: {e}")

if __name__ == '__main__':
    print("🚀 PWA Icon Generator")
    print("=" * 60)
    
    ensure_directory()
    generate_icons()
    create_favicon()
    create_screenshots()
    
    print("\n" + "=" * 60)
    print("✨ Icon generation complete!")
    print(f"\n📁 Icons saved to: {IMAGES_DIR}")
    print("\n✅ Your PWA is ready to be installed!")
