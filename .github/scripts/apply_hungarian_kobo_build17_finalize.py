from pathlib import Path

crroot = Path("base/thirdparty/kpvcrlib/crengine/crengine")

# Make the new dialogue CR hint inheritable, like the existing paragraph-level
# CJK/strut hints, so inline spans inside a paragraph retain the opt-in state.
hint_header = None
for candidate in (crroot / "include").glob("*.h"):
    text = candidate.read_text(encoding="utf-8")
    if "CSS_CR_HINT_INHERITABLE_MASK" in text and "CSS_CR_HINT_DIALOGUE_FIX" in text:
        hint_header = candidate
        break
if hint_header is None:
    raise SystemExit("Dialogue CR hint header not found")
text = hint_header.read_text(encoding="utf-8")
old = "#define CSS_CR_HINT_INHERITABLE_MASK        0x0000000E\n"
new = "#define CSS_CR_HINT_INHERITABLE_MASK        0x0000004E\n"
if old not in text:
    raise SystemExit("CR hint inheritable mask anchor not found")
hint_header.write_text(text.replace(old, new, 1), encoding="utf-8")

# Also map the inherited hint while walking inline descendants. This mirrors
# the established STRUT_CONFINED propagation path.
lvrend = crroot / "src/lvrend.cpp"
text = lvrend.read_text(encoding="utf-8")
old = '''        else if ( STYLE_HAS_CR_HINT(style, STRUT_CONFINED) ) {
            // Previous branch for the top final node has set the strut.
            // Inline nodes having "-cr-hint: strut-confined" will be confined
            // inside that strut.
            flags |= LTEXT_STRUT_CONFINED;
        }

        // Other inherited CSS properties that don't need a special flag.
'''
new = '''        else if ( STYLE_HAS_CR_HINT(style, STRUT_CONFINED) ) {
            // Previous branch for the top final node has set the strut.
            // Inline nodes having "-cr-hint: strut-confined" will be confined
            // inside that strut.
            flags |= LTEXT_STRUT_CONFINED;
        }
        if ( STYLE_HAS_CR_HINT(style, DIALOGUE_FIX) )
            flags |= LTEXT_DIALOGUE_FIX;

        // Other inherited CSS properties that don't need a special flag.
'''
if text.count(old) != 1:
    raise SystemExit(f"inline dialogue hint propagation anchor: expected exactly one match, found {text.count(old)}")
lvrend.write_text(text.replace(old, new, 1), encoding="utf-8")

print("Kobo dialogue fix hardening applied successfully")
