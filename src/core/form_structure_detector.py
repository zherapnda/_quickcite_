# src/core/form_structure_detector.py
"""
Lesson 4: Understanding Form Structure
Goal: Detect lines, boxes, and identify where to place fillable fields
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class FormElement:
    """
    A dataclass is a Python 3.7+ feature that automatically creates
    __init__, __repr__, and other methods for us!
    It's perfect for storing data.
    """
    element_type: str  # 'hline', 'vline', 'box', 'checkbox', 'field'
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    
    def __repr__(self):
        """How this object appears when printed"""
        return f"{self.element_type}(x={self.x}, y={self.y}, w={self.width}, h={self.height})"

class FormStructureDetector:
    """Detects the structure of forms - lines, boxes, fields"""
    
    def __init__(self, debug=True):
        self.debug = debug
        self.min_line_length = 50  # Minimum pixels for a line
        self.checkbox_size_range = (15, 40)  # Min and max size for checkboxes
        
    def detect_lines(self, binary_image):
        """
        Step 1: Find all horizontal and vertical lines
        Teaching: Lines help us understand form layout
        """
        print("\n📏 Detecting lines in the form...")
        
        # Create copies for visualization
        horizontal_viz = np.copy(binary_image)
        vertical_viz = np.copy(binary_image)
        
        # Method 1: Morphological operations (like erosion and dilation)
        # These help us find lines by their shape
        
        # Kernel for detecting horizontal lines
        # This is like a filter that's 1 pixel tall and 40 pixels wide
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        
        # Find horizontal lines
        horizontal_lines = cv2.morphologyEx(
            binary_image, 
            cv2.MORPH_OPEN,  # Opening = erosion followed by dilation
            horizontal_kernel,
            iterations=1
        )
        
        # Kernel for vertical lines (1 pixel wide, 40 pixels tall)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # Find vertical lines
        vertical_lines = cv2.morphologyEx(
            binary_image,
            cv2.MORPH_OPEN,
            vertical_kernel,
            iterations=1
        )
        
        # Method 2: Hough Line Transform (finds lines mathematically)
        # This is more accurate but also more complex
        
        # Detect edges first (lines are edges!)
        edges = cv2.Canny(binary_image, 50, 150)
        
        # Find lines using HoughLinesP (P = Probabilistic)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,              # Distance resolution in pixels
            theta=np.pi/180,    # Angle resolution in radians
            threshold=100,      # Minimum votes to be a line
            minLineLength=self.min_line_length,
            maxLineGap=10       # Max gap between line segments
        )
        
        # Process found lines
        horizontal_elements = []
        vertical_elements = []
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # Calculate line properties
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)
                
                # Classify as horizontal or vertical
                if angle < 10 or angle > 170:  # Horizontal
                    element = FormElement(
                        element_type='hline',
                        x=min(x1, x2),
                        y=min(y1, y2),
                        width=int(abs(x2-x1)),
                        height=2  # Thin line
                    )
                    horizontal_elements.append(element)
                    
                    # Draw for visualization
                    if self.debug:
                        cv2.line(horizontal_viz, (x1,y1), (x2,y2), 128, 2)
                        
                elif 80 < angle < 100:  # Vertical
                    element = FormElement(
                        element_type='vline',
                        x=min(x1, x2),
                        y=min(y1, y2),
                        width=2,  # Thin line
                        height=int(abs(y2-y1))
                    )
                    vertical_elements.append(element)
                    
                    # Draw for visualization
                    if self.debug:
                        cv2.line(vertical_viz, (x1,y1), (x2,y2), 128, 2)
        
        print(f"  Found {len(horizontal_elements)} horizontal lines")
        print(f"  Found {len(vertical_elements)} vertical lines")
        
        if self.debug:
            cv2.imshow("Horizontal Lines", horizontal_viz)
            cv2.imshow("Vertical Lines", vertical_viz)
            cv2.waitKey(1)
        
        return horizontal_elements, vertical_elements
    
    def detect_boxes_and_checkboxes(self, binary_image):
        """
        Step 2: Find rectangles (could be checkboxes or text fields)
        Teaching: Boxes often indicate where to input data
        """
        print("\n📦 Detecting boxes and checkboxes...")
        
        # Find contours (connected components)
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        boxes = []
        checkboxes = []
        
        # Visualization image
        viz_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
        
        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate properties
            area = w * h
            aspect_ratio = w / h if h > 0 else 0
            
            # Is it square-ish? (aspect ratio close to 1)
            is_square = 0.7 < aspect_ratio < 1.3
            
            # Is it the right size for a checkbox?
            min_size, max_size = self.checkbox_size_range
            is_checkbox_size = min_size < w < max_size and min_size < h < max_size
            
            if is_square and is_checkbox_size:
                # Likely a checkbox
                checkbox = FormElement(
                    element_type='checkbox',
                    x=x, y=y, width=w, height=h,
                    confidence=0.8
                )
                checkboxes.append(checkbox)
                
                # Draw in red
                if self.debug:
                    cv2.rectangle(viz_image, (x,y), (x+w,y+h), (0,0,255), 2)
                    cv2.putText(viz_image, "CB", (x,y-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0,0,255), 1)
            
            elif w > 50 and h > 15 and h < 50:
                # Likely a text field box
                box = FormElement(
                    element_type='field',
                    x=x, y=y, width=w, height=h,
                    confidence=0.7
                )
                boxes.append(box)
                
                # Draw in green
                if self.debug:
                    cv2.rectangle(viz_image, (x,y), (x+w,y+h), (0,255,0), 2)
        
        print(f"  Found {len(checkboxes)} checkboxes")
        print(f"  Found {len(boxes)} potential text fields")
        
        if self.debug:
            cv2.imshow("Boxes and Checkboxes", viz_image)
            cv2.waitKey(1)
        
        return boxes, checkboxes
    
    def identify_fillable_fields(self, binary_image, horizontal_lines, vertical_lines):
        """
        Step 3: Find areas where text should be entered
        Teaching: We look for blank spaces near labels
        """
        print("\n✏️ Identifying fillable fields...")
        
        # Strategy: Look for horizontal lines (underscores) that could be fill areas
        # Also look for blank rectangular areas
        
        height, width = binary_image.shape
        fillable_fields = []
        
        # Create visualization
        viz_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
        
        # Look for horizontal lines that might be fill lines
        for line in horizontal_lines:
            # Check if there's text above this line (label)
            region_above = binary_image[
                max(0, line.y-30):line.y,
                line.x:line.x+line.width
            ]
            
            # If there's text above, this might be a fill line
            text_pixels = np.sum(region_above == 0)  # Count black pixels
            if text_pixels > 50:  # Some text exists
                field = FormElement(
                    element_type='text_field',
                    x=line.x,
                    y=line.y-25,  # Place field above line
                    width=line.width,
                    height=25,
                    confidence=0.9
                )
                fillable_fields.append(field)
                
                # Draw in blue
                if self.debug:
                    cv2.rectangle(viz_image, 
                                (field.x, field.y), 
                                (field.x + field.width, field.y + field.height),
                                (255, 0, 0), 2)
        
        print(f"  Found {len(fillable_fields)} fillable fields")
        
        if self.debug:
            cv2.imshow("Fillable Fields", viz_image)
            cv2.waitKey(1)
        
        return fillable_fields
    
    def analyze_form_structure(self, binary_image):
        """
        Main method: Detect complete form structure
        """
        print("\n" + "="*60)
        print("🏗️ ANALYZING FORM STRUCTURE")
        print("="*60)
        
        # Step 1: Detect lines
        h_lines, v_lines = self.detect_lines(binary_image)
        
        # Step 2: Detect boxes and checkboxes
        boxes, checkboxes = self.detect_boxes_and_checkboxes(binary_image)
        
        # Step 3: Identify fillable fields
        fields = self.identify_fillable_fields(binary_image, h_lines, v_lines)
        
        # Combine all elements
        all_elements = h_lines + v_lines + boxes + checkboxes + fields
        
        print(f"\n📊 Structure Summary:")
        print(f"  Total elements: {len(all_elements)}")
        print(f"  - Horizontal lines: {len(h_lines)}")
        print(f"  - Vertical lines: {len(v_lines)}")
        print(f"  - Checkboxes: {len(checkboxes)}")
        print(f"  - Text boxes: {len(boxes)}")
        print(f"  - Fillable fields: {len(fields)}")
        
        if self.debug:
            print("\nPress any key to close windows...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        return {
            'horizontal_lines': h_lines,
            'vertical_lines': v_lines,
            'boxes': boxes,
            'checkboxes': checkboxes,
            'fields': fields,
            'all_elements': all_elements
        }

# Test the detector
if __name__ == "__main__":
    from image_preprocessor import ImagePreprocessor
    from pathlib import Path
    
    # Load and preprocess image
    preprocessor = ImagePreprocessor()
    ticket_path = Path("../../data/sample_images/ticket.jpg")
    
    if ticket_path.exists():
        # Process image
        results = preprocessor.process_ticket_image(ticket_path)
        
        # Detect structure
        detector = FormStructureDetector(debug=True)
        structure = detector.analyze_form_structure(results['binary'])
        
        # Print some detected elements
        print("\n🔍 Sample detected elements:")
        for element in structure['all_elements'][:5]:
            print(f"  {element}")
    else:
        print(f"⚠️ Please add your ticket image to: {ticket_path}")