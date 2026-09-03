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

lua = "frontend/apps/reader/modules/readertypography.lua"
replace_once(
    lua,
    f'                method = _("Extended Hungarian hyphenation") .. " #{build_number}"\n',
    '                method = _("Extended Hungarian")\n',
    "compact Extended Hungarian summary",
)

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
            description = _([[Keep the space after a paragraph-opening dialogue dash fixed and unbreakable.
This prevents the opening dialogue dash from being left alone at the end of a line and keeps the gap from stretching in justified text.]]),
            css = [[p { -cr-hint: dialogue-fix; }]],
            separator = true,
        },
        {
            id = "paragraph_web_browser_style",
'''
replace_once(css_tweaks, paragraph_anchor, paragraph_replacement, "dialogue Style tweak")

crroot = Path("base/thirdparty/kpvcrlib/crengine/crengine")
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

lvstsheet = crroot / "src/lvstsheet.cpp"
text = lvstsheet.read_text(encoding="utf-8")
old = '                        else if ( substr_icompare("cjk-tailored", decl) )           hints |= CSS_CR_HINT_CJK_TAILORED;\n'
new = old + '                        else if ( substr_icompare("dialogue-fix", decl) )           hints |= CSS_CR_HINT_DIALOGUE_FIX;\n'
if text.count(old) != 1:
    raise SystemExit(f"dialogue CR hint parser anchor: expected exactly one match, found {text.count(old)}")
lvstsheet.write_text(text.replace(old, new, 1), encoding="utf-8")

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
text = text.replace(old, new, 1)
lvrend.write_text(text, encoding="utf-8")

# Apply the dialogue fix where CREngine already finalizes spacing flags for the
# first word. Build 18/19 applied it just after copyText(), but later text
# measurement reconstructs the flags that justification actually consumes.
lvtextfm = crroot / "src/lvtextfm.cpp"
text = lvtextfm.read_text(encoding="utf-8")
old = '''                                if ( first_word_len == 1 ) { // Previous word is a single char
                                    if ( k > 0 && isLeftPunctuation(m_text[k-1]) ) {
                                        // This space follows one of the common opening quotation marks or
                                        // dashes used to introduce a quotation or a part of a dialog:
                                        // https://en.wikipedia.org/wiki/Quotation_mark
                                        // Don't allow this space to change width, so text justification
                                        // doesn't move away next word, so that other similar paragraphs
                                        // get their real first words vertically aligned.
                                        flags[k] |= LCHAR_LOCKED_SPACING;
                                        // Also prevent that quotation mark or dash from getting
                                        // additional letter spacing for justification
                                        flags[k-1] |= LCHAR_LOCKED_SPACING;
                                        // If what's coming next is also such a char, continue doing that
                                        if ( k+1 < len && isLeftPunctuation(m_text[k+1]) ) {
                                            keep_checking = true;
                                        }
                                        //
                                        // Note: we do this check here, with the text still in logical
                                        // order, so we get that working with RTL text too (where, in
                                        // visual order, we'll have lost track of which word is the
                                        // first word - untested though).
                                    }
                                }
'''
new = '''                                if ( first_word_len == 1 ) { // Previous word is a single char
                                    int first_char_pos = start + k - 1;
                                    lChar32 dialogue_char = first_char_pos >= 0 ? m_text[first_char_pos] : 0;
                                    bool is_dialogue_dash = dialogue_char == 0x002D || // hyphen-minus
                                                            dialogue_char == 0x2012 || // figure dash
                                                            dialogue_char == 0x2013 || // en dash
                                                            dialogue_char == 0x2014 || // em dash
                                                            dialogue_char == 0x2015 || // horizontal bar
                                                            dialogue_char == 0x2212;   // minus sign
                                    bool dialogue_fix_requested = false;
                                    if ( is_dialogue_dash ) {
                                        // The hint can live on the final block source fragment or on
                                        // an inherited inline fragment. The formatter buffer contains
                                        // only this paragraph, so accept the hint from either location.
                                        for ( int si=0; si < m_pbuffer->srctextlen; si++ ) {
                                            if ( m_pbuffer->srctext[si].flags & LTEXT_DIALOGUE_FIX ) {
                                                dialogue_fix_requested = true;
                                                break;
                                            }
                                        }
                                    }
                                    if ( (k > 0 && isLeftPunctuation(m_text[k-1])) || dialogue_fix_requested ) {
                                        // Lock at the formatter text-measurement stage, where the flags
                                        // used by final justification are assembled.
                                        flags[k] |= LCHAR_LOCKED_SPACING;
                                        flags[k-1] |= LCHAR_LOCKED_SPACING;
                                        if ( dialogue_fix_requested ) {
                                            // Keep the opening dash and the following space together too.
                                            m_flags[first_char_pos] &= ~LCHAR_ALLOW_WRAP_AFTER;
                                            m_flags[start+k] &= ~LCHAR_ALLOW_WRAP_AFTER;
                                            flags[k] &= ~LCHAR_ALLOW_WRAP_AFTER;
                                        }
                                        // Preserve CREngine's existing handling of repeated opening punctuation.
                                        if ( k+1 < len && isLeftPunctuation(m_text[k+1]) ) {
                                            keep_checking = true;
                                        }
                                        //
                                        // Note: we do this check here, with the text still in logical
                                        // order, so we get that working with RTL text too (where, in
                                        // visual order, we'll have lost track of which word is the
                                        // first word - untested though).
                                    }
                                }
'''
if text.count(old) != 1:
    raise SystemExit(f"formatter dialogue integration anchor: expected exactly one match, found {text.count(old)}")
text = text.replace(old, new, 1)
lvtextfm.write_text(text, encoding="utf-8")

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
    "Keep the space after a paragraph-opening dialogue dash fixed and unbreakable.\\nThis prevents the opening dialogue dash from being left alone at the end of a line and keeps the gap from stretching in justified text.",
    "A bekezdést nyitó párbeszédjel utáni szóközt rögzített szélességűvé és nem törhetővé teszi.\\nÍgy a párbeszédjel nem marad egyedül a sor végén, és sorkizárt szövegben sem nyúlik meg az utána következő szóköz.",
    "frontend/ui/data/css_tweaks.lua",
)

print("Kobo formatter-stage dialogue-line and compact-menu patches applied successfully")
