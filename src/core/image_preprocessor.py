# src/core/image_preprocessor.py
"""
Lesson 3: Preparing Images for OCR
Goal: Make the ticket image cleaner and easier for the computer to read
"""

import cv2
import numpy as np
from pathlib import Path

class ImagePreprocessor:
    """Prepares images for OCR and analysis"""
    
    def __init__(self):
        self.debug = True
    
    def load_image(self, image_path):
        """
        Step 1: Load the image
        Teaching point: We load as grayscale for easier processing
        """
        print(f"\n📷 Loading image: {image_path}")
        
        
        color_image = cv2.imread(str(image_path))
        
        # Load as grayscale for processing
        gray_image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        
        print(f"✅ Image shape: {gray_image.shape}")
        print(f"   Height: {gray_image.shape[0]} pixels")
        print(f"   Width: {gray_image.shape[1]} pixels")
        
        if self.debug:
            self._show_image("Original", color_image, wait=False)
            self._show_image("Grayscale", gray_image, wait=False)
        
        return color_image, gray_image
    
    def enhance_image(self, gray_image):
        """
        Step 2: Make the image clearer
        Teaching point: OCR works better on high-contrast, clean images
        """
        print("\n🔧 Enhancing image for better OCR...")
        
        # 1. Remove noise (small dots and imperfections)
        print("  1. Removing noise...")
        denoised = cv2.fastNlMeansDenoising(gray_image, h=10)
        
        # 2. Increase contrast
        print("  2. Increasing contrast...")
        # CLAHE = Contrast Limited Adaptive Histogram Equalization
        # (fancy name for "make dark things darker, light things lighter")
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(denoised)
        
        # 3. Sharpen the image
        print("  3. Sharpening edges...")
        # Create a sharpening kernel
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        sharpened = cv2.filter2D(contrast, -1, kernel)
        
        if self.debug:
            self._show_image("After Noise Removal", denoised, wait=False)
            self._show_image("After Contrast", contrast, wait=False)
            self._show_image("After Sharpening", sharpened, wait=False)
        
        return sharpened
    
    def binarize_image(self, gray_image):
        """
        Step 3: Convert to pure black and white
        Teaching point: This makes text stand out clearly
        """
        print("\n⚪⚫ Converting to black and white...")
        
        # Method 1: Simple threshold
        # Everything above 127 becomes white (255), below becomes black (0)
        _, simple_binary = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
        
        # Method 2: Adaptive threshold
        # Smarter! Adjusts threshold based on local area
        adaptive_binary = cv2.adaptiveThreshold(
            gray_image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,  
            2    
        )
        
        # Method 3: Otsu's method
        # Automatically finds the best threshold
        _, otsu_binary = cv2.threshold(
            gray_image, 0, 255, 
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        print(f"  Simple threshold: Fixed at 127")
        print(f"  Otsu's threshold: Automatically chose {_}")
        
        if self.debug:
            self._show_image("Simple Binary", simple_binary, wait=False)
            self._show_image("Adaptive Binary", adaptive_binary, wait=False)
            self._show_image("Otsu Binary", otsu_binary, wait=False)
        
        return otsu_binary  
    
    def detect_text_regions(self, binary_image):
        """
        Step 4: Find where text is located
        Teaching point: We need to find text areas vs lines/boxes
        """
        print("\n🔍 Finding text regions...")
        
        
        contours, hierarchy = cv2.findContours(
            binary_image, 
            cv2.RETR_EXTERNAL,  # Only outer contours
            cv2.CHAIN_APPROX_SIMPLE  # Compress contours
        )
        
        print(f"  Found {len(contours)} potential regions")
        
        
        result_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
        
        text_regions = []
        for contour in contours:
            
            x, y, w, h = cv2.boundingRect(contour)
            
            
            if w > 20 and h > 10:
                text_regions.append((x, y, w, h))
                
                cv2.rectangle(result_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        print(f"  Kept {len(text_regions)} text regions")
        
        if self.debug:
            self._show_image("Detected Regions", result_image)
        
        return text_regions
    
    def _show_image(self, title, image, wait=True):
        """Helper to display images"""
        cv2.imshow(title, image)
        if wait:
            print(f"\n👀 Showing: {title}")
            print("   Press any key to continue...")
            cv2.waitKey(0)
        else:
            cv2.waitKey(1)  
    
    def process_ticket_image(self, image_path):
        """
        Full pipeline: Load → Enhance → Binarize → Detect regions
        """
        print("=" * 60)
        print("🎫 PROCESSING TICKET IMAGE")
        print("=" * 60)
        
        # Load
        color, gray = self.load_image(image_path)
        
        # Enhance
        enhanced = self.enhance_image(gray)
        
        # Binarize
        binary = self.binarize_image(enhanced)
        
        # Detect text regions
        regions = self.detect_text_regions(binary)
        
        print("\n✅ Processing complete!")
        print("Press any key to close all windows...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return {
            'original': color,
            'grayscale': gray,
            'enhanced': enhanced,
            'binary': binary,
            'text_regions': regions
        }

# Test the preprocessor
if __name__ == "__main__":
    # Create test script
    preprocessor = ImagePreprocessor()
    
    # Put your ticket image in data/sample_images/
    ticket_path = Path("data/sample_images/ticket.jpg")
    
    if not ticket_path.exists():
        print("⚠️  Please put your ticket image at:")
        print(f"   {ticket_path.absolute()}")
    else:
        results = preprocessor.process_ticket_image(ticket_path)
        print(f"\n📊 Found {len(results['text_regions'])} text regions")