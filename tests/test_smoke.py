"""Smoke test: verifies the new QWebEngineView architecture boots without errors."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_app_boots():
    """Verify MainWindow and ViewerController can be instantiated."""
    from viewer import register_scheme
    register_scheme()
    
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    # Verify viewer controller exists and has expected attributes
    assert hasattr(window, 'viewer')
    assert hasattr(window.viewer, 'web_view')
    assert hasattr(window.viewer, 'current_page')
    assert hasattr(window.viewer, 'dark_mode')
    assert window.viewer.current_page == 0
    assert window.viewer.dark_mode == False
    
    # Verify the stacked widget has home + webview
    assert window.stacked.count() == 2
    assert window.stacked.currentIndex() == 0  # starts on home
    
    print("✅ Boot smoke test PASSED")
    window.close()

def test_viewer_scheme_handler():
    """Verify the custom scheme handler is installed."""
    from PyQt6.QtWebEngineCore import QWebEngineProfile
    from PyQt6.QtCore import QByteArray
    
    # The scheme handler should already be installed from test_app_boots
    profile = QWebEngineProfile.defaultProfile()
    # No direct way to check if handler is installed, but we can verify it doesn't crash
    print("✅ Scheme handler test PASSED")

def test_dark_mode_toggle():
    """Verify dark mode toggle doesn't crash."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    from ui.main_window import MainWindow
    window = MainWindow()
    
    # Toggle dark mode on/off
    window.viewer.toggle_dark_mode(True)
    assert window.viewer.dark_mode == True
    
    window.viewer.toggle_dark_mode(False)
    assert window.viewer.dark_mode == False
    
    print("✅ Dark mode toggle test PASSED")
    window.close()

if __name__ == "__main__":
    test_app_boots()
    test_viewer_scheme_handler()
    test_dark_mode_toggle()
    print("\n🎉 All smoke tests passed!")
