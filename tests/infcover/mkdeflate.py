"""Hand-made raw deflate streams for test/infcover.c, as hex in its style ("e5 e0 81 ...").

A block is ("fixed", symbols) or ("dynamic", litlen_lengths, dist_lengths, symbols); symbols are ("lit", byte),
("match", length, distance), ("eob",), ("sym", n) for a raw literal/length symbol, ("dsym", n) for a raw distance
symbol after a length symbol. mkcover.py checks every valid stream with Python's zlib.
"""
LBASE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195,
         227, 258]
LEXT = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0]
DBASE = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073,
         4097, 6145, 8193, 12289, 16385, 24577]
DEXT = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]
ORDER = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]


class Bits:
    def __init__(self):
        self.out, self.acc, self.n = bytearray(), 0, 0

    def put(self, v, n):                      # n bits of v, least significant first
        self.acc |= (v & ((1 << n) - 1)) << self.n
        self.n += n
        while self.n >= 8:
            self.out.append(self.acc & 255); self.acc >>= 8; self.n -= 8

    def huff(self, code, n):                  # a Huffman code, most significant bit first
        for i in range(n - 1, -1, -1):
            self.put((code >> i) & 1, 1)

    def flush(self):
        if self.n:
            self.out.append(self.acc & 255); self.acc, self.n = 0, 0
        return bytes(self.out)


def canonical(lengths):
    """codes for a list of code lengths (0: unused), RFC 1951 3.2.2"""
    mx = max(lengths) if lengths else 0
    count = [0] * (mx + 2)
    for l in lengths:
        if l: count[l] += 1
    code, nxt = 0, [0] * (mx + 2)
    for b in range(1, mx + 1):
        code = (code + count[b - 1]) << 1 if b > 1 else 0
        nxt[b] = code
    codes = [0] * len(lengths)
    for s, l in enumerate(lengths):
        if l:
            codes[s] = nxt[l]; nxt[l] += 1
    return codes


def kraft(lengths):
    return sum(2.0 ** -l for l in lengths if l)


def len_sym(length):
    if length == 258: return 285, 0, 0
    for i in range(28, -1, -1):
        if LBASE[i] <= length and i < 28:
            return 257 + i, length - LBASE[i], LEXT[i]
    raise ValueError(length)


def dist_sym(d):
    for i in range(29, -1, -1):
        if DBASE[i] <= d:
            return i, d - DBASE[i], DEXT[i]
    raise ValueError(d)


def fixed_lengths():
    ll = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
    return ll, [5] * 32


def write_symbols(bw, syms, ll, dl):
    lc, dc = canonical(ll), canonical(dl)
    for s in syms:
        if s[0] == "lit":
            bw.huff(lc[s[1]], ll[s[1]])
        elif s[0] == "eob":
            bw.huff(lc[256], ll[256])
        elif s[0] == "sym":
            bw.huff(lc[s[1]], ll[s[1]])
        elif s[0] == "dsym":
            bw.huff(dc[s[1]], dl[s[1]])
        else:
            _, length, d = s
            sym, e, eb = len_sym(length)
            bw.huff(lc[sym], ll[sym]); bw.put(e, eb)
            ds, e, eb = dist_sym(d)
            bw.huff(dc[ds], dl[ds]); bw.put(e, eb)


def write_dynamic_header(bw, ll, dl):
    nlen = max(257, max(i for i, l in enumerate(ll) if l) + 1)
    ndist = max(1, max([i for i, l in enumerate(dl) if l] or [0]) + 1)
    lens = list(ll[:nlen]) + list(dl[:ndist])
    seq = []                                         # (code length symbol, extra value, extra bits)
    i = 0
    while i < len(lens):                             # zero runs as 17 (3-10) and 18 (11-138)
        if lens[i] == 0:
            j = i
            while j < len(lens) and lens[j] == 0 and j - i < 138: j += 1
            run = j - i
            if run >= 11: seq.append((18, run - 11, 7)); i = j; continue
            if run >= 3: seq.append((17, run - 3, 3)); i = j; continue
        seq.append((lens[i], 0, 0)); i += 1
    used = sorted(set(s for s, _, _ in seq))
    k = 1
    while (1 << k) < len(used): k += 1               # a complete code: lengths k and k-1
    short = (1 << k) - len(used)                     # symbols that get k-1 bits
    cl = [0] * 19
    for i, s in enumerate(used):
        cl[s] = k - 1 if i < short else k
    if len(used) == 1: cl[used[0]] = 1               # a single symbol: one bit (incomplete, allowed? no) -> pad
    assert len(used) > 1 and abs(kraft(cl) - 1) < 1e-12, (used, cl)
    nclen = max(i for i, s in enumerate(ORDER) if cl[s]) + 1
    nclen = max(nclen, 4)
    bw.put(nlen - 257, 5); bw.put(ndist - 1, 5); bw.put(nclen - 4, 4)
    for i in range(nclen):
        bw.put(cl[ORDER[i]], 3)
    cc = canonical(cl)
    for s, e, eb in seq:
        bw.huff(cc[s], cl[s]); bw.put(e, eb)


def stream(blocks):
    bw = Bits()
    for i, b in enumerate(blocks):
        last = 1 if i == len(blocks) - 1 else 0
        if b[0] == "fixed":
            bw.put(last, 1); bw.put(1, 2)
            ll, dl = fixed_lengths()
            write_symbols(bw, b[1], ll, dl)
        else:
            _, ll, dl, syms = b
            bw.put(last, 1); bw.put(2, 2)
            write_dynamic_header(bw, ll, dl)
            write_symbols(bw, syms, ll, dl)
    return bw.flush()


def hexs(data):
    return " ".join("%x" % b for b in data)


def expand(syms, prefix=b""):
    out = bytearray(prefix)
    for s in syms:
        if s[0] == "lit": out.append(s[1])
        elif s[0] == "match":
            _, length, d = s
            assert d <= len(out), ("distance too far", d, len(out))
            for _ in range(length): out.append(out[-d])
    return bytes(out[len(prefix):])


if __name__ == "__main__":
    print(hexs(stream([("fixed", [("lit", 97), ("match", 5, 1), ("eob",)])])))
