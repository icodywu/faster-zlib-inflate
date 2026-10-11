"""Streams for infcover's fast-loop cases (inffast.c with a 64-bit bit buffer and 10/8-bit root tables)."""
import zlib
import mkdeflate as m
import mkwin

lit = lambda s: [("lit", ord(c)) for c in s]

# 1. long codes: literal/length codes of 1-15 bits and distance codes of 1-15 bits, so that codes longer than the
#    root tables (10 and 8 bits) take second-level tables (a literal among them); literal runs, a run of one byte,
#    distances 2-7 (with lengths not a multiple of three) and 8 or more
ll = [0] * 286
for c, l in zip("acdefghi", (1, 3, 4, 5, 6, 7, 8, 9)):
    ll[ord(c)] = l
for s, l in ((256, 2), (257, 10), (ord("j"), 11), (260, 12), (265, 13), (269, 14), (285, 15), (ord("b"), 15)):
    ll[s] = l
dl = [0] * 30
for s, l in ((0, 15), (3, 14), (6, 13), (9, 12), (12, 11), (15, 10), (1, 1), (2, 2), (4, 3), (5, 4), (7, 5),
             (8, 6), (10, 7), (11, 8), (13, 9), (14, 15)):
    dl[s] = l
assert abs(m.kraft(ll) - 1) < 1e-12 and abs(m.kraft(dl) - 1) < 1e-12


def long_syms(tail):
    return lit("abcdefghij") + [("match", 3, 1), ("match", 6, 4), ("match", 11, 4), ("match", 19, 2),
                                ("match", 11, 9), ("match", 19, 25), ("match", 258, 1), ("match", 258, 65)] +         lit("jab" + tail) + [("match", 3, 193), ("eob",)]


def long_stream(tail=""):
    s = m.stream([("dynamic", ll, dl, long_syms(tail))])
    assert zlib.decompress(s, -15) == m.expand(long_syms(tail))
    return s


long_codes = long_stream("aaaa")     # puts the last distance code where inflateBack() pulls a byte
long_variants = [long_stream("a" * k) for k in range(8)]     # the last match at eight bit offsets

# 2. an end of block in the fast loop: a fixed block followed by enough of a second block
eob2 = m.stream([("fixed", lit("abc") + [("eob",)]), ("fixed", lit("defghijklmnopqrstuvwxyzabcdefghijklmnop") + [("eob",)])])
assert zlib.decompress(eob2, -15) == b"abc" + b"defghijklmnopqrstuvwxyzabcdefghijklmnop"

# 3. window copies: 600 bytes of output a call, window 2^12 (wrapped or contiguous, split or not) and 2^9 (every
#    update fills the window, so its write index is zero)
w12, hits = mkwin.build()
win12 = m.stream([("fixed", w12)])
w9 = lit("abcdefghijklmnopqrstuvwxyz") + [("match", 258, 26), ("match", 258, 1)]
for d in (300, 500, 100, 3, 512, 260, 2, 400, 37, 450, 8, 333):
    w9.append(("match", 258, d))
w9 += lit("end") + [("eob",)]
win9 = m.stream([("fixed", w9)])
assert zlib.decompress(win9, -9) == m.expand(w9)

# 4. errors in the fast loop, with enough input after them: a distance beyond the output so far, length symbol 286,
#    distance code 30
pad, after = lit("abcdefghijklmnop"), lit("abcdefghijklmnopqrstuvwxyzabcdef")
far = m.stream([("fixed", pad + [("match", 10, 100)] + after + [("eob",)])])
bad_len = m.stream([("fixed", pad + [("sym", 286)] + after + [("eob",)])])
bad_dist = m.stream([("fixed", pad + [("sym", 257), ("dsym", 30)] + after + [("eob",)])])

if __name__ == "__main__":
    for name, s in (("long_codes", long_codes), ("eob2", eob2), ("win12", win12), ("win9", win9), ("far", far),
                    ("bad_len", bad_len), ("bad_dist", bad_dist)):
        print("%-10s %4d bytes: %s" % (name, len(s), m.hexs(s)[:100]))
    print("window cases", hits)
