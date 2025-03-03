import sys
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.debug("Starting debug.py")

try:
    # First import and initialize PyQt to catch any initialization errors
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    logger.debug("PyQt initialized successfully")
    
    # Now import our application
    import main
    logger.debug("Main module imported successfully")
    
except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")
    print(f"\n\n{'='*50}")
    print(f"ERROR TYPE: {type(e).__name__}")
    print(f"ERROR MESSAGE: {str(e)}")
    print(f"{'='*50}")
    print("\nTRACEBACK:")
    traceback.print_exc()
    print(f"{'='*50}\n")
    
    # Try to get more context for the error
    print("ERROR CONTEXT:")
    tb = traceback.extract_tb(sys.exc_info()[2])
    for i, frame in enumerate(tb):
        filename, line_number, func_name, text = frame
        print(f"{i}. File: {filename}, Line: {line_number}, Function: {func_name}")
        print(f"   Code: {text}")
    
    print(f"{'='*50}\n")
