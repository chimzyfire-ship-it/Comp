"""Central styling for the desktop interface."""

APP_STYLESHEET = """
QMainWindow {
    background: #F7F9FC;
}
QWidget {
    color: #162033;
    font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
    font-size: 14px;
}
QFrame#contentCard {
    background: white;
    border: 1px solid #E5EAF1;
    border-radius: 14px;
}
QLabel#titleLabel {
    color: #0E1D35;
    font-size: 28px;
    font-weight: 700;
}
QLabel#subtitleLabel {
    color: #64748B;
    font-size: 14px;
}
QPushButton#startButton {
    background: #126B5C;
    border: none;
    border-radius: 9px;
    color: white;
    font-size: 16px;
    font-weight: 600;
    padding: 13px 28px;
}
QPushButton#startButton:hover {
    background: #0D584B;
}
QPushButton#startButton:pressed {
    background: #0A463D;
}
QComboBox#categorySelector {
    background: white;
    border: 1px solid #CBD5E1;
    border-radius: 9px;
    padding: 0 12px;
    font-size: 15px;
}
QLabel#controlLabel {
    color: #526174;
    font-weight: 600;
}
QProgressBar {
    background: #E9EEF4;
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk {
    background: #1A9A83;
    border-radius: 5px;
}
QLabel#statusLabel {
    color: #64748B;
}
QTableWidget {
    background: white;
    alternate-background-color: #F8FAFC;
    border: 1px solid #E5EAF1;
    border-radius: 10px;
    gridline-color: #EEF2F6;
    selection-background-color: #D9F1EC;
    selection-color: #162033;
}
QHeaderView::section {
    background: #F8FAFC;
    border: none;
    border-bottom: 1px solid #E5EAF1;
    color: #526174;
    font-weight: 600;
    padding: 11px 12px;
}
"""
