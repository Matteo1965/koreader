from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Kobo build #12: discard the failed synthetic-spacing experiment from #11.
# Start from the Build-4 path and measure the *actual synthetic left fragment*
# that will be rendered at a Hungarian replacement break.
#
# Previous builds started from the already-measured original prefix and added an
# estimated replacement delta.  That can diverge from HarfBuzz/FreeType shaping
# because inserting the restored z/y/s characters can reshape the whole prefix.
# Here we build exactly the same prefix as the draw path (original prefix + the
# restored Hungarian character(s)) and run it through LVFont::measureText() with
# the same language configuration and source letter spacing.
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")

old_helper = '''static int huReplacementWidth( LVFont * font, const lChar32 * text, int len, int break_after ) {
    lChar32 replacement[2];
    int replacement_len = huHyphenReplacement(text, len, break_after, replacement);
    if ( replacement_len <= 0 )
        return 0;

    // Measure the actual shaped prefix before and after adding the synthetic
    // Hungarian replacement. This keeps line fitting/justification in sync with
    // the text that DrawTextString() will really render.
    lString32 shaped_prefix;
    shaped_prefix.append(text, break_after + 1);
    int base_width = (int)font->getTextWidth(shaped_prefix.c_str(), shaped_prefix.length());
    for ( int i=0; i<replacement_len; i++ )
        shaped_prefix << replacement[i];
    int expanded_width = (int)font->getTextWidth(shaped_prefix.c_str(), shaped_prefix.length());
    return expanded_width > base_width ? expanded_width - base_width : 0;
}
'''

new_helper = '''static int huRenderedPrefixWidth( LVFont * font, TextLangCfg * lang_cfg, int letter_spacing,
                                  const lChar32 * text, int len, int break_after ) {
    lChar32 replacement[2];
    int replacement_len = huHyphenReplacement(text, len, break_after, replacement);
    if ( replacement_len <= 0 )
        return -1;

    lString32 rendered_prefix;
    rendered_prefix.append(text, break_after + 1);
    for ( int i=0; i<replacement_len; i++ )
        rendered_prefix << replacement[i];

    // Hungarian words are already limited to MAX_WORD_SIZE by the formatter;
    // keep a little extra room for the restored digraph/trigraph characters.
    lUInt16 widths[128];
    lUInt8 flags[128];
    int rendered_len = rendered_prefix.length();
    if ( rendered_len <= 0 || rendered_len >= 128 )
        return -1;

    int measured = font->measureText(
            rendered_prefix.c_str(), rendered_len,
            widths, flags,
            0x7FFF,
            '?',
            lang_cfg,
            letter_spacing,
            false,
            0 );
    if ( measured != rendered_len )
        return -1;
    return widths[rendered_len-1];
}
'''
replace_once(cpp, old_helper, new_helper, "replace delta width with exact rendered-prefix measurement")

old_candidate = '''                                int candidate_width = widths[i] + _hyphen_width;
                                if ( (m_flags[wstart+i] & LCHAR_HUNGARIAN_HYPH_REPLACE) && hyphen_font )
                                    candidate_width += huReplacementWidth(hyphen_font, m_text+wstart, len, i);
'''

new_candidate = '''                                int candidate_width = widths[i] + _hyphen_width;
                                if ( (m_flags[wstart+i] & LCHAR_HUNGARIAN_HYPH_REPLACE) && hyphen_font ) {
                                    src_text_fragment_t * hu_src = m_srcs[wstart+i];
                                    int rendered_prefix_width = huRenderedPrefixWidth(
                                            hyphen_font,
                                            hu_src ? hu_src->lang_cfg : NULL,
                                            hu_src ? hu_src->letter_spacing : 0,
                                            m_text+wstart, len, i);
                                    if ( rendered_prefix_width >= 0 )
                                        candidate_width = rendered_prefix_width + _hyphen_width;
                                }
'''
replace_once(cpp, old_candidate, new_candidate, "use exact rendered prefix while choosing line break")

old_addline = '''                        if ( m_flags[i-1] & LCHAR_HUNGARIAN_HYPH_REPLACE ) {
                            word->width += huReplacementWidth(font, m_text+wstart, end-wstart, i-1-wstart);
                            word->flags |= LTEXT_WORD_HUNGARIAN_HYPH_REPLACE;
                        }
'''

new_addline = '''                        if ( m_flags[i-1] & LCHAR_HUNGARIAN_HYPH_REPLACE ) {
                            int rendered_prefix_width = huRenderedPrefixWidth(
                                    font, srcline->lang_cfg, srcline->letter_spacing,
                                    m_text+wstart, end-wstart, i-1-wstart);
                            if ( rendered_prefix_width >= 0 ) {
                                // Replace the old source-prefix width outright: this is the
                                // exact synthetic fragment that DrawTextString() will render.
                                word->width = rendered_prefix_width;
                            }
                            word->flags |= LTEXT_WORD_HUNGARIAN_HYPH_REPLACE;
                        }
'''
replace_once(cpp, old_addline, new_addline, "use exact rendered prefix in final word width")

print("Kobo build #12 exact Hungarian rendered-prefix measurement applied successfully")
