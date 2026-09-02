from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) CREngine: measure the synthetic Hungarian replacement with the same shaped
#    text-width path used by the font engine, instead of summing isolated glyph
#    advances. This fixes right-margin overflow on compact doubled digraph/trigraph
#    hyphenation such as asszony -> asz-szony and gallyat -> galy-lyat.
# -----------------------------------------------------------------------------
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")

replace_once(cpp,
'''static int huReplacementWidth( LVFont * font, const lChar32 * text, int len, int break_after ) {
    lChar32 replacement[2];
    int replacement_len = huHyphenReplacement(text, len, break_after, replacement);
    int width = 0;
    for ( int i=0; i<replacement_len; i++ )
        width += font->getCharWidth(replacement[i]);
    return width;
}
''',
'''static int huReplacementWidth( LVFont * font, const lChar32 * text, int len, int break_after ) {
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
''', "CRE exact Hungarian replacement width")

replace_once(cpp,
'''                                if ( (m_flags[wstart+i] & LCHAR_HUNGARIAN_HYPH_REPLACE) && hyphen_font ) {
                                    const int replacement_width = huReplacementWidth(hyphen_font, m_text+wstart, len, i);
                                    candidate_width += replacement_width;
                                    // Reserve one additional replacement glyph width while choosing
                                    // the line break. Rendering/shaping of the synthetic suffix can
                                    // otherwise exceed the simple getCharWidth() estimate by roughly
                                    // one glyph on Kobo. This affects fitting only, not drawn width.
                                    candidate_width += replacement_width;
                                }
''',
'''                                if ( (m_flags[wstart+i] & LCHAR_HUNGARIAN_HYPH_REPLACE) && hyphen_font )
                                    candidate_width += huReplacementWidth(hyphen_font, m_text+wstart, len, i);
''', "remove build3 replacement-width workaround")


# -----------------------------------------------------------------------------
# 2) KOReader: Hungarian books default to Extended Hungarian hyphenation only
#    when the book has no saved choice yet. Once the user selects any mode, the
#    existing per-book setting is preserved and wins on subsequent opens.
# -----------------------------------------------------------------------------
lua = Path("frontend/apps/reader/modules/readertypography.lua")
text = lua.read_text(encoding="utf-8")
marker = '''    self.book_lang_tag = self:fixLangTag(doc_language)

    local is_known_lang_tag = self.book_lang_tag and LANG_TAG_TO_LANG_NAME[self.book_lang_tag] ~= nil
'''
replacement = '''    self.book_lang_tag = self:fixLangTag(doc_language)

    -- For a Hungarian book with no previously saved choice, make Extended
    -- Hungarian hyphenation the default. Existing per-book choices always win,
    -- including an explicit switch to dictionary/algorithmic/soft-hyphen mode.
    if self.hyphenation and not config:has("hungarian_extended_hyphenation")
            and self.book_lang_tag ~= nil then
        local primary_lang = string.lower(self.book_lang_tag):match("^[^%-%_]+")
        if primary_lang == "hu" or primary_lang == "hun" then
            self.hyph_soft_hyphens_only = false
            self.hyph_force_algorithmic = false
            self.hungarian_extended_hyphenation = true
            self.ui.document:setTextHyphenationSoftHyphensOnly(false)
            self.ui.document:setTextHyphenationForceAlgorithmic(false)
            self.ui.document:setHungarianExtendedHyphenation(true)
        end
    end

    local is_known_lang_tag = self.book_lang_tag and LANG_TAG_TO_LANG_NAME[self.book_lang_tag] ~= nil
'''
if text.count(marker) != 1:
    raise SystemExit(f"Hungarian default-on marker: expected 1 match, found {text.count(marker)}")
lua.write_text(text.replace(marker, replacement, 1), encoding="utf-8")

print("Hungarian Kobo build 4 patches applied successfully")
