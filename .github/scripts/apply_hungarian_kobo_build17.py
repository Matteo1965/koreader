from pathlib import Path
import os


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_po_entry(path, msgid, msgstr, source):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Missing translation file: {p}")
    text = p.read_text(encoding="utf-8")
    marker = f'msgid "{msgid}"'
    if marker in text:
        return
    text += f'\n#: {source}\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n'
    p.write_text(text, encoding="utf-8")


build_number = os.environ.get("HUNGARIAN_BUILD_NUMBER", "").strip()
if not build_number:
    raise SystemExit("HUNGARIAN_BUILD_NUMBER is required")

# -----------------------------------------------------------------------------
# 1) Typography menu: keep the full build-tagged label inside the submenu,
#    but use a compact localized summary on the parent Typography rules page.
# -----------------------------------------------------------------------------
lua = "frontend/apps/reader/modules/readertypography.lua"
replace_once(
    lua,
    f'                method = _("Extended Hungarian hyphenation") .. " #{build_number}"\n',
    '                method = _("Extended Hungarian")\n',
    "compact Extended Hungarian summary",
)

# -----------------------------------------------------------------------------
# 2) Style tweaks UI: expose the dialogue fix as an opt-in paragraph tweak.
#    The CSS hint is intentionally language-independent.
# -----------------------------------------------------------------------------
css_tweaks = "frontend/ui/data/css_tweaks.lua"
paragraph_anchor = '''    {
        title = _("Paragraphs"),
        {
            id = "paragraph_web_browser_style",
'''
paragraph_replacement = '''    {
        title = _("Paragraphs"),
        {
            id = "paragraph_dialogue_fix",
            title = _("Fix dialogue lines"),
            description = _([[Keep the space after a paragraph-opening en dash or em dash fixed and unbreakable.
This prevents the opening dialogue dash from being left alone at the end of a line and keeps the gap from stretching in justified text.]]),
            css = [[p { -cr-hint: dialogue-fix; }]],
            separator = true,
        },
        {
            id = "paragraph_web_browser_style",
'''
replace_once(css_tweaks, paragraph_anchor, paragraph_replacement, "dialogue Style tweak")

# -----------------------------------------------------------------------------
# 3) CREngine CSS hint and source-fragment flag.
#    Use currently-unused bits so existing KOReader/CREngine behaviour is untouched
#    when the Style tweak is disabled.
# -----------------------------------------------------------------------------
crroot = Path("base/thirdparty/kpvcrlib/crengine/crengine")

# Locate the header that owns the existing CR hint bit definitions.
hint_header = None
for candidate in (crroot / "include").glob("*.h"):
    data = candidate.read_text(encoding="utf-8")
    if "CSS_CR_HINT_CJK_TAILORED" in data and "#define CSS_CR_HINT_" in data:
        hint_header = candidate
        break
if hint_header is None:
    raise SystemExit("Could not locate CSS CR hint definitions")
hints = hint_header.read_text(encoding="utf-8")
if "CSS_CR_HINT_DIALOGUE_FIX" not in hints:
    lines = hints.splitlines(keepends=True)
    inserted = False
    for idx, line in enumerate(lines):
        if line.startswith("#define CSS_CR_HINT_CJK_TAILORED"):
            lines.insert(idx + 1, "#define CSS_CR_HINT_DIALOGUE_FIX          0x00000040 // Keep paragraph-opening dialogue dash + space together\n")
            inserted = True
            break
    if not inserted:
        raise SystemExit("CSS_CR_HINT_CJK_TAILORED definition not found")
    hint_header.write_text("".join(lines), encoding="utf-8")

lvtextfm_h = crroot / "include/lvtextfm.h"
flags = lvtextfm_h.read_text(encoding="utf-8")
old_flag = "#define LTEXT__AVAILABLE_BIT_23__    0x00400000\n"
new_flag = "#define LTEXT_DIALOGUE_FIX           0x00400000  // Keep paragraph-opening dialogue dash + following space together\n"
if old_flag not in flags:
    raise SystemExit("Available LTEXT bit 23 marker not found")
lvtextfm_h.write_text(flags.replace(old_flag, new_flag, 1), encoding="utf-8")

# Teach -cr-hint parser about dialogue-fix.
lvstsheet = crroot / "src/lvstsheet.cpp"
text = lvstsheet.read_text(encoding="utf-8")
old = '                        else if ( substr_icompare("cjk-tailored", decl) )           hints |= CSS_CR_HINT_CJK_TAILORED;\n'
new = old + '                        else if ( substr_icompare("dialogue-fix", decl) )           hints |= CSS_CR_HINT_DIALOGUE_FIX;\n'
if text.count(old) != 1:
    raise SystemExit(f"dialogue CR hint parser anchor: expected exactly one match, found {text.count(old)}")
lvstsheet.write_text(text.replace(old, new, 1), encoding="utf-8")

# Propagate the block-level CR hint into formatted-text source fragments.
lvrend = crroot / "src/lvrend.cpp"
text = lvrend.read_text(encoding="utf-8")
old = '''            if ( STYLE_HAS_CR_HINT(style, STRUT_CONFINED) )
                flags |= LTEXT_STRUT_CONFINED;
'''
new = old + '''            if ( STYLE_HAS_CR_HINT(style, DIALOGUE_FIX) )
                flags |= LTEXT_DIALOGUE_FIX;
'''
count = text.count(old)
if count < 1:
    raise SystemExit("CRE render hint propagation anchor not found")
# The first occurrence is the final-block setup that seeds flags inherited by inline fragments.
text = text.replace(old, new, 1)
lvrend.write_text(text, encoding="utf-8")

# -----------------------------------------------------------------------------
# 4) CREngine line preparation: for an opted-in paragraph beginning with an
#    en dash (U+2013) or em dash (U+2014) followed by a regular source space:
#      - forbid wrapping between dash and first word;
#      - lock that one space so justification cannot stretch it.
#    No text is rewritten, and there is no language check.
#
#    Insert after copyText() has normalized/collapsed spaces and set m_flags.
#    This anchor exists in the current CREngine baseline and is deliberately
#    independent from the Hungarian Build #3/#12/#13/#15/#16 patches.
# -----------------------------------------------------------------------------
lvtextfm = crroot / "src/lvtextfm.cpp"
text = lvtextfm.read_text(encoding="utf-8")
anchor = '        TR("%s", LCSTR(lString32(m_text, m_length)));\n\n'
if text.count(anchor) != 1:
    raise SystemExit(f"dialogue line-fix insertion anchor: expected exactly one match, found {text.count(anchor)}")
block = r'''        // Optional language-independent dialogue-line fix, enabled via
        // Style tweaks > Paragraphs > Fix dialogue lines.
        // Keep a paragraph-opening en/em dash and its following source space
        // together, and prevent text justification from stretching that gap.
        if ( m_length > 2 ) {
            int dialogue_start = 0;
            while ( dialogue_start < m_length &&
                    (m_flags[dialogue_start] & (LCHAR_IS_SPACE | LCHAR_IS_COLLAPSED_SPACE)) )
                dialogue_start++;
            if ( dialogue_start + 1 < m_length && m_srcs[dialogue_start] &&
                 (m_srcs[dialogue_start]->flags & LTEXT_DIALOGUE_FIX) &&
                 (m_text[dialogue_start] == 0x2013 || m_text[dialogue_start] == 0x2014) &&
                 (m_flags[dialogue_start + 1] & LCHAR_IS_SPACE) ) {
                m_flags[dialogue_start] &= ~LCHAR_ALLOW_WRAP_AFTER;
                m_flags[dialogue_start + 1] &= ~LCHAR_ALLOW_WRAP_AFTER;
                m_flags[dialogue_start] |= LCHAR_LOCKED_SPACING;
                m_flags[dialogue_start + 1] |= LCHAR_LOCKED_SPACING;
            }
        }

'''
text = text.replace(anchor, block + anchor, 1)
lvtextfm.write_text(text, encoding="utf-8")

# -----------------------------------------------------------------------------
# 5) Hungarian localization for the new compact summary and Style tweak.
#    English is the msgid/fallback. Existing full Extended Hungarian label stays
#    untouched, so Build #16's #<run> suffix remains visible inside the submenu.
# -----------------------------------------------------------------------------
append_po_entry(
    "l10n/hu/koreader.po",
    "Extended Hungarian",
    "Kiterjesztett magyar",
    "frontend/apps/reader/modules/readertypography.lua",
)
append_po_entry(
    "l10n/hu/koreader.po",
    "Fix dialogue lines",
    "Párbeszédsorok javítása",
    "frontend/ui/data/css_tweaks.lua",
)
append_po_entry(
    "l10n/hu/koreader.po",
    "Keep the space after a paragraph-opening en dash or em dash fixed and unbreakable.\\nThis prevents the opening dialogue dash from being left alone at the end of a line and keeps the gap from stretching in justified text.",
    "A bekezdést nyitó nagykötőjel vagy gondolatjel utáni szóközt rögzített szélességűvé és nem törhetővé teszi.\\nÍgy a párbeszédjel nem marad egyedül a sor végén, és sorkizárt szövegben sem nyúlik meg az utána következő szóköz.",
    "frontend/ui/data/css_tweaks.lua",
)

print("Kobo build dialogue-line and compact-menu patches applied successfully")
