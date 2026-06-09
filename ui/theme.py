from PyQt6.QtGui import QPalette, QColor

THEMES = {
    "dark": {
        # Qt palette
        "window":            "#353535",
        "window_text":       "#dcdcdc",
        "base":              "#232323",
        "alternate_base":    "#353535",
        "text":              "#dcdcdc",
        "button":            "#353535",
        "button_text":       "#dcdcdc",
        "highlight":         "#2a82da",
        "highlighted_text":  "#000000",
        # pyqtgraph chart
        "chart_bg":          "#1a1a2e",
        "chart_axis_pen":    "#3a3a5c",
        "chart_text_pen":    "#888888",
        "chart_grid_alpha":  0.12,
        "price_line":        "#6495ED",
        "price_fill_top":    (100, 149, 237, 120),
        "price_fill_bottom": (100, 149, 237, 0),
        "crosshair_pen":     "#555555",
        "dot_brush":         "#6495ED",
        "dot_pen":           "#ffffff",
        "tooltip_style": (
            "QLabel { background: rgba(20,20,35,210); color: #eeeeee;"
            " border: 1px solid #3a3a5c; border-radius: 6px;"
            " padding: 7px 11px; font-size: 12px; }"
        ),
        "empty_label_style": "color: #666; font-size: 16px;",
    },
    "light": {
        # Qt palette
        "window":            "#f0f0f0",
        "window_text":       "#1e1e1e",
        "base":              "#ffffff",
        "alternate_base":    "#e9e9e9",
        "text":              "#1e1e1e",
        "button":            "#e1e1e1",
        "button_text":       "#1e1e1e",
        "highlight":         "#2a82da",
        "highlighted_text":  "#ffffff",
        # pyqtgraph chart
        "chart_bg":          "#f8f8f8",
        "chart_axis_pen":    "#cccccc",
        "chart_text_pen":    "#555555",
        "chart_grid_alpha":  0.15,
        "price_line":        "#1a5fa8",
        "price_fill_top":    (26, 95, 168, 70),
        "price_fill_bottom": (26, 95, 168, 0),
        "crosshair_pen":     "#aaaaaa",
        "dot_brush":         "#1a5fa8",
        "dot_pen":           "#333333",
        "tooltip_style": (
            "QLabel { background: rgba(255,255,255,230); color: #222222;"
            " border: 1px solid #cccccc; border-radius: 6px;"
            " padding: 7px 11px; font-size: 12px; }"
        ),
        "empty_label_style": "color: #999; font-size: 16px;",
    },
}


def get_tokens(theme_name: str) -> dict:
    return THEMES.get(theme_name, THEMES["dark"])


def apply_palette(app, theme_name: str):
    app.setStyle("Fusion")
    t = get_tokens(theme_name)
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,           QColor(t["window"]))
    p.setColor(QPalette.ColorRole.WindowText,       QColor(t["window_text"]))
    p.setColor(QPalette.ColorRole.Base,             QColor(t["base"]))
    p.setColor(QPalette.ColorRole.AlternateBase,    QColor(t["alternate_base"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,      QColor(t["base"]))
    p.setColor(QPalette.ColorRole.ToolTipText,      QColor(t["text"]))
    p.setColor(QPalette.ColorRole.Text,             QColor(t["text"]))
    p.setColor(QPalette.ColorRole.Button,           QColor(t["button"]))
    p.setColor(QPalette.ColorRole.ButtonText,       QColor(t["button_text"]))
    p.setColor(QPalette.ColorRole.BrightText,       QColor("#ff0000") if theme_name == "dark" else QColor("#cc0000"))
    p.setColor(QPalette.ColorRole.Highlight,        QColor(t["highlight"]))
    p.setColor(QPalette.ColorRole.HighlightedText,  QColor(t["highlighted_text"]))
    app.setPalette(p)
