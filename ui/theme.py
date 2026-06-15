from PyQt6.QtGui import QPalette, QColor

THEMES = {
    "dark": {
        # Semantic text / UI tokens
        "label_secondary":   "#909090",
        "label_muted":       "#686868",
        "label_faint":       "#4E4E4E",
        "value_text":        "#E0E0E0",
        "separator":         "#555555",
        "separator_strong":  "#3a3a3a",
        "donut_center":      "#353535",
        # Qt palette
        "window":            "#353535",
        "window_text":       "#E0E0E0",
        "base":              "#232323",
        "alternate_base":    "#353535",
        "text":              "#E0E0E0",
        "button":            "#353535",
        "button_text":       "#E0E0E0",
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
        # Semantic text / UI tokens
        "label_secondary":   "#5A5A5A",
        "label_muted":       "#848484",
        "label_faint":       "#ABABAB",
        "value_text":        "#222222",
        "separator":         "#cccccc",
        "separator_strong":  "#dddddd",
        "donut_center":      "#f0f0f0",
        # Qt palette
        "window":            "#f0f0f0",
        "window_text":       "#222222",
        "base":              "#ffffff",
        "alternate_base":    "#e9e9e9",
        "text":              "#222222",
        "button":            "#e1e1e1",
        "button_text":       "#222222",
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


_FONT_SCALE = {
    "font_micro":   "10px",   # disclaimers, timestamps
    "font_small":   "11px",   # stat keys, secondary labels
    "font_body":    "12px",   # body text, list items
    "font_title":   "13px",   # section titles, main UI text
    "font_subhead": "15px",   # panel subheadings, price change
    "font_heading": "16px",   # dialog / page headers
    "font_value":   "22px",   # value displays, inline scores
    "font_name":    "24px",   # profile name heading
    "font_symbol":  "26px",   # stock ticker symbol
    "font_price":   "32px",   # current price large display
    "font_score":   "52px",   # AI analysis score number
}

_SIGNAL_COLORS = {
    "buy_color":  "#00cc66",
    "sell_color": "#ff4444",
    "hold_color": "#ffaa00",
}


def get_tokens(theme_name: str) -> dict:
    t = dict(THEMES.get(theme_name, THEMES["dark"]))
    t.update(_FONT_SCALE)
    t.update(_SIGNAL_COLORS)
    return t


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
