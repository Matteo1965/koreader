from pathlib import Path

crroot = Path("base/thirdparty/kpvcrlib/crengine/crengine")
lvtextfm = crroot / "src/lvtextfm.cpp"
text = lvtextfm.read_text(encoding="utf-8")

# Build 18/19 applied the dialogue lock just after copyText(). That proved too
# early for the final formatter path: later text measurement reconstructs the
# spacing flags used by justification. Remove that early block entirely.
early_start = text.find("        // Optional language-independent dialogue-line fix, enabled via\n")
early_end_marker = '        TR("%s", LCSTR(lString32(m_text, m_length)));\n\n'
if early_start < 0:
    raise SystemExit("Build 18/19 early dialogue block start not found")
early_end = text.find(early_end_marker, early_start)
if early_end < 0:
    raise SystemExit("Build 18/19 early dialogue block end anchor not found")
text = text[:early_start] + text[early_end:]

# Keep the supported dialogue-dash set in one language-independent helper.
helper_anchor = '''static lChar32 huAsciiLower( lChar32 ch ) {
    return ch >= 'A' && ch <= 'Z' ? ch + ('a' - 'A') : ch;
}

'''
helper = helper_anchor + '''static bool isDialogueDashChar( lChar32 ch ) {
    switch ( ch ) {
        case 0x002D: // hyphen-minus
        case 0x2012: // figure dash
        case 0x2013: // en dash
        case 0x2014: // em dash
        case 0x2015: // horizontal bar
        case 0x2212: // minus sign
            return true;
        default:
            return false;
    }
}

'''
if text.count(helper_anchor) != 1:
    raise SystemExit(f"dialogue helper anchor: expected exactly one match, found {text.count(helper_anchor)}")
text = text.replace(helper_anchor, helper, 1)

# Apply the opt-in rule at the exact stage where CREngine already locks the
# first punctuation+space pair against text justification. This is late enough
# that LCHAR_LOCKED_SPACING survives into the final word/line construction.
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
                                    bool dialogue_fix_requested = false;
                                    if ( first_char_pos >= 0 && isDialogueDashChar(m_text[first_char_pos]) ) {
                                        // The paragraph hint may live on the final block source fragment
                                        // or on an inherited inline fragment. Accept either: the formatter
                                        // buffer contains only this paragraph's source fragments.
                                        for ( int si=0; si < m_pbuffer->srctextlen; si++ ) {
                                            if ( m_pbuffer->srctext[si].flags & LTEXT_DIALOGUE_FIX ) {
                                                dialogue_fix_requested = true;
                                                break;
                                            }
                                        }
                                    }
                                    if ( (k > 0 && isLeftPunctuation(m_text[k-1])) || dialogue_fix_requested ) {
                                        // This space follows one of the common opening quotation marks/dashes,
                                        // or an explicitly enabled dialogue dash. Lock it at the formatter's
                                        // text-measurement stage so justification cannot stretch the gap.
                                        flags[k] |= LCHAR_LOCKED_SPACING;
                                        flags[k-1] |= LCHAR_LOCKED_SPACING;
                                        if ( dialogue_fix_requested ) {
                                            // Keep dash + following space unbreakable as well. The previous
                                            // character has already been merged into m_flags; the current
                                            // space is still in local flags[], so clear both representations.
                                            m_flags[first_char_pos] &= ~LCHAR_ALLOW_WRAP_AFTER;
                                            m_flags[start+k] &= ~LCHAR_ALLOW_WRAP_AFTER;
                                            flags[k] &= ~LCHAR_ALLOW_WRAP_AFTER;
                                        }
                                        // Preserve CREngine's existing repeated-opening-punctuation handling.
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
print("Kobo Build 20 formatter-stage dialogue fix applied successfully")
