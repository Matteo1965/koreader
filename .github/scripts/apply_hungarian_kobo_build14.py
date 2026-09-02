from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Kobo build #14: port the CrossPoint Hungarian break-priority rule to CREngine.
#
# CrossPoint's proven rule is that an ordinary Hungarian language-pattern break
# must beat a heuristic compact-digraph/trigraph replacement when they collide.
# CREngine already skips an extended replacement when the pattern dictionary has
# a break at the exact same offset.  This patch extends that idea to the compact
# multi-letter sequence itself: if the dictionary provides a legal break after
# the completed digraph/trigraph, prefer that normal boundary instead of breaking
# inside the compact spelling.
#
# Examples this targets:
#   meggyből  : prefer meggy-ből over megy-gyből
#   Rosszfiú  : prefer rossz-fiú over Rosz-szfiú
# and analogous compound/morpheme-boundary collisions.
#
# The Build #13 full-source-context width fix is intentionally untouched.
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")

# Keep the existing regression blocklist as a safety net and add the four freshly
# observed cases.  Matching is case-insensitive through huWordEquals(), so this
# also covers Rosszfiú without a separate uppercase spelling.
old_guard_tail = '''    return false;
}

static int huHyphenReplacement( const lChar32 * text, int len, int break_after, lChar32 replacement[2] ) {
'''
new_guard_tail = '''    // Additional regression controls observed while validating the generalized
    // CrossPoint-style priority rule on Kobo build #13.
    static const lChar32 extra0[] = { 'm','e','g','g','y','b',0x0151,'l' }; // meggyből
    static const lChar32 extra1[] = { 'b','r','i','d','z','z','s','e','l' }; // bridzzsel
    static const lChar32 extra2[] = { 'e','d','d','z','e','n' }; // eddzen
    static const lChar32 extra3[] = { 'r','o','s','s','z','f','i',0x00FA }; // rosszfiú
    if ( len == 8 && huWordEquals(text, extra0, 8) ) return true;
    if ( len == 9 && huWordEquals(text, extra1, 9) ) return true;
    if ( len == 6 && huWordEquals(text, extra2, 6) ) return true;
    if ( len == 8 && huWordEquals(text, extra3, 8) ) return true;
    return false;
}

static bool huNearbyPatternBreakWins( const lUInt16 * flags, int len, int break_after,
                                      int replacement_len ) {
    // A compact doubled digraph consumes two following source codepoints; doubled
    // dzs consumes three.  If normal Hungarian patterns offer a break at/just after
    // the completed letter sequence, that is a stronger linguistic boundary than
    // the heuristic replacement inside it (CrossPoint Round2 priority rule).
    int lookahead = replacement_len > 1 ? 3 : 2;
    int last = break_after + lookahead;
    if ( last >= len )
        last = len - 1;
    for ( int k=break_after + 1; k<=last; k++ ) {
        if ( flags[k] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
            return true;
    }
    return false;
}

static int huHyphenReplacement( const lChar32 * text, int len, int break_after, lChar32 replacement[2] ) {
'''
replace_once(cpp, old_guard_tail, new_guard_tail, "add CrossPoint-style nearby pattern priority helper")

old_loop = '''    for ( int i=0; i<len; i++ ) {
        lChar32 replacement[2];
        if ( !huHyphenReplacement(text, len, i, replacement) )
            continue;
        // If the Hungarian pattern dictionary already provides a break at this exact
        // position, it wins over the heuristic replacement.
        if ( flags[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
            continue;
        int split = i + 1;
'''
new_loop = '''    for ( int i=0; i<len; i++ ) {
        lChar32 replacement[2];
        int replacement_len = huHyphenReplacement(text, len, i, replacement);
        if ( !replacement_len )
            continue;
        // CrossPoint priority port: a normal Hungarian pattern break wins over the
        // heuristic replacement, first at the exact offset, then at the natural
        // boundary immediately after the completed compact digraph/trigraph.
        if ( flags[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
            continue;
        if ( huNearbyPatternBreakWins(flags, len, i, replacement_len) )
            continue;
        int split = i + 1;
'''
replace_once(cpp, old_loop, new_loop, "prefer nearby normal Hungarian pattern boundary")

print("Kobo build #14 CrossPoint Hungarian priority rules applied successfully")
