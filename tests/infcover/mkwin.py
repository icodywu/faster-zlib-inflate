"""A fixed-code stream of 258-byte matches whose first match in each 600-byte inflate() call reaches into the
window in a chosen way (window 2^12): wrapped and split, wrapped, contiguous and split, contiguous."""
import zlib
import mkdeflate as m

OUT, W, FAST_END = 600, 4096, 600 - 265


def build(ncalls=24):
    syms = [("lit", c) for c in b"abcdefghijklmnopqrstuvwxyz"]
    pos = 26
    cases = ["wrap_split", "wrap", "contig_split", "contig"]
    hit = {c: 0 for c in cases}
    k = 0
    while pos < ncalls * OUT:
        S = (pos // OUT) * OUT
        r = pos - S
        first = r < FAST_END and (pos == S or (pos - 258) < S)   # first symbol starting in this call
        d = 3 if pos % 2 else 300
        if first and S >= OUT:
            wnext = S % W if S >= W else S
            whave = min(S, W)
            want = cases[k % 4]; k += 1
            if want == "wrap_split" and wnext and wnext + 100 <= whave:
                op = wnext + 100
            elif want == "wrap" and wnext and wnext + 300 <= whave:
                op = wnext + 300
            elif want == "contig_split" and wnext >= 100:
                op = 100
            elif want == "contig" and wnext >= 300:
                op = 300
            else:
                op = None
            if op is not None and op + r <= pos:
                d = op + r
                hit[want] += 1
        d = min(d, pos)
        syms.append(("match", 258, d))
        pos += 258
    syms += [("lit", c) for c in b"end"] + [("eob",)]
    return syms, hit


if __name__ == "__main__":
    syms, hit = build()
    s = m.stream([("fixed", syms)])
    assert zlib.decompress(s, -12) == m.expand(syms)
    print(hit, len(s), "bytes,", len(m.expand(syms)), "out")
    print(m.hexs(s))
