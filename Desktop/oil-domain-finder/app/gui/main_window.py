"""Main application window."""

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gui.styles import APP_STYLESHEET
from sources.base import SearchResult
from sources.engine import SearchEngine


class SearchWorker(QObject):
    """Run the source engine outside the GUI thread."""

    progress = Signal(str, int)
    finished = Signal(list)
    failed = Signal(str)

    @Slot()
    def run(self) -> None:
        try:
            companies = SearchEngine().search(progress_callback=self.progress.emit)
        except Exception as error:
            self.failed.emit(str(error) or "We couldn't complete the search. Please try again.")
        else:
            self.finished.emit(companies)


class MainWindow(QMainWindow):
    """The MVP shell for future domain search workflows."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Oil Domain Finder")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(APP_STYLESHEET)
        self._search_thread: QThread | None = None
        self._search_worker: SearchWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        page_layout = QVBoxLayout(central_widget)
        page_layout.setContentsMargins(36, 30, 36, 34)
        page_layout.setSpacing(22)

        title = QLabel("Oil Domain Finder")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Find structured oil and gas company websites — no API key required.")
        subtitle.setObjectName("subtitleLabel")
        page_layout.addWidget(title)
        page_layout.addWidget(subtitle)

        controls_card = QFrame()
        controls_card.setObjectName("contentCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(24, 20, 24, 20)
        controls_layout.setSpacing(16)

        controls_row = QHBoxLayout()
        self.start_button = QPushButton("Start Search")
        self.start_button.setObjectName("startButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setMinimumHeight(48)
        self.start_button.clicked.connect(self._start_search)
        controls_row.addWidget(self.start_button)
        controls_row.addStretch()
        controls_layout.addLayout(controls_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        controls_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        controls_layout.addWidget(self.status_label)
        page_layout.addWidget(controls_card)

        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(
            ["Company", "Website", "Location", "Source"]
        )
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        page_layout.addWidget(self.results_table, stretch=1)

    def _start_search(self) -> None:
        """Start a live search without blocking the Qt event loop."""
        self.start_button.setEnabled(False)
        self.status_label.setText("Searching...")
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self._search_thread = QThread(self)
        self._search_worker = SearchWorker()
        self._search_worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(self._search_worker.run)
        self._search_worker.progress.connect(self._update_search_progress)
        self._search_worker.finished.connect(self._search_finished)
        self._search_worker.failed.connect(self._search_failed)
        self._search_worker.finished.connect(self._search_thread.quit)
        self._search_worker.failed.connect(self._search_thread.quit)
        self._search_thread.finished.connect(self._cleanup_search_thread)
        self._search_thread.start()

    @Slot(str, int)
    def _update_search_progress(self, message: str, progress: int) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(progress)

    @Slot(list)
    def _search_finished(self, companies: list[SearchResult]) -> None:
        for company in companies:
            self._add_result(company)
        self.status_label.setText("Search Complete")
        self.progress_bar.setValue(100)
        self.start_button.setEnabled(True)

    @Slot(str)
    def _search_failed(self, message: str) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(0)
        self.start_button.setEnabled(True)

    @Slot()
    def _cleanup_search_thread(self) -> None:
        if self._search_worker:
            self._search_worker.deleteLater()
        if self._search_thread:
            self._search_thread.deleteLater()
        self._search_worker = None
        self._search_thread = None

    def _add_result(self, company: SearchResult) -> None:
        """Append a source-neutral result row to the table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        for column, value in enumerate(company.table_values()):
            self.results_table.setItem(row, column, QTableWidgetItem(value))
