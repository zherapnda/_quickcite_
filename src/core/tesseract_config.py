# src/core/tesseract_config.py
"""
Configure Tesseract path for Windows
"""
import platform
import os
import pytesseract

def configure_tesseract():
    """Set up Tesseract path based on OS"""
    if platform.system() == 'Windows':
        # Common installation paths for Tesseract on Windows
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR',
        ]
        
        # Find which path exists
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✅ Found Tesseract at: {path}")
                return True
        
        print("❌ Tesseract not found! Please install from:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    return True  # Assume it's in PATH on other systems

# Auto-configure when imported
configure_tesseract()