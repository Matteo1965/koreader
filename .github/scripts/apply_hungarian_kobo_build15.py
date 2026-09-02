from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Kobo build #15: corrected port of the CrossPoint Hungarian break-priority rule.
# Build #14 failed before compilation because its insertion marker assumed
# huKnownFalseExtendedWord() was immediately followed by huHyphenReplacement().
# In the actual post-Build-3 source, huHyphenReplacement() comes first and the
# generated regression helpers are inserted after huHasVowel().  Anchor this
# patch on the stable huAddExtendedHyphenation() declaration instead.
#
# Build #13 full-source-context width accounting is intentionally untouched.
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")
text = cpp.read_text(encoding="utf-8")

# Add the freshly observed regression words inside the existing safety-net
# function. Matching remains case-insensitive through huWordEquals().
known_marker = '''static bool huKnownFalseExtendedWord( const lChar32 * text, int len ) {\n'''
start = text.find(known_marker)
if start < 0:
    raise SystemExit("huKnownFalseExtendedWord marker missing")
end_marker = '''    return false;\n}\n\n'''
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit("huKnownFalseExtendedWord end marker missing")
insert_at = end
extra = '''    static const lChar32 extra0[] = { 'm','e','g','g','y','b',0x0151,'l' }; // meggyből\n    static const lChar32 extra1[] = { 'b','r','i','d','z','z','s','e','l' }; // bridzzsel\n    static const lChar32 extra2[] = { 'e','d','d','z','e','n' }; // eddzen\n    static const lChar32 extra3[] = { 'r','o','s','s','z','f','i',0x00FA }; // rosszfiú\n    if ( len == 8 && huWordEquals(text, extra0, 8) ) return true;\n    if ( len == 9 && huWordEquals(text, extra1, 9) ) return true;\n    if ( len == 6 && huWordEquals(text, extra2, 6) ) return true;\n    if ( len == 8 && huWordEquals(text, extra3, 8) ) return true;\n'''
if "static const lChar32 extra0[]" not in text[start:end]:
    text = text[:insert_at] + extra + text[insert_at:]

# Add a helper immediately before huAddExtendedHyphenation(), whose declaration
# is stable across Builds #3/#4/#12/#13.
add_marker = '''static bool huAddExtendedHyphenation( const lChar32 * text, int len, lUInt16 * flags,\n                                      int left_hyphen_min, int right_hyphen_min ) {\n'''
if text.count(add_marker) != 1:
    raise SystemExit(f"huAddExtendedHyphenation marker: expected exactly one match, found {text.count(add_marker)}")
helper = '''static bool huNearbyPatternBreakWins( const lUInt16 * flags, int len, int break_after,\n                                      int replacement_len ) {\n    // CrossPoint Round2 principle: prefer an ordinary Hungarian pattern break\n    // at the natural boundary after a compact doubled digraph/trigraph instead\n    // of a heuristic replacement inside the compact spelling.\n    int lookahead = replacement_len > 1 ? 3 : 2;\n    int last = break_after + lookahead;\n    if ( last >= len )\n        last = len - 1;\n    for ( int k=break_after + 1; k<=last; k++ ) {\n        if ( flags[k] & LCHAR_ALLOW_HYPH_WRAP_AFTER )\n            return true;\n    }\n    return false;\n}\n\n'''
text = text.replace(add_marker, helper + add_marker, 1)

old_loop = '''    bool found = false;\n    for ( int i=0; i<len; i++ ) {\n        lChar32 replacement[2];\n        if ( !huHyphenReplacement(text, len, i, replacement) )\n            continue;\n        // If the Hungarian pattern dictionary already provides a break at this exact\n        // position, it wins over the heuristic replacement.\n        if ( flags[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )\n            continue;\n        int split = i + 1;\n'''
new_loop = '''    bool found = false;\n    for ( int i=0; i<len; i++ ) {\n        lChar32 replacement[2];\n        int replacement_len = huHyphenReplacement(text, len, i, replacement);\n        if ( !replacement_len )\n            continue;\n        // Normal Hungarian pattern breaks have priority over the heuristic\n        // replacement, both at the exact offset and at the completed compact\n        // digraph/trigraph boundary.\n        if ( flags[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )\n            continue;\n        if ( huNearbyPatternBreakWins(flags, len, i, replacement_len) )\n            continue;\n        int split = i + 1;\n'''
if text.count(old_loop) != 1:
    raise SystemExit(f"extended hyphenation loop: expected exactly one match, found {text.count(old_loop)}")
text = text.replace(old_loop, new_loop, 1)

cpp.write_text(text, encoding="utf-8")
print("Kobo build #15 corrected CrossPoint Hungarian priority rules applied successfully")
