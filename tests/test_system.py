# test_system.py
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"  # Hide pygame message

# Test imports
try:
    from src.core.integrated_ticket_processor import IntegratedTicketFiller
    print("✅ Imports working!")
except Exception as e:
    print(f"❌ Import error: {e}")

# Test Tesseract
try:
    import pytesseract
    print(f"✅ Tesseract version: {pytesseract.get_tesseract_version()}")
except Exception as e:
    print(f"❌ Tesseract error: {e}")