import cv2
import numpy as np
import pytesseract
from PIL import Image
from dataclasses import dataclass
from typing import List, Tuple, Dict
import re
import os
import platform

# Configure Tesseract path for Windows
if platform.system() == 'Windows':
    # Try to find Tesseract
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files\Tesseract-OCR',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe',
        r'C:\tesseract\tesseract.exe',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Found Tesseract at: {path}")
            break
    else:
        print("⚠️ Tesseract not found. OCR will not work!")
        print("Download from: https://github.com/UB-Mannheim/tesseract/wiki")

@dataclass
class TextBlock:
    """Represents a piece of text found in the image"""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    
    def __repr__(self):
        return f"TextBlock('{self.text[:20]}...', x={self.x}, y={self.y}, conf={self.confidence:.2f})"

class OCRExtractor:
    """Extracts text from images using multiple OCR strategies"""
    
    def __init__(self):
        # Configure Tesseract path for Windows (adjust if needed)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # OCR configuration options
        self.tesseract_config = '--oem 3 --psm 6'
        # OEM 3 = Default OCR Engine Mode
        # PSM 6 = Uniform block of text
        
        self.min_confidence = 30  # Minimum confidence to keep text
        
    def extract_text_with_positions(self, image):
        """
        Extract text and its position from image
        Teaching: OCR gives us not just text, but WHERE it is
        """
        print("\n🔤 Extracting text with positions...")
        
        # Tesseract expects PIL Image or numpy array
        if isinstance(image, np.ndarray):
            # Convert to PIL if needed
            if len(image.shape) == 3:  # Color image
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:  # Grayscale
                pil_image = Image.fromarray(image)
        else:
            pil_image = image
        
        # Get detailed OCR data (not just text)
        ocr_data = pytesseract.image_to_data(
            pil_image, 
            output_type=pytesseract.Output.DICT,
            config=self.tesseract_config
        )
        
        # Process OCR results
        text_blocks = []
        n_boxes = len(ocr_data['level'])
        
        for i in range(n_boxes):
            # Extract data for each detected element
            confidence = float(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            
            # Skip empty or low-confidence text
            if confidence < self.min_confidence or not text:
                continue
            
            # Get position
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            width = ocr_data['width'][i]
            height = ocr_data['height'][i]
            
            # Create text block
            block = TextBlock(
                text=text,
                x=x, y=y,
                width=width, height=height,
                confidence=confidence
            )
            text_blocks.append(block)
        
        print(f"  Found {len(text_blocks)} text blocks")
        return text_blocks
    
    def group_text_into_lines(self, text_blocks):
        """
        Group text blocks into lines
        Teaching: Words on the same line should be grouped together
        """
        print("\n📏 Grouping text into lines...")
        
        if not text_blocks:
            return []
        
        # Sort by Y position (top to bottom)
        sorted_blocks = sorted(text_blocks, key=lambda b: b.y)
        
        lines = []
        current_line = [sorted_blocks[0]]
        current_y = sorted_blocks[0].y
        
        # Group blocks that are on similar Y positions
        for block in sorted_blocks[1:]:
            # If Y position is close (within 10 pixels), same line
            if abs(block.y - current_y) < 10:
                current_line.append(block)
            else:
                # Start new line
                # Sort current line by X position (left to right)
                current_line.sort(key=lambda b: b.x)
                lines.append(current_line)
                
                current_line = [block]
                current_y = block.y
        
        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda b: b.x)
            lines.append(current_line)
        
        print(f"  Grouped into {len(lines)} lines")
        return lines
    
    def identify_labels_and_values(self, text_blocks, form_elements):
        """
        Smart identification of what's a label vs. what's a value
        Teaching: Labels usually end with ':' or are near fields
        """
        print("\n🏷️ Identifying labels and values...")
        
        labels = []
        values = []
        
        for block in text_blocks:
            text = block.text
            
            # Common patterns for labels
            is_label = False
            
            # Pattern 1: Ends with colon
            if text.endswith(':'):
                is_label = True
            
            # Pattern 2: Common label keywords
            label_keywords = [
                'NAME', 'DATE', 'ADDRESS', 'CITY', 'STATE', 'ZIP',
                'LICENSE', 'PLATE', 'VIOLATION', 'OFFICER', 'BADGE',
                'COURT', 'TICKET', 'CASE', 'SPEED', 'LOCATION'
            ]
            
            if any(keyword in text.upper() for keyword in label_keywords):
                is_label = True
            
            # Pattern 3: Near a form field
            for element in form_elements:
                if element.element_type in ['field', 'text_field']:
                    # Is this text just above or to the left of a field?
                    if (abs(block.y - element.y) < 30 and 
                        block.x < element.x + element.width):
                        is_label = True
                        break
            
            if is_label:
                labels.append(block)
            else:
                values.append(block)
        
        print(f"  Found {len(labels)} labels and {len(values)} values")
        return labels, values
    
    def extract_ticket_information(self, image, form_structure):
        """
        Main method: Extract all information from ticket
        Returns structured data
        """
        print("\n" + "="*60)
        print("🎫 EXTRACTING TICKET INFORMATION")
        print("="*60)
        
        # Step 1: Extract all text with positions
        text_blocks = self.extract_text_with_positions(image)
        
        # Step 2: Group into lines
        text_lines = self.group_text_into_lines(text_blocks)
        
        # Step 3: Identify labels vs values
        all_elements = form_structure.get('all_elements', [])
        labels, values = self.identify_labels_and_values(text_blocks, all_elements)
        
        # Step 4: Extract specific ticket information
        ticket_info = self.parse_ticket_data(text_blocks)
        
        # Step 5: Create visualization
        self.visualize_ocr_results(image, text_blocks, labels)
        
        return {
            'text_blocks': text_blocks,
            'text_lines': text_lines,
            'labels': labels,
            'values': values,
            'ticket_info': ticket_info
        }
    
    def parse_ticket_data(self, text_blocks):
        """
        Extract specific ticket information using patterns
        Teaching: Real-world text extraction uses patterns and heuristics
        """
        print("\n🔍 Parsing ticket data...")
        
        # Combine all text for pattern matching
        all_text = ' '.join([block.text for block in text_blocks])
        
        ticket_info = {}
        
        # Pattern matching for common ticket fields
        patterns = {
            'ticket_number': r'TICKET\s*#?\s*(\d+)',
            'case_number': r'CASE\s*#?\s*(\d+)',
            'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            'time': r'(\d{1,2}:\d{2}\s*[APM]{2})',
            'speed': r'(\d+)\s*MPH',
            'violation_code': r'([A-Z]{2,4}\s*\d+\.\d+)',
            'badge_number': r'BADGE\s*#?\s*(\d+)',
            'court_date': r'COURT.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                ticket_info[field] = match.group(1)
                print(f"  Found {field}: {match.group(1)}")
        
        return ticket_info
    
    def visualize_ocr_results(self, image, text_blocks, labels):
        """
        Visualize what OCR found
        Teaching: Always verify OCR results visually
        """
        # Create color image for visualization
        if len(image.shape) == 2:  # Grayscale
            viz_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            viz_image = image.copy()
        
        # Draw text blocks
        for block in text_blocks:
            # Labels in blue, others in green
            color = (255, 0, 0) if block in labels else (0, 255, 0)
            
            # Draw rectangle
            cv2.rectangle(
                viz_image,
                (block.x, block.y),
                (block.x + block.width, block.y + block.height),
                color, 1
            )
            
            # Add confidence score
            cv2.putText(
                viz_image,
                f"{block.confidence:.0f}%",
                (block.x, block.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.3, color, 1
            )
        
        # Show result
        cv2.imshow("OCR Results", viz_image)
        cv2.waitKey(1)
        
        return viz_image

# Integration module
class TicketProcessor:
    """
    Brings everything together!
    This is where we combine OCR, structure detection, and DOCX creation
    """
    
    def __init__(self):
        self.ocr = OCRExtractor()
        
    def process_ticket(self, image_path, output_path):
        """
        Complete ticket processing pipeline
        """
        print("\n" + "="*70)
        print("🎯 COMPLETE TICKET PROCESSING PIPELINE")
        print("="*70)
        
        # Import our modules
        from image_preprocessor import ImagePreprocessor
        from form_structure_detector import FormStructureDetector
        from docx_creator import DocxCreator
        
        # Step 1: Preprocess image
        print("\n[Step 1/4] Preprocessing image...")
        preprocessor = ImagePreprocessor()
        preprocessor.debug = False
        results = preprocessor.process_ticket_image(image_path)
        
        # Step 2: Detect structure
        print("\n[Step 2/4] Detecting form structure...")
        detector = FormStructureDetector(debug=False)
        structure = detector.analyze_form_structure(results['binary'])
        
        # Step 3: Extract text
        print("\n[Step 3/4] Extracting text with OCR...")
        ocr_results = self.ocr.extract_ticket_information(
            results['enhanced'],  # Use enhanced image for better OCR
            structure
        )
        
        # Step 4: Create DOCX
        print("\n[Step 4/4] Creating DOCX with extracted data...")
        creator = DocxCreator()
        
        # Create the document
        doc = creator.create_form_replica(
            results['original'],
            structure,
            output_path
        )
        
        # Print summary
        print("\n" + "="*70)
        print("✅ PROCESSING COMPLETE!")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"  - Text blocks found: {len(ocr_results['text_blocks'])}")
        print(f"  - Form fields detected: {len([e for e in structure['all_elements'] if 'field' in e.element_type])}")
        print(f"  - Output saved to: {output_path}")
        
        if ocr_results['ticket_info']:
            print(f"\n🎫 Extracted ticket info:")
            for key, value in ocr_results['ticket_info'].items():
                print(f"  - {key}: {value}")
        
        print("\n Press any key to close visualization windows...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return {
            'structure': structure,
            'ocr_results': ocr_results,
            'output_path': output_path
        }

# Test the complete pipeline
if __name__ == "__main__":
    from pathlib import Path
    
    # Test OCR only
    print("🧪 Testing OCR Extraction...")
    
    ticket_path = Path("../../data/sample_images/ticket.jpg")
    output_path = Path("../../data/output/ticket_with_ocr.docx")
    
    if ticket_path.exists():
        # Run complete pipeline
        processor = TicketProcessor()
        results = processor.process_ticket(ticket_path, output_path)
        
        print("\n🎉 Success! Check your output folder!")
        print("\n💡 Next steps:")
        print("  1. Open the DOCX file")
        print("  2. Verify text was extracted correctly")
        print("  3. Check if fields are in the right positions")
        
    else:
        print(f"⚠️ Please add your ticket image to: {ticket_path}")