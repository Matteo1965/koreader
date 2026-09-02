from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Kobo build #13: fix the actual root cause of the right-margin overflow.
#
# Build #12 measures the synthetic Hungarian prefix exactly, but addLine() still
# passed only the already-truncated current-line fragment (m_text+wstart,
# end-wstart) into huRenderedPrefixWidth(). At a line-end break this fragment no
# longer contains the look-ahead characters required by huHyphenReplacement(),
# so the replacement width could not be detected and the helper returned -1.
#
# The draw path already uses the full original source-node remainder. Mirror that
# same context here so layout and drawing call huHyphenReplacement() with identical
# text and break position semantics.
cpp = Path("base/thirdparty/kpvcrlib/crengine/crengine/src/lvtextfm.cpp")

old = '''                        if ( m_flags[i-1] & LCHAR_HUNGARIAN_HYPH_REPLACE ) {
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

new = '''                        if ( m_flags[i-1] & LCHAR_HUNGARIAN_HYPH_REPLACE ) {
                            // Use the same full source context as DrawTextString().  The
                            // replacement detector needs the characters after the break
                            // (e.g. the second s + z in asszony) to identify the compact
                            // doubled Hungarian digraph/trigraph.  end-wstart stops exactly
                            // at the line break and therefore cannot provide that look-ahead.
                            const lChar32 * hu_source = srcline->t.text + word->t.start;
                            int hu_source_len = srcline->t.len - word->t.start;
                            int rendered_prefix_width = huRenderedPrefixWidth(
                                    font, srcline->lang_cfg, srcline->letter_spacing,
                                    hu_source, hu_source_len, word->t.len-1);
                            if ( rendered_prefix_width >= 0 ) {
                                // Replace the old source-prefix width outright: this is the
                                // exact synthetic fragment that DrawTextString() will render.
                                word->width = rendered_prefix_width;
                            }
                            word->flags |= LTEXT_WORD_HUNGARIAN_HYPH_REPLACE;
                        }
'''

replace_once(cpp, old, new, "use full source context for Hungarian replacement width")

print("Kobo build #13 Hungarian full-context width fix applied successfully")
