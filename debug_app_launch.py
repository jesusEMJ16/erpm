"""Debug script to capture app startup errors."""

import sys
import traceback
import logging

# Configure logging to capture everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_app.log')
    ]
)

logger = logging.getLogger(__name__)

try:
    logger.info("Starting app initialization...")
    
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    import os
    
    logger.info("Qt imports successful")
    
    # Configure Qt environment
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    
    logger.info("Qt environment configured")
    
    # Import app modules
    from app.core.theme import APP_NAME, APP_STYLE, ORG_NAME, default_app_font
    logger.info("Theme imports successful")
    
    from app.ui.icon_utils import load_app_icon
    logger.info("Icon utils imported")
    
    from app.ui.login_window import LoginWindow
    logger.info("LoginWindow imported")
    
    from db.db_initializer import initialize_database
    logger.info("DB initializer imported")
    
    # Initialize database
    try:
        logger.info("Initializing database...")
        initialize_database()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.warning(f"Database initialization warning: {exc}")
        traceback.print_exc()
    
    # Create and configure QApplication
    logger.info("Creating QApplication...")
    app = QApplication(sys.argv)
    logger.info("QApplication created")
    
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setFont(default_app_font())
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(APP_STYLE)
    
    logger.info("QApplication configured")
    
    # Create and show login window
    logger.info("Creating LoginWindow...")
    window = LoginWindow()
    logger.info("LoginWindow created")
    
    logger.info("Showing LoginWindow...")
    window.show()
    logger.info("LoginWindow shown")
    
    # Setup signal handling
    import signal
    from PyQt5.QtCore import QTimer
    
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal_pump = QTimer()
    signal_pump.setInterval(250)
    signal_pump.timeout.connect(lambda: None)
    signal_pump.start()
    app._signal_pump = signal_pump
    
    logger.info("Signal handling configured")
    logger.info("Starting event loop...")
    
    exit_code = app.exec_()
    logger.info(f"App exited with code: {exit_code}")
    sys.exit(exit_code)
    
except Exception as e:
    logger.error(f"Fatal error: {e}")
    traceback.print_exc()
    sys.exit(1)
