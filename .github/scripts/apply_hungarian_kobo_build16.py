from pathlib import Path
import os


cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")
text = cpp.read_text(encoding="utf-8")

# Build #16 goals:
# 1) Make normal Hungarian Liang-pattern opportunities independent from the
#    current line width when they are used to veto a nearby heuristic compact
#    doubled-digraph/trigraph split (e.g. rosszfiúkat).
# 2) Keep the genuine ddzs compact-doubling restoration even if the ordinary
#    pattern engine proposes a raw split at the same source offset
#    (e.g. briddzsező -> bridzs-dzsező, not brid-ddzsező).
# 3) Append the GitHub Actions build number to the Extended Hungarian
#    hyphenation menu label without changing translation keys.
#
# Build #13 full-context rendered-width accounting is intentionally untouched.

# The Build #15 safety-net contained an earlier misspelled regression token
# (bridzzsel). Remove only that temporary exact-word guard; ddzs handling below
# is structural and covers correctly spelled briddz... forms.
text = text.replace(
"    static const lChar32 extra1[] = { 'b','r','i','d','z','z','s','e','l' }; // bridzzsel\n",
"",
1,
)
text = text.replace(
"    if ( len == 9 && huWordEquals(text, extra1, 9) ) return true;\n",
"",
1,
)

old_helper = '''static bool huNearbyPatternBreakWins( const lUInt16 * flags, int len, int break_after,
                                      int replacement_len ) {
    // CrossPoint Round2 principle: prefer an ordinary Hungarian pattern break
    // at the natural boundary after a compact doubled digraph/trigraph instead
    // of a heuristic replacement inside the compact spelling.
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

'''
new_helper = '''static bool huNearbyPatternBreakWins( const lUInt16 * pattern_flags_all, int len,
                                      int break_after, int replacement_len ) {
    // Language first, line fitting second: pattern_flags_all is generated with
    // an effectively unlimited width, so a valid Hungarian pattern boundary
    // can veto a nearby heuristic replacement even when that boundary would
    // not fit on the current rendered line.
    int lookahead = replacement_len > 1 ? 3 : 2;
    int last = break_after + lookahead;
    if ( last >= len )
        last = len - 1;
    for ( int k=break_after + 1; k<=last; k++ ) {
        if ( pattern_flags_all[k] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
            return true;
    }
    return false;
}

'''
if text.count(old_helper) != 1:
    raise SystemExit(f"Build16 helper marker: expected exactly one match, found {text.count(old_helper)}")
text = text.replace(old_helper, new_helper, 1)

old_decl = '''static bool huAddExtendedHyphenation( const lChar32 * text, int len, lUInt16 * flags,
                                      int left_hyphen_min, int right_hyphen_min ) {'''
new_decl = '''static bool huAddExtendedHyphenation( const lChar32 * text, int len, lUInt16 * flags,
                                      const lUInt16 * pattern_flags_all,
                                      int left_hyphen_min, int right_hyphen_min ) {'''
if text.count(old_decl) != 1:
    raise SystemExit(f"Build16 huAdd declaration marker: expected exactly one match, found {text.count(old_decl)}")
text = text.replace(old_decl, new_decl, 1)

old_priority = '''        // Normal Hungarian pattern breaks have priority over the heuristic
        // replacement, both at the exact offset and at the completed compact
        // digraph/trigraph boundary.
        if ( flags[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
            continue;
        if ( huNearbyPatternBreakWins(flags, len, i, replacement_len) )
            continue;
        int split = i + 1;
        if ( split < left_hyphen_min || len - split < right_hyphen_min )
            continue;
        if ( !huHasVowel(text, 0, split) || !huHasVowel(text, split, len) )
            continue;
        flags[i] |= LCHAR_ALLOW_HYPH_WRAP_AFTER | LCHAR_HUNGARIAN_HYPH_REPLACE;
'''
new_priority = '''        int split = i + 1;
        if ( split < left_hyphen_min || len - split < right_hyphen_min )
            continue;
        if ( !huHasVowel(text, 0, split) || !huHasVowel(text, split, len) )
            continue;

        if ( replacement_len > 1 ) {
            // ddzs is the compact written form of doubled dzs. A raw ordinary
            // break at this same source offset would render brid-ddz..., while
            // the replacement restores the full trigraph: bridzs-dzs....
            // Once the candidate is otherwise legal, the replacement wins at
            // this exact offset.
            flags[i] &= ~LCHAR_ALLOW_HYPH_WRAP_AFTER;
        } else {
            // For single-character restorations (ssz, ggy, lly, nny, tty,
            // ccs, ddz, zzs...), ordinary Hungarian pattern boundaries win,
            // using the width-independent map rather than the current-line map.
            if ( pattern_flags_all[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
                continue;
            if ( huNearbyPatternBreakWins(pattern_flags_all, len, i, replacement_len) )
                continue;
        }
        flags[i] |= LCHAR_ALLOW_HYPH_WRAP_AFTER | LCHAR_HUNGARIAN_HYPH_REPLACE;
'''
if text.count(old_priority) != 1:
    raise SystemExit(f"Build16 priority loop marker: expected exactly one match, found {text.count(old_priority)}")
text = text.replace(old_priority, new_priority, 1)

old_call = '''                    if ( TextLangMan::getHyphenationHungarianExtended() &&
                         m_srcs[wordpos]->lang_cfg->isHungarian() ) {
                        int left_hyphen_min = HyphMan::getLeftHyphenMin();
                        int right_hyphen_min = HyphMan::getRightHyphenMin();
                        if ( !left_hyphen_min )
                            left_hyphen_min = hyph_method->getLeftHyphenMin();
                        if ( !right_hyphen_min )
                            right_hyphen_min = hyph_method->getRightHyphenMin();
                        hyphen_found = huAddExtendedHyphenation(m_text+wstart, len, m_flags+wstart,
                                                               left_hyphen_min, right_hyphen_min) || hyphen_found;
                    }
'''
new_call = '''                    if ( TextLangMan::getHyphenationHungarianExtended() &&
                         m_srcs[wordpos]->lang_cfg->isHungarian() ) {
                        int left_hyphen_min = HyphMan::getLeftHyphenMin();
                        int right_hyphen_min = HyphMan::getRightHyphenMin();
                        if ( !left_hyphen_min )
                            left_hyphen_min = hyph_method->getLeftHyphenMin();
                        if ( !right_hyphen_min )
                            right_hyphen_min = hyph_method->getRightHyphenMin();

                        // Generate a second, width-independent pattern map used
                        // only for language-priority decisions. The normal map
                        // above remains width-filtered for actual line fitting.
                        lUInt16 * hu_pattern_flags_all = (lUInt16*)calloc(len, sizeof(lUInt16));
                        if ( hu_pattern_flags_all ) {
                            hyph_method->hyphenate(m_text+wstart, len, widths,
                                                  (lUInt8*)hu_pattern_flags_all,
                                                  _hyphen_width, 0xFFFF, 2);
                        }
                        const lUInt16 * hu_priority_flags = hu_pattern_flags_all
                                                          ? hu_pattern_flags_all
                                                          : m_flags+wstart;
                        hyphen_found = huAddExtendedHyphenation(m_text+wstart, len, m_flags+wstart,
                                                               hu_priority_flags,
                                                               left_hyphen_min, right_hyphen_min) || hyphen_found;
                        if ( hu_pattern_flags_all )
                            free(hu_pattern_flags_all);
                    }
'''
if text.count(old_call) != 1:
    raise SystemExit(f"Build16 Hungarian call-site marker: expected exactly one match, found {text.count(old_call)}")
text = text.replace(old_call, new_call, 1)

cpp.write_text(text, encoding="utf-8")

# Append the Actions run number to the translated menu label at build time.
build_number = os.environ.get("HUNGARIAN_BUILD_NUMBER", "").strip()
if not build_number:
    raise SystemExit("HUNGARIAN_BUILD_NUMBER is required")

lua = Path("frontend/apps/reader/modules/readertypography.lua")
lua_text = lua.read_text(encoding="utf-8")
menu_old = '        text = _("Extended Hungarian hyphenation"),\n'
menu_new = f'        text = _("Extended Hungarian hyphenation") .. " #{build_number}",\n'
if lua_text.count(menu_old) != 1:
    raise SystemExit(f"Build16 menu label marker: expected exactly one match, found {lua_text.count(menu_old)}")
lua_text = lua_text.replace(menu_old, menu_new, 1)
summary_old = '                method = _("Extended Hungarian hyphenation")\n'
summary_new = f'                method = _("Extended Hungarian hyphenation") .. " #{build_number}"\n'
if lua_text.count(summary_old) == 1:
    lua_text = lua_text.replace(summary_old, summary_new, 1)
lua.write_text(lua_text, encoding="utf-8")

print(f"Kobo build #{build_number} Hungarian hyphenation fixes applied successfully")
