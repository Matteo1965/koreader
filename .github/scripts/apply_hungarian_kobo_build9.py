from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Kobo build #9: start from the Build-4 rendering path and correct the spacing
# accounting for the synthetic Hungarian characters themselves.
#
# Build #8's hanging-punctuation experiment is deliberately NOT part of this
# patch. The natural glyph advance is already supplied by Build 4's shaped
# huReplacementWidth(). What was still missing is spacing attached to the
# inserted glyph(s):
#   1) the source text's base letter_spacing; and
#   2) justification's later word->added_letter_spacing.
#
# One synthetic character therefore needs one additional spacing unit; the
# doubled-ddzs case restores two characters and needs two.  We account for the
# base spacing directly in word->width and add the synthetic glyph count to
# distinct_glyphs so alignLine() accounts for justification spacing with the
# same glyph count that DrawTextString() will actually render.
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")

old = '''                        if ( m_flags[i-1] & LCHAR_HUNGARIAN_HYPH_REPLACE ) {
                            word->width += huReplacementWidth(font, m_text+wstart, end-wstart, i-1-wstart);
                            word->flags |= LTEXT_WORD_HUNGARIAN_HYPH_REPLACE;
                        }
'''

new = '''                        if ( m_flags[i-1] & LCHAR_HUNGARIAN_HYPH_REPLACE ) {
                            lChar32 hu_replacement[2];
                            int hu_replacement_len = huHyphenReplacement(
                                    m_text+wstart, end-wstart, i-1-wstart, hu_replacement);
                            word->width += huReplacementWidth(
                                    font, m_text+wstart, end-wstart, i-1-wstart);

                            // huReplacementWidth() covers the shaped natural advance.
                            // The synthetic glyphs also participate in the source-level
                            // letter spacing used by DrawTextString().
                            if ( hu_replacement_len > 0 && srcline->letter_spacing )
                                word->width += hu_replacement_len * srcline->letter_spacing;

                            // alignLine() later reserves justification letter spacing as
                            // distinct_glyphs * added_letter_spacing.  Include the synthetic
                            // glyphs so its width accounting matches the rendered string.
                            if ( hu_replacement_len > 0 && word->distinct_glyphs > 0 )
                                word->distinct_glyphs += hu_replacement_len;

                            word->flags |= LTEXT_WORD_HUNGARIAN_HYPH_REPLACE;
                        }
'''

replace_once(cpp, old, new, "account Hungarian synthetic glyph spacing")

print("Kobo build #9 Hungarian synthetic glyph spacing patch applied successfully")
