"""
OsdagBridge report — centralized style configuration (single source of truth).

Every chapter generator imports its layout and visual settings from here instead
of hard-coding LaTeX lengths, colours, column specs or status strings.  Changing
a value in this module restyles the whole report.

Sections
--------
1. Page geometry        – margins, header/footer spacing
2. Colours              – brand and status colours
3. Typography           – base font size, line spacing, caption/table fonts
4. Table appearance     – padding, row height, rule width, row spacing
5. Column specs         – reusable longtable column layouts
6. Status helpers       – PASS / FAIL / not-available markers
7. Table builders       – longtable start/end with repeating headers
"""

# =============================================================================
# 1. PAGE GEOMETRY
# =============================================================================
PAGE = {
    "paper":      "a4paper",
    "top":        "1in",
    "bottom":     "1.1in",   # a little more room so table rows never reach the footer
    "left":       "1in",
    "right":      "1in",
    "headheight": "15pt",
    "headsep":    "12pt",
    "footskip":   "30pt",    # distance from last text line to footer baseline
}


def geometry_options():
    """Options string for \\usepackage[...]{geometry}."""
    return ", ".join([PAGE["paper"]] + [f"{k}={v}" for k, v in PAGE.items() if k != "paper"])


# =============================================================================
# 2. COLOURS  (HTML hex, no leading '#')
# =============================================================================
COLORS = {
    "osdagGreen":  "91B014",   # header/footer rules, accents
    "failRed":     "C62828",   # FAIL status text, threshold lines in charts
    "passGreen":   "2E7D32",   # optional PASS accent (charts)
    "headerFill":  "EEF4DC",   # table header row background
    "ruleGray":    "808080",
}


def define_colors():
    """\\definecolor lines for every colour in COLORS (goes in the preamble)."""
    return "\n".join(rf"\definecolor{{{name}}}{{HTML}}{{{hexv}}}" for name, hexv in COLORS.items())


def hex_color(name):
    """'#RRGGBB' for use in matplotlib charts, so charts match the PDF palette."""
    return "#" + COLORS[name]


# =============================================================================
# 3. TYPOGRAPHY
# =============================================================================
FONT = {
    "base_size":    "12pt",
    "line_stretch": "1.15",
    "table_size":   r"\small",       # font size used inside dense tables
    "caption_size": r"\normalsize",
    "note_size":    r"\footnotesize",
}


# =============================================================================
# 4. TABLE APPEARANCE
# =============================================================================
TABLE = {
    "tabcolsep":      "6pt",    # horizontal cell padding
    "arraystretch":   "1.12",   # row height multiplier
    "arrayrulewidth": "0.5pt",  # border thickness
    "extrarowheight": "0.6pt",
    "lt_pre":         "0pt",    # space before a longtable
    "lt_post":        "6pt",    # space after a longtable
    "row_gap":        "6pt",    # extra space after each body row (\\[6pt])
    "needspace":      "6",      # min. free lines before starting a table
}

ROW_END = r" \\[" + TABLE["row_gap"] + "]"   # use at the end of every body row


def table_preamble():
    """Global table settings for the document preamble."""
    return "\n".join([
        rf"\setlength{{\tabcolsep}}{{{TABLE['tabcolsep']}}}",
        rf"\renewcommand{{\arraystretch}}{{{TABLE['arraystretch']}}}",
        rf"\setlength{{\arrayrulewidth}}{{{TABLE['arrayrulewidth']}}}",
        rf"\setlength{{\extrarowheight}}{{{TABLE['extrarowheight']}}}",
        rf"\setlength{{\LTpre}}{{{TABLE['lt_pre']}}}",
        rf"\setlength{{\LTpost}}{{{TABLE['lt_post']}}}",
        r"\setlength{\LTleft}{\fill}",
        r"\setlength{\LTright}{\fill}",
        rf"\BeforeBeginEnvironment{{longtable}}{{\needspace{{{TABLE['needspace']}\baselineskip}}}}",
        rf"\BeforeBeginEnvironment{{table}}{{\needspace{{{TABLE['needspace']}\baselineskip}}}}",
    ])


# =============================================================================
# 5. COLUMN SPECS  (L/C/R{width} column types are defined in the preamble)
# =============================================================================
COLS = {
    # two-column "parameter | value" tables (Chapters 2 and 3)
    "kv":          r"|L{5.5cm}|p{10.0cm}|",
    # load-combination list (Chapter 3)
    "combo":       r"|C{4.0cm}|p{11.5cm}|",
    # per-girder check tables (Chapter 5)
    "check5":      r"|C{2.5cm}|C{3.5cm}|C{3.5cm}|>{\centering\arraybackslash}p{4.2cm}|C{1.8cm}|",
    # bill of materials (Chapter 7)
    "bom":         r"|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|",
}


# =============================================================================
# 6. STATUS HELPERS
# =============================================================================
PASS_TEXT = "PASS"
FAIL_TEXT = r"\textcolor{failRed}{\textbf{FAIL}}"
NA_TEXT = "---"


def status(ok):
    """PASS / FAIL / --- for a boolean (or None when not evaluated)."""
    if ok is None:
        return NA_TEXT
    return PASS_TEXT if ok else FAIL_TEXT


def highlight_fail(text):
    """Colour any string containing 'FAIL' with the failure style."""
    s = str(text)
    return rf"\textcolor{{failRed}}{{{s}}}" if "FAIL" in s.upper() else s


# =============================================================================
# 7. TABLE BUILDERS — headers repeat automatically on every page
# =============================================================================
def _header_row(headers):
    cells = " & ".join(rf"\textbf{{{h}}}" for h in headers)
    return r"\rowcolor{headerFill}" + "\n" + cells + r" \\"


def begin_table(colspec, headers, caption=None, label=None):
    """
    Open a longtable whose caption + header row repeat on every page.

    Uses \\endfirsthead / \\endhead so a table that breaks across pages keeps
    its column headers, and \\endfoot adds a 'continued' note at each break.
    """
    ncols = len(headers)
    head = _header_row(headers)
    cap = rf"\caption{{\textbf{{{caption}}}}}" + (rf"\label{{{label}}}" if label else "") + r"\\" if caption else ""
    cont_cap = rf"\caption[]{{\textbf{{{caption}}} \textit{{(continued)}}}}\\" if caption else ""
    return "\n".join([
        rf"\begin{{longtable}}{{{colspec}}}",
        # first page
        cap, r"\hline", head, r"\hline", r"\endfirsthead",
        # continuation pages
        cont_cap, r"\hline", head, r"\hline", r"\endhead",
        # bottom of every page except the last (body rows already end in \hline)
        rf"\multicolumn{{{ncols}}}{{r}}{{{FONT['note_size']}\textit{{Continued on next page}}}} \\",
        r"\endfoot",
        # bottom of the last page
        r"\endlastfoot",
    ])


def end_table():
    return r"\end{longtable}"


def kv_table(caption, rows, headers=("Parameter", "Value"), colspec=None):
    """
    Two-column parameter/value table.
    rows: iterable of (label, value) — both already LaTeX-safe strings.
    """
    body = "\n".join(rf"\textnormal{{{k}}} & {v}{ROW_END}" + "\n" + r"\hline" for k, v in rows)
    return "\n".join([
        begin_table(colspec or COLS["kv"], list(headers), caption),
        body,
        end_table(),
    ])
