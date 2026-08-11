import sys
import os
from urllib.parse import urlparse, parse_qs

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QToolBar, QPushButton, QHBoxLayout,
    QLineEdit, QLabel
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon, QAction

HOMEPAGE = "https://www.google.com"
TWIG_VERSION = "1.3"


class TwigPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class BrowserTab(QWidget):
    def __init__(self, url=HOMEPAGE, parent=None):
        super().__init__(parent)

        self.error_shown = False

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.browser = QWebEngineView(self)
        self.page = TwigPage(self.browser)
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(url))

        self.layout.addWidget(self.browser)

        self.browser.titleChanged.connect(self.update_tab_title)
        self.browser.loadFinished.connect(self.handle_load_result)

    def get_tab_widget(self):
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    def update_tab_title(self, title):
        tabs = self.get_tab_widget()
        if not tabs:
            return

        index = tabs.indexOf(self)

        if title.strip() == "":
            title = "Untitled"
        elif self.browser.url().toString() == HOMEPAGE:
            title = "Home"

        tabs.setTabText(index, title)

    def handle_load_result(self, success):
        tabs = self.get_tab_widget()
        if not tabs:
            return

        index = tabs.indexOf(self)

        if not success and not self.error_shown:
            self.error_shown = True
            tabs.setTabText(index, "Failed")
            self.browser.setHtml(
                """
                <html>
                    <head>
                        <title>TWIG - Error</title>
                        <style>
                            body {
                                background-color: #121212;
                                color: #f0f0f0;
                                font-family: sans-serif;
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                justify-content: center;
                                height: 100vh;
                                margin: 0;
                            }
                            .box {
                                background: #1e1e1e;
                                padding: 24px 32px;
                                border-radius: 12px;
                                box-shadow: 0 0 24px rgba(0,0,0,0.5);
                                text-align: center;
                            }
                            button {
                                margin-top: 16px;
                                padding: 8px 16px;
                                border-radius: 8px;
                                border: none;
                                background: #2e2e2e;
                                color: #f0f0f0;
                                cursor: pointer;
                            }
                            button:hover {
                                background: #3a3a3a;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="box">
                            <h1>Page failed to load</h1>
                            <p>TWIG couldn't load this page.</p>
                            <button onclick="location.reload()">Retry</button>
                        </div>
                    </body>
                </html>
                """,
                QUrl("about:blank"),
            )


class Twig(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TWIG 1.3")
        self.resize(1024, 768)

        self.devtools_windows = []

        profile = QWebEngineProfile.defaultProfile()
        original_ua = profile.httpUserAgent()

        cache_path = os.path.join(os.getenv("APPDATA") or "", "TwigCache")
        profile.setCachePath(cache_path)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        profile.setHttpUserAgent(f"{original_ua} Twig/{TWIG_VERSION}")

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)

        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(4, 4, 4, 4)
        top_layout.setSpacing(4)

        self.back_button = QPushButton("←")
        self.forward_button = QPushButton("→")
        self.reload_button = QPushButton("⟳")
        self.home_button = QPushButton("🏠")

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)

        self.devtools_button = QPushButton("DevTools")
        self.new_tab_button = QPushButton("+")

        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)
        self.reload_button.clicked.connect(self.reload_page)
        self.home_button.clicked.connect(self.go_home)
        self.devtools_button.clicked.connect(self.open_devtools)
        self.new_tab_button.clicked.connect(lambda: self.add_tab(HOMEPAGE))

        top_layout.addWidget(self.back_button)
        top_layout.addWidget(self.forward_button)
        top_layout.addWidget(self.reload_button)
        top_layout.addWidget(self.home_button)
        top_layout.addWidget(QLabel("URL:"))
        top_layout.addWidget(self.url_bar)
        top_layout.addWidget(self.devtools_button)
        top_layout.addWidget(self.new_tab_button)

        central_layout.addWidget(top_bar)
        central_layout.addWidget(self.tabs)

        self.setCentralWidget(central_widget)

        self.add_tab(HOMEPAGE)

    def add_tab(self, url=HOMEPAGE):
        tab = BrowserTab(url, self.tabs)
        index = self.tabs.addTab(tab, "Loading...")
        self.tabs.setCurrentIndex(index)
        self.update_url_bar()

    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()
        else:
            self.close()

    def current_tab_changed(self, index):
        self.update_url_bar()

    def get_current_browser(self):
        widget = self.tabs.currentWidget()
        if isinstance(widget, BrowserTab):
            return widget.browser
        return None

    def update_url_bar(self):
        browser = self.get_current_browser()
        if browser:
            self.url_bar.setText(browser.url().toString())
        else:
            self.url_bar.clear()

    def navigate_to_url(self):
        browser = self.get_current_browser()
        if not browser:
            return
        text = self.url_bar.text().strip()
        if not text:
            return
        if "://" not in text:
            text = "https://" + text
        browser.setUrl(QUrl(text))

    def go_back(self):
        browser = self.get_current_browser()
        if browser and browser.history().canGoBack():
            browser.back()

    def go_forward(self):
        browser = self.get_current_browser()
        if browser and browser.history().canGoForward():
            browser.forward()

    def reload_page(self):
        browser = self.get_current_browser()
        if browser:
            browser.reload()

    def go_home(self):
        browser = self.get_current_browser()
        if browser:
            browser.setUrl(QUrl(HOMEPAGE))

    def open_devtools(self):
        browser = self.get_current_browser()
        if not browser:
            return
        devtools = QWebEngineView()
        dev_page = QWebEnginePage(browser.page().profile(), devtools)
        devtools.setPage(dev_page)
        browser.page().setDevToolsPage(dev_page)
        devtools.setWindowTitle("Twig DevTools")
        devtools.resize(800, 600)
        devtools.show()
        self.devtools_windows.append(devtools)


def main():
    app = QApplication(sys.argv)
    window = Twig()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
