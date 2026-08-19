"""Debug script to check each page import."""

import sys
import os
import traceback
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Qt environment
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
os.environ.setdefault("QT_SCALE_FACTOR", "1")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

try:
    from PyQt5.QtWidgets import QApplication
    logger.info("✓ QApplication import")
    
    from app.core.theme import APP_NAME, APP_STYLE, ORG_NAME, default_app_font
    logger.info("✓ Theme imports")
    
    from db.db_initializer import initialize_database
    logger.info("✓ DB initializer")
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setFont(default_app_font())
    app.setStyleSheet(APP_STYLE)
    logger.info("✓ QApplication configured")
    
    # Test each page import
    pages_to_test = [
        ("DashboardPage", "app.ui.pages.dashboard_page"),
        ("InventoryPage", "app.ui.pages.inventory_page"),
        ("ProductionPage", "app.ui.pages.production_page"),
        ("ReceptionPage", "app.ui.pages.reception_page"),
        ("ShipmentsPage", "app.ui.pages.shipments_page"),
        ("TraceabilityPage", "app.ui.pages.traceability_page"),
        ("SettingsPage", "app.ui.pages.settings_page"),
    ]
    
    for page_name, module_path in pages_to_test:
        try:
            logger.info(f"Importing {page_name}...")
            module = __import__(module_path, fromlist=[page_name])
            cls = getattr(module, page_name)
            logger.info(f"✓ {page_name} imported successfully")
            
            logger.info(f"Instantiating {page_name}...")
            instance = cls()
            logger.info(f"✓ {page_name} instantiated successfully")
        except Exception as e:
            logger.error(f"✗ {page_name} failed: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    logger.info("✓ All pages imported and instantiated successfully")
    logger.info("Creating AppShellWindow...")
    from app.ui.shell_window import AppShellWindow
    
    shell = AppShellWindow(username="Admin")
    logger.info("✓ AppShellWindow created successfully")
    
    logger.info("Done. App is ready to run.")
    
except Exception as e:
    logger.error(f"Fatal error: {e}")
    traceback.print_exc()
    sys.exit(1)
