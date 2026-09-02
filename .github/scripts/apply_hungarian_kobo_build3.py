from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) UI: make Extended Hungarian hyphenation a real fourth radio mode.
# -----------------------------------------------------------------------------
lua = "frontend/apps/reader/modules/readertypography.lua"
replace_once(lua,
'''    table.insert(hyphenation_submenu, {
        text_func = function()
            return "Magyar elválasztás: " .. (self.hungarian_extended_hyphenation and "Kiterjesztett" or "Alap")
        end,
        callback = function()
            self.hungarian_extended_hyphenation = not self.hungarian_extended_hyphenation
            self.ui.document:setHungarianExtendedHyphenation(self.hungarian_extended_hyphenation)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
        checked_func = function()
            return self.hungarian_extended_hyphenation
        end,
        enabled_func = function()
            return self.hyphenation and self.text_lang_tag ~= nil
                and (self.text_lang_tag == "hu" or self.text_lang_tag == "hun"
                    or self.text_lang_tag:match("^hu[-_]") ~= nil)
        end,
    })
''',
'''    table.insert(hyphenation_submenu, {
        text = _("Extended Hungarian hyphenation"),
        callback = function()
            -- This is a real hyphenation mode, mutually exclusive with the three
            -- standard modes below. Selecting it also selects Hungarian typography
            -- rules so the Hungarian pattern dictionary is always its base.
            self:onSetTypographyLanguage("hu")
            self.hyph_soft_hyphens_only = false
            self.hyph_force_algorithmic = false
            self.hungarian_extended_hyphenation = true
            self.ui.document:setTextHyphenationSoftHyphensOnly(false)
            self.ui.document:setTextHyphenationForceAlgorithmic(false)
            self.ui.document:setHungarianExtendedHyphenation(true)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
        checked_func = function()
            return self.hyphenation and self.hungarian_extended_hyphenation
        end,
        radio = true,
        enabled_func = function()
            return self.hyphenation
        end,
    })
''', "extended Hungarian radio item")

replace_once(lua,
'''        callback = function()
            self.hyph_soft_hyphens_only = false
            self.hyph_force_algorithmic = false
            self.ui.document:setTextHyphenationSoftHyphensOnly(self.hyph_soft_hyphens_only)
            self.ui.document:setTextHyphenationForceAlgorithmic(self.hyph_force_algorithmic)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
        -- no hold_callback
        checked_func = function()
            return self.hyphenation and not self.hyph_soft_hyphens_only
                                    and not self.hyph_force_algorithmic
        end,
''',
'''        callback = function()
            self.hyph_soft_hyphens_only = false
            self.hyph_force_algorithmic = false
            self.hungarian_extended_hyphenation = false
            self.ui.document:setTextHyphenationSoftHyphensOnly(self.hyph_soft_hyphens_only)
            self.ui.document:setTextHyphenationForceAlgorithmic(self.hyph_force_algorithmic)
            self.ui.document:setHungarianExtendedHyphenation(false)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
        -- no hold_callback
        checked_func = function()
            return self.hyphenation and not self.hungarian_extended_hyphenation
                                    and not self.hyph_soft_hyphens_only
                                    and not self.hyph_force_algorithmic
        end,
''', "dictionary mode excludes Hungarian extended")

replace_once(lua,
'''        callback = function()
            self.hyph_force_algorithmic = not self.hyph_force_algorithmic
            self.hyph_soft_hyphens_only = false
            self.ui.document:setTextHyphenationSoftHyphensOnly(self.hyph_soft_hyphens_only)
            self.ui.document:setTextHyphenationForceAlgorithmic(self.hyph_force_algorithmic)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
''',
'''        callback = function()
            self.hyph_force_algorithmic = true
            self.hyph_soft_hyphens_only = false
            self.hungarian_extended_hyphenation = false
            self.ui.document:setTextHyphenationSoftHyphensOnly(self.hyph_soft_hyphens_only)
            self.ui.document:setTextHyphenationForceAlgorithmic(self.hyph_force_algorithmic)
            self.ui.document:setHungarianExtendedHyphenation(false)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
''', "algorithmic mode excludes Hungarian extended")
replace_once(lua,
'''            return self.hyphenation and not self.hyph_soft_hyphens_only and self.hyph_force_algorithmic
''',
'''            return self.hyphenation and not self.hungarian_extended_hyphenation
                                    and not self.hyph_soft_hyphens_only and self.hyph_force_algorithmic
''', "algorithmic radio state")

replace_once(lua,
'''        callback = function()
            self.hyph_soft_hyphens_only = not self.hyph_soft_hyphens_only
            self.hyph_force_algorithmic = false
            self.ui.document:setTextHyphenationSoftHyphensOnly(self.hyph_soft_hyphens_only)
            self.ui.document:setTextHyphenationForceAlgorithmic(self.hyph_force_algorithmic)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
''',
'''        callback = function()
            self.hyph_soft_hyphens_only = true
            self.hyph_force_algorithmic = false
            self.hungarian_extended_hyphenation = false
            self.ui.document:setTextHyphenationSoftHyphensOnly(self.hyph_soft_hyphens_only)
            self.ui.document:setTextHyphenationForceAlgorithmic(self.hyph_force_algorithmic)
            self.ui.document:setHungarianExtendedHyphenation(false)
            self.ui:handleEvent(Event:new("UpdatePos"))
        end,
''', "soft hyphens mode excludes Hungarian extended")
replace_once(lua,
'''            return self.hyphenation and self.hyph_soft_hyphens_only
''',
'''            return self.hyphenation and not self.hungarian_extended_hyphenation
                                    and self.hyph_soft_hyphens_only
''', "soft hyphens radio state")

replace_once(lua,
'''            if not self.hyphenation then
                method = _("disabled")
            elseif self.hyph_soft_hyphens_only then
''',
'''            if not self.hyphenation then
                method = _("disabled")
            elseif self.hungarian_extended_hyphenation then
                method = _("Extended Hungarian hyphenation")
            elseif self.hyph_soft_hyphens_only then
''', "hyphenation menu summary")

replace_once(lua,
'''    if lang_tag then
        self.text_lang_tag = lang_tag
        self.ui.document:setTextMainLang(lang_tag)
''',
'''    if lang_tag then
        self.text_lang_tag = lang_tag
        local primary_lang = string.lower(lang_tag):match("^[^%-%_]+")
        if primary_lang ~= "hu" and primary_lang ~= "hun" and self.hungarian_extended_hyphenation then
            self.hungarian_extended_hyphenation = false
            self.ui.document:setHungarianExtendedHyphenation(false)
        end
        self.ui.document:setTextMainLang(lang_tag)
''', "disable Hungarian extended after language change")

# -----------------------------------------------------------------------------
# 2) CREngine: suppress the reported false extended replacements, prefer an
#    already existing normal pattern break at the same position, and reserve
#    one extra replacement-glyph width during candidate fitting. The latter is
#    deliberately conservative for this test build and prevents the inserted
#    glyph from pushing the rendered line beyond the right margin.
# -----------------------------------------------------------------------------
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")
text = cpp.read_text(encoding="utf-8")
marker = '''static bool huHasVowel( const lChar32 * text, int start, int end ) {
    for ( int i=start; i<end; i++ ) {
        if ( huIsVowel(text[i]) )
            return true;
    }
    return false;
}

'''
false_words = [
    "rosszfiúval", "gyorsszolgálat", "okosszemüveg", "rossztól", "rosszízű",
    "meggyullad", "kisszék", "arccsont", "nyolccsillagos", "színnyomás",
    "cipősszekrény", "meggyón", "rosszban", "vasszeg", "tánccsoport",
    "ideggyógyász", "gallyból",
]
arrays = []
checks = []
for n, word in enumerate(false_words):
    vals = ", ".join(f"0x{ord(ch):04X}" for ch in word)
    arrays.append(f"    static const lChar32 w{n}[] = {{ {vals} }};")
    checks.append(f"    if ( len == {len(word)} && huWordEquals(text, w{n}, {len(word)}) ) return true;")
helper = marker + '''static bool huWordEquals( const lChar32 * text, const lChar32 * word, int len ) {
    for ( int i=0; i<len; i++ ) {
        if ( huAsciiLower(text[i]) != huAsciiLower(word[i]) )
            return false;
    }
    return true;
}

static bool huKnownFalseExtendedWord( const lChar32 * text, int len ) {
''' + "\n".join(arrays) + "\n" + "\n".join(checks) + '''
    return false;
}

'''
if text.count(marker) != 1:
    raise SystemExit("CRE Hungarian helper marker missing")
text = text.replace(marker, helper, 1)

old = '''static bool huAddExtendedHyphenation( const lChar32 * text, int len, lUInt16 * flags,
                                      int left_hyphen_min, int right_hyphen_min ) {
    bool found = false;
    for ( int i=0; i<len; i++ ) {
        lChar32 replacement[2];
        if ( !huHyphenReplacement(text, len, i, replacement) )
            continue;
'''
new = '''static bool huAddExtendedHyphenation( const lChar32 * text, int len, lUInt16 * flags,
                                      int left_hyphen_min, int right_hyphen_min ) {
    // Regression guard for compound/morpheme boundaries reported during Kobo testing.
    // Keep normal Hungarian pattern hyphenation for these words; do not synthesize a
    // doubled-digraph/trigraph replacement inside them.
    if ( huKnownFalseExtendedWord(text, len) )
        return false;
    bool found = false;
    for ( int i=0; i<len; i++ ) {
        lChar32 replacement[2];
        if ( !huHyphenReplacement(text, len, i, replacement) )
            continue;
        // If the Hungarian pattern dictionary already provides a break at this exact
        // position, it wins over the heuristic replacement.
        if ( flags[i] & LCHAR_ALLOW_HYPH_WRAP_AFTER )
            continue;
'''
if text.count(old) != 1:
    raise SystemExit("CRE extended hyphenation loop marker missing")
text = text.replace(old, new, 1)

old = '''                                if ( (m_flags[wstart+i] & LCHAR_HUNGARIAN_HYPH_REPLACE) && hyphen_font )
                                    candidate_width += huReplacementWidth(hyphen_font, m_text+wstart, len, i);
'''
new = '''                                if ( (m_flags[wstart+i] & LCHAR_HUNGARIAN_HYPH_REPLACE) && hyphen_font ) {
                                    const int replacement_width = huReplacementWidth(hyphen_font, m_text+wstart, len, i);
                                    candidate_width += replacement_width;
                                    // Reserve one additional replacement glyph width while choosing
                                    // the line break. Rendering/shaping of the synthetic suffix can
                                    // otherwise exceed the simple getCharWidth() estimate by roughly
                                    // one glyph on Kobo. This affects fitting only, not drawn width.
                                    candidate_width += replacement_width;
                                }
'''
if text.count(old) != 1:
    raise SystemExit("CRE Hungarian replacement candidate width marker missing")
text = text.replace(old, new, 1)
cpp.write_text(text, encoding="utf-8")


# -----------------------------------------------------------------------------
# 3) Localize the new menu entry. English is the msgid/fallback.
# -----------------------------------------------------------------------------
translations = {
    "hu": "Kiterjesztett magyar elválasztás",
    "de": "Erweiterte ungarische Silbentrennung",
    "es": "División de palabras húngara avanzada",
    "it": "Sillabazione ungherese avanzata",
    "fr": "Césure hongroise avancée",
}
for lang, translated in translations.items():
    po = Path("l10n") / lang / "koreader.po"
    if not po.exists():
        raise SystemExit(f"Missing translation file: {po}")
    data = po.read_text(encoding="utf-8")
    if 'msgid "Extended Hungarian hyphenation"' not in data:
        data += f'\n#: frontend/apps/reader/modules/readertypography.lua\nmsgid "Extended Hungarian hyphenation"\nmsgstr "{translated}"\n'
        po.write_text(data, encoding="utf-8")

print("Hungarian Kobo build 3 patches applied successfully")
