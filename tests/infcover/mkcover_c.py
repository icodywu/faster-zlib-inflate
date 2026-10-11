"""Print the cover_fast64() function of test/infcover.c (in the patch) from mkcover.py's streams.

usage: cd tests/infcover && python3 mkcover_c.py
"""
import mkcover as c, mkdeflate as m

def cstr(s, indent):
    """hex as C string literal pieces, lines of at most 79 columns"""
    words = m.hexs(s).split()
    lines, cur = [], ""
    for w in words:
        nxt = (cur + " " + w) if cur else w
        if len(indent) + len(nxt) + 3 > 79:
            lines.append(cur); cur = w
        else:
            cur = nxt
    lines.append(cur)
    out = []
    for i, l in enumerate(lines):
        piece = '"' + l + (' ' if i < len(lines) - 1 else '') + '"'
        out.append(indent + piece)
    return "\n".join(out)

i8 = " " * 8
code = """/* cover the fast loop of inffast.c, which needs sixteen bytes of input and
   room for 265 bytes of output: second-level codes with 10- and 8-bit root
   tables, literal runs, copies at distances 1, 2..7 and 8 or more, window
   copies (wrapped, contiguous, and with the write index at zero), and its
   errors */
local void cover_fast64(void)
{
    char *longcodes =
%s;
    char *win12 =
%s;
    char *win9 =
%s;

    inf(longcodes, "fast long codes", 0, -15, 1000, Z_STREAM_END);
    inf(%s,
        "fast end of block", 0, -15, 300, Z_STREAM_END);
    inf(longcodes, "long codes in small pieces", 3, -15, 100, Z_OK);
    try(longcodes, "long codes", 0);
    inf(win12, "fast window copies", 0, -12, 600, Z_OK);
    inf(win9, "fast window write index zero", 0, -9, 600, Z_OK);
    inf(%s,
        "fast too far back", 0, -15, 300, Z_DATA_ERROR);
    inf(%s,
        "fast invalid literal/length code", 0, -15, 300, Z_DATA_ERROR);
    inf(%s,
        "fast invalid distance code", 0, -15, 300, Z_DATA_ERROR);
}
""" % (cstr(c.long_codes, i8), cstr(c.win12, i8), cstr(c.win9, i8),
       cstr(c.eob2, i8).lstrip(), cstr(c.far, i8).lstrip(), cstr(c.bad_len, i8).lstrip(), cstr(c.bad_dist, i8).lstrip())
print(code)
