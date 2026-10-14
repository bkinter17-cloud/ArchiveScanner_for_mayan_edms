"""رموز التصميم والثوابت البصرية للتطبيق."""

# ---- لوحة الألوان ----------------------------------------------------------
BG             = "#f8fafc"
SURFACE        = "#ffffff"
BORDER         = "#e2e8f0"
TEXT           = "#0f172a"
MUTED          = "#64748b"
SIDEBAR_TOP    = "#0f172a"
SIDEBAR_BOTTOM = "#1e293b"
ACCENT         = "#4f46e5"
ACCENT_DARK    = "#4338ca"
ACCENT_LIGHT   = "#eef2ff"
ACCENT_GLOW    = "#c7d2fe"
MINT           = "#06b6d4"
SUCCESS        = "#059669"
SUCCESS_DARK   = "#047857"
SUCCESS_LIGHT  = "#ecfdf5"
DANGER         = "#dc2626"
DANGER_LIGHT   = "#fef2f2"

# ---- الخطوط ----------------------------------------------------------------
FONT_STACK = (
    "'Segoe UI', 'Arial', 'Tahoma', 'Microsoft Sans Serif', system-ui, sans-serif"
)

# ---- ورقة الأنماط الرئيسية -------------------------------------------------
STYLESHEET = f"""
QWidget {{ font-family: {FONT_STACK}; font-size: 10.5pt; color: {TEXT}; }}
QMainWindow, #root {{ background: {BG}; }}

/* ---------- الشريط الجانبي ---------- */
#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {SIDEBAR_TOP}, stop:1 {SIDEBAR_BOTTOM});
    border-left: 1px solid rgba(255, 255, 255, 0.05);
}}
#sidebarMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {ACCENT}, stop:1 {MINT});
    color: white; font-size: 15pt; font-weight: 800; border-radius: 12px;
}}
#brand        {{ color: #ffffff; font-size: 13pt; font-weight: 800; letter-spacing: 0.5px; }}
#brandCaption {{ color: #94a3b8; font-size: 8.5pt; }}
#sidebarDivider {{ background: rgba(255, 255, 255, 0.08); border: none; }}

#navButton, #navActive {{
    text-align: right; color: #cbd5e1; background: transparent; border: none;
    border-radius: 12px; padding: 0 16px; font-size: 10.5pt; font-weight: 600;
}}
#navButton:hover {{ background: rgba(255, 255, 255, 0.08); color: #ffffff; }}
#navActive {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
    color: #ffffff; font-weight: 700;
}}

#avatarBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1e293b, stop:1 #334155);
    color: {MINT}; border: 1.5px solid rgba(6, 182, 212, 0.4);
    border-radius: 18px; font-weight: 800;
}}
#userName  {{ color: #ffffff; font-weight: 700; font-size: 9.5pt; }}
#userState {{ color: #34d399; font-size: 8pt; font-weight: 600; }}
#logoutButton {{
    text-align: right; color: #fca5a5;
    background: rgba(239, 68, 68, 0.06);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 12px; padding: 0 16px; font-weight: 600;
}}
#logoutButton:hover {{
    background: rgba(239, 68, 68, 0.16);
    border-color: {DANGER}; color: #ffffff;
}}

/* ---------- الترويسة ---------- */
#pageTitle    {{
    font-size: 17pt; font-weight: 800; color: {TEXT};
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}
#pageSubtitle {{
    font-size: 9.5pt; color: {MUTED};
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}
#chip {{
    background: {SURFACE}; color: {MUTED}; border: 1px solid {BORDER};
    border-radius: 16px; padding: 6px 14px; font-size: 9pt; font-weight: 600;
}}
#statusChip {{
    background: #f1f5f9; color: #475569; border-radius: 16px;
    padding: 6px 14px; font-size: 9pt; font-weight: 700;
}}
#statusChip[state="busy"]    {{ background: #eff6ff; color: #1d4ed8; }}
#statusChip[state="success"] {{ background: {SUCCESS_LIGHT}; color: {SUCCESS_DARK}; }}
#statusChip[state="error"]   {{ background: {DANGER_LIGHT};  color: {DANGER}; }}

/* ---------- البطاقات ---------- */
#card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 18px;
}}
#sectionTitle {{
    font-size: 11pt; font-weight: 700; color: {TEXT};
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}
#divider {{ background: {BORDER}; border: none; }}

/* ---------- عناصر النموذج ---------- */
#fieldLabel {{
    font-size: 9pt; font-weight: 600; color: {MUTED};
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}
QLineEdit, QTextEdit, QComboBox {{
    background: {SURFACE}; border: 1.5px solid {BORDER};
    border-radius: 10px; padding: 8px 14px; font-size: 10pt; color: {TEXT};
    min-width: 60px;
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover  {{ border-color: #cbd5e1; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus  {{
    border-color: {ACCENT}; background: #ffffff;
}}
QLineEdit[invalid="true"] {{
    border-color: {DANGER}; background: {DANGER_LIGHT};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: top left;
    width: 32px; border: none;
}}
QComboBox::down-arrow  {{ width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_LIGHT}; selection-color: {ACCENT};
    padding: 4px; border-radius: 8px;
}}

/* ---------- الأزرار ---------- */
#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
    color: white; border: none; border-radius: 10px;
    font-weight: 700; font-size: 10pt; padding: 0 20px;
}}
#primaryButton:hover    {{ background: {ACCENT_DARK}; }}
#primaryButton:disabled {{ background: #94a3b8; color: #e2e8f0; }}

#successButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {SUCCESS}, stop:1 {SUCCESS_DARK});
    color: white; border: none; border-radius: 10px;
    font-weight: 700; font-size: 10pt; padding: 0 20px;
}}
#successButton:hover    {{ background: {SUCCESS_DARK}; }}
#successButton:disabled {{ background: #94a3b8; color: #e2e8f0; }}

#ghostButton {{
    background: transparent; color: {MUTED}; border: 1.5px solid {BORDER};
    border-radius: 10px; font-weight: 600; font-size: 9.5pt;
    padding: 0 14px; min-width: 72px;
}}
#ghostButton:hover {{ background: #f1f5f9; color: {TEXT}; border-color: #cbd5e1; }}
#ghostButton:disabled {{ color: #94a3b8; background: #f8fafc; border-color: #e2e8f0; }}

#filePill {{
    background: #f8fafc; color: {MUTED}; border: 1px dashed #cbd5e1;
    border-radius: 10px; padding: 10px 14px; font-size: 9pt;
}}

/* ---------- الجدول ---------- */
QTableWidget {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 12px; gridline-color: #f1f5f9; outline: none;
}}
QTableWidget::item {{
    padding: 10px 12px; border-bottom: 1px solid #f1f5f9;
}}
QTableWidget::item:selected {{
    background: {ACCENT_LIGHT}; color: {ACCENT_DARK}; font-weight: 600;
}}
QHeaderView::section {{
    background: #f8fafc; color: {MUTED}; font-weight: 700; font-size: 8.5pt;
    border: none; border-bottom: 1.5px solid {BORDER};
    padding: 8px 12px; text-align: right;
}}

/* ---------- شاشة تسجيل الدخول ---------- */
#brandPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {SIDEBAR_TOP}, stop:1 {SIDEBAR_BOTTOM});
    border-left: 1px solid rgba(255, 255, 255, 0.05);
}}
#brandMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {ACCENT}, stop:1 {MINT});
    color: white; font-size: 26pt; font-weight: 800; border-radius: 20px;
}}
#brandTitle   {{ color: #ffffff; font-size: 20pt; font-weight: 800; }}
#brandSubtitle {{ color: #94a3b8; font-size: 10pt; line-height: 1.5; }}
#brandBullet  {{ color: {MINT}; font-size: 8pt; }}
#brandFeature {{ color: #e2e8f0; font-size: 9.5pt; }}

#loginPanel   {{ background: {SURFACE}; }}
#loginHeading {{
    font-size: 20pt; font-weight: 800; color: {TEXT};
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}
#loginStatus  {{
    font-size: 9pt; min-height: 18px;
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}
#loginStatus[state="info"]  {{ color: {ACCENT}; }}
#loginStatus[state="error"] {{ color: {DANGER}; font-weight: 600; }}
#serverCaption {{
    color: #94a3b8; font-size: 8.5pt; font-style: italic;
    qproperty-alignment: 'AlignRight | AlignAbsolute | AlignVCenter';
    text-align: right;
}}

/* ---------- حوارات الرسائل ---------- */
QMessageBox        {{ font-family: {FONT_STACK}; }}
QMessageBox QLabel {{ font-size: 10pt; }}

/* ---------- منطقة التمرير ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ---------- شريط التمرير ---------- */
QScrollBar:vertical {{
    background: #f1f5f9; width: 8px; border-radius: 4px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #94a3b8; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; border: none; background: none; }}
"""
