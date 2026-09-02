from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Build 5: preserve all Build 3/4 behaviour, but prevent CREngine's optical
# hyphen hanging from being applied to Hungarian synthetic replacement breaks.
#
# Normal KOReader hyphenation still keeps its existing hanging-punctuation
# behaviour. Only lines marked with LCHAR_HUNGARIAN_HYPH_REPLACE are excluded,
# because these lines already contain one or two synthetic characters restored
# before the hyphen (asszony -> asz-szony, gallyat -> galy-lyat, etc.).
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")

old = '''                                if ( ends_with_hyphen ) {
                                    int percent = srcline->lang_cfg->getHyphenHangingPercent();
                                    if ( percent ) {
                                        shift_w = font->getHyphenWidth() * percent / 100;
                                        if ( shift_w == 0 ) // Force at least 1px if division rounded it to 0
                                            shift_w = 1;
                                    }
'''

new = '''                                if ( ends_with_hyphen ) {
                                    // Extended Hungarian hyphenation can synthesize one or two
                                    // characters immediately before the rendered hyphen. Keep the
                                    // whole synthetic form inside the normal text measure instead
                                    // of additionally hanging the hyphen into the right margin.
                                    // Ordinary KOReader hyphenation keeps its existing optical
                                    // hyphen hanging behaviour unchanged.
                                    if ( !(m_flags[lastnonspace] & LCHAR_HUNGARIAN_HYPH_REPLACE) ) {
                                        int percent = srcline->lang_cfg->getHyphenHangingPercent();
                                        if ( percent ) {
                                            shift_w = font->getHyphenWidth() * percent / 100;
                                            if ( shift_w == 0 ) // Force at least 1px if division rounded it to 0
                                                shift_w = 1;
                                        }
                                    }
'''

replace_once(cpp, old, new, "disable hyphen hanging for Hungarian replacement breaks")

print("Hungarian Kobo build 5 patch applied successfully")
