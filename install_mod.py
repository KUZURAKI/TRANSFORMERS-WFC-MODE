#!/usr/bin/env python3
"""
TRANSFORMERS: War for Cybertron - "All Characters" campaign mod (patcher)

What it does (applied to YOUR copy of the game, nothing from the game is redistributed):
  1. Coalesced.ini
       - every campaign chapter (A1-A5 / D1-D5) offers every campaign-capable character of its faction
       - all "LockedCharacter=true" are set to false
  2. TransGame.xxx
       - the in-level character list = chapter's own 3 characters + the rest of the faction
         (the 3 originals still become AI buddies, a different pick plays as an extra 4th character)
       - the campaign lobby no longer wipes your character when the chapter loads, so the in-level
         character-select screen is skipped and the character picked in the lobby is used.
  3. PCTOC.txt  - size / md5 of the changed files

Originals are backed up next to the files as "*.original" the first time the script runs.
Usage:
    python install_mod.py "D:\\Games\\TRANSFORMERS - War for Cybertron"
    python install_mod.py "<game dir>" --restore
"""
import hashlib, os, re, shutil, struct, sys

# ----------------------------------------------------------------------------- configuration
AUTOBOTS = ['Optimus Prime', 'Optimus', 'Bumblebee', 'Ironhide', 'Ratchet', 'Sideswipe', 'Warpath', 'Jetfire', 'AirRaid']
DECEPTICONS = ['Megatron', 'Starscream', 'Soundwave', 'Breakdown', 'Brawl', 'Barricade', 'Skywarp', 'Thundercracker']

# ----------------------------------------------------------------------------- Coalesced.ini codec
KEY = b'vvp;aseiurwefsdcfszdcvnas;dwepo2345098]qw]{}p2039458pseasdfzc'
K = len(KEY)


def _xor(data, r):
    k = KEY[r:] + KEY[:r]
    return bytes(b ^ k[j % K] for j, b in enumerate(data))


def coalesced_unpack(d):
    hdr, = struct.unpack_from('<i', d, 0)
    pos, sigma, out = 4, 0, []
    while pos < len(d):
        l, = struct.unpack_from('<i', d, pos)
        name = d[pos + 4:pos + 4 + l]
        pos += 4 + l
        s, = struct.unpack_from('<i', d, pos)
        cont = d[pos + 4:pos + 4 + s]
        pos += 4 + s
        rn = (sigma + 23) % K
        rc = (rn + l - 1) % K
        out.append([_xor(name, rn), _xor(cont, rc)])
        sigma += l + s - 2
    return hdr, out


def coalesced_pack(hdr, files):
    out = bytearray(struct.pack('<i', hdr))
    sigma = 0
    for n, c in files:
        l, s = len(n), len(c)
        rn = (sigma + 23) % K
        rc = (rn + l - 1) % K
        out += struct.pack('<i', l) + _xor(n, rn) + struct.pack('<i', s) + _xor(c, rc)
        sigma += l + s - 2
    return bytes(out)


def patch_coalesced(path_in, path_out):
    d = open(path_in, 'rb').read()
    hdr, files = coalesced_unpack(d)
    assert coalesced_pack(hdr, files) == d, 'Coalesced.ini round-trip failed (unsupported game version?)'

    def find(name):
        for f in files:
            if f[0].decode('latin1').split('\\')[-1].startswith(name):
                return f
        raise KeyError(name)

    # --- TransLevels.ini
    lv = find('TransLevels.ini')
    text = lv[1].decode('latin1')
    seps = re.findall(r'(?:\r?\n){2,}', text)
    secs = re.split(r'(?:\r?\n){2,}', text)
    patched = 0
    for k, sec in enumerate(secs):
        if 'CampaignCharacters=' in sec and 'SOLO' in sec:
            fac = re.search(r'Faction=(\d)', sec)
            if not fac:
                continue
            full = AUTOBOTS if fac.group(1) == '0' else DECEPTICONS
            lines = sec.split('\n')
            orig = [l.strip().split('=', 1)[1] for l in lines if l.strip().startswith('CampaignCharacters=')]
            order = orig + [c for c in full if c not in orig]
            new, done = [], False
            for l in lines:
                if l.strip().startswith('CampaignCharacters='):
                    if not done:
                        eol = '\r' if l.endswith('\r') else ''
                        new += ['CampaignCharacters=%s%s' % (c, eol) for c in order]
                        done = True
                else:
                    new.append(l)
            secs[k] = '\n'.join(new)
            patched += 1
    res = secs[0]
    for s, sec in zip(seps, secs[1:]):
        res += s + sec
    lv[1] = res.encode('latin1')
    # --- TransCustomization.ini
    cu = find('TransCustomization.ini')
    t, n = re.subn(r'LockedCharacter=true', 'LockedCharacter=false', cu[1].decode('latin1'))
    cu[1] = t.encode('latin1')
    out = coalesced_pack(hdr, files)
    open(path_out, 'wb').write(out)
    print('  Coalesced.ini: %d campaign maps patched, %d characters unlocked' % (patched, n))
    return out


# ----------------------------------------------------------------------------- minimal UE3 package reader
class Pkg:
    def __init__(s, data):
        s.d = d = data
        assert d[:4] == b'\xc1\x83\x2a\x9e'
        l, = struct.unpack_from('<i', d, 16)
        o = 20 + l
        (s.flags, s.nc, s.no, s.ec, s.eo, s.ic, s.io) = struct.unpack_from('<Iiiiiii', d, o)
        s.names, p = [], s.no
        for _ in range(s.nc):
            l, = struct.unpack_from('<i', d, p)
            if l > 0:
                s.names.append(d[p + 4:p + 3 + l].decode('latin1'))
                p += 4 + l + 8
            else:
                s.names.append(d[p + 4:p + 2 + (-l) * 2].decode('utf-16le', 'replace'))
                p += 4 + (-l) * 2 + 8
        s.imports = []
        for i in range(s.ic):
            pk, _, cn, _, outer, on, onn = struct.unpack_from('<iiiiiii', d, s.io + 28 * i)
            s.imports.append(dict(name=s.names[on], outer=outer, cls=s.names[cn]))
        s.exports = []
        p = s.eo
        for i in range(s.ec):
            if not s._valid(p):
                q = p
                while q < len(d) and not s._valid(q):
                    q += 1
                p = q
            cls, sup, outer, on, onn, arch = struct.unpack_from('<6i', d, p)
            flags, size, off, ef = struct.unpack_from('<QiiI', d, p + 24)
            q = p + 44
            cnt = d[q]
            q += 1
            if cnt == 1 and ef & 1 and s._valid(q + 28):
                q += 28
            elif cnt != 0:
                for k in range(200):
                    if s._valid(q + k):
                        q += k
                        break
            s.exports.append(dict(idx=i + 1, cls=cls, outer=outer, name=s.names[on], size=size, off=off, hdr=p))
            p = q

    def _valid(s, p):
        d = s.d
        if p + 45 > len(d):
            return False
        cls, sup, outer, on, onn, arch = struct.unpack_from('<6i', d, p)
        size, off = struct.unpack_from('<ii', d, p + 32)
        return (-s.ic <= cls <= s.ec and -s.ic <= sup <= s.ec and -s.ic <= outer <= s.ec and 0 <= on < s.nc
                and 0 <= size < len(d) and 0 <= off <= len(d) and -s.ic <= arch <= s.ec)

    def path(s, ref, depth=0):
        if ref == 0 or depth > 40:
            return ''
        if ref < 0:
            im = s.imports[-ref - 1]
            o = s.path(im['outer'], depth + 1)
            return (o + '.' if o else '') + im['name']
        e = s.exports[ref - 1]
        o = s.path(e['outer'], depth + 1)
        return (o + '.' if o else '') + e['name']

    def cls_name(s, e):
        r = e['cls']
        if r == 0:
            return 'None'
        return s.imports[-r - 1]['name'] if r < 0 else s.exports[r - 1]['name']

    def find(s, suffix, cls=None):
        r = [e for e in s.exports if s.path(e['idx']).endswith(suffix) and (cls is None or s.cls_name(e) == cls)]
        assert len(r) == 1, 'cannot uniquely locate %s (%d hits) - unsupported game version?' % (suffix, len(r))
        return r[0]


def script_of(pk, e):
    p = e['off'] + 40
    n, = struct.unpack_from('<i', pk.d, p)
    assert 0 < n < e['size'] and pk.d[p + 4 + n - 1] == 0x53, 'unexpected function layout'
    return p + 4, n


# ----------------------------------------------------------------------------- TransGame.xxx patches
def _sconst(s):
    return b'\x1f' + s.encode('latin1') + b'\x00'


def _add_if_missing(name, base, pc):
    val = _sconst(name)
    find = b'\x46\x00' + pc + struct.pack('<H', len(val)) + val
    cond = b'\x9a' + find + b'\x1d\xff\xff\xff\xff' + b'\x16'
    add = b'\x55\x00' + pc + struct.pack('<H', len(val)) + val
    size = 3 + len(cond) + len(add)
    return b'\x07' + struct.pack('<H', base + size) + cond + add


def _block(names, base, pc):
    out = b''
    for n in names:
        out += _add_if_missing(n, base + len(out), pc)
    return out


def patch_transgame(path_in, path_out):
    pk = Pkg(open(path_in, 'rb').read())
    d = bytearray(pk.d)

    # (A) in-level list = chapter's characters + every other character of the faction
    fn = pk.find('TnWorldInfo.GetPlayableIconicCharacterNames', 'Function')
    fac = pk.find('TnCoopInfo.Faction')
    dec = [e for e in pk.exports if e['name'] == 'TnFactionTeamDecepticons' and pk.cls_name(e) in ('None', 'Class')]
    assert len(dec) == 1
    p0, n = script_of(pk, fn)
    orig = bytes(d[p0:p0 + n])
    assert n == 75 and orig[0] == 0x0F
    PC, COOP, RV = orig[2:6], orig[8:12], orig[-5:-1]
    head = orig[:25]
    cond = b'\x72' + b'\x19\x01' + COOP + struct.pack('<H', 5) + b'\x04\x01' + struct.pack('<i', fac['idx']) \
        + b'\x20' + struct.pack('<i', dec[0]['idx']) + b'\x16'
    dec_base = len(head) + 3 + len(cond)
    dec_block = _block(DECEPTICONS, dec_base, PC)
    a_base = dec_base + len(dec_block) + 3
    a_block = _block(AUTOBOTS, a_base, PC)
    end_pos = a_base + len(a_block)
    script = (head + b'\x07' + struct.pack('<H', a_base) + cond + dec_block
              + b'\x06' + struct.pack('<H', end_pos) + a_block
              + b'\x04\x00' + PC + b'\x04\x3a' + RV + b'\x53')
    blob_old = bytes(d[fn['off']:fn['off'] + fn['size']])
    new_blob = blob_old[:40] + struct.pack('<i', len(script)) + script + blob_old[44 + n:]
    while len(d) % 4:
        d.append(0)
    new_off = len(d)
    d += new_blob
    struct.pack_into('<ii', d, fn['hdr'] + 32, len(new_blob), new_off)

    # (B) campaign lobby must not wipe the picked character on level load
    fb = pk.find('TnGameLobbyGameCampaign.HandleSeamlessTravelPlayer', 'Function')
    q0, m = script_of(pk, fb)
    s = bytes(d[q0:q0 + m])
    # expected statement: 19 00 <PRI local ref> 0a 00 00 1b <ClearCharacter name 8 bytes> 16   (19 bytes) ending at "04 3a ..."? -> locate by shape
    i = s.find(b'\x19\x00')
    j = i
    # the ClearCharacter call is the last statement before the final return/end: pattern 19 00 ref(4) 0a 00 00 1b name(8) 16
    m_ = re.search(rb'\x19\x00....\x0a\x00\x00\x1b........\x16', s, re.S)
    assert m_ and m_.end() - m_.start() == 19, 'ClearCharacter statement not found - unsupported game version?'
    for k in range(m_.start(), m_.end()):
        d[q0 + k] = 0x0B
    # (C) lobby start: append "?Character=<picked character>" to the level URL.
    #     The level's TnGame.PostLogin -> SelectPieCharacter reads that option and selects the character
    #     itself, which skips the in-level character-select screen.
    fm = pk.find('TnGameReplicationInfoGameLobby.ModifyURL', 'Function')
    m0, mn = script_of(pk, fm)
    ms = bytes(d[m0:m0 + mn])
    assert ms.endswith(b'\x04\x0b\x53'), 'ModifyURL layout changed'
    ins = len(ms) - 3
    assert (b'\x07' + struct.pack('<H', ins)) in ms, 'ModifyURL jump layout changed'
    m_opt = re.search(rb'\x0f\x48(....)\x70\x70\x48\1\x1f\?Checkpoint=\x00\x16', ms, re.S)
    assert m_opt, 'ModifyURL OptionsURL pattern not found'
    opt = m_opt.group(1)
    # references taken from TnGameReplicationInfoGameLobby.DeselectInvalidCharacters (same package)
    dsel = pk.find('TnGameReplicationInfoGameLobby.DeselectInvalidCharacters', 'Function')
    s0, sn = script_of(pk, dsel)
    ss = bytes(d[s0:s0 + sn])
    m_arr = re.search(rb'\x58(\x01....)\x00', ss, re.S)           # I:PRIArray
    m_cast = re.search(rb'\x2e(....)\x00', ss, re.S)               # class TnPlayerReplicationInfo
    m_call = re.search(rb'\x19\x00....\x0a\x00\x00\x1b(........)\x16\x07', ss, re.S)  # GetCharacterName
    assert m_arr and m_cast and m_call, 'DeselectInvalidCharacters layout changed'
    name_expr = (b'\x19\x2e' + m_cast.group(1) + b'\x10\x25' + m_arr.group(1)
                 + b'\x0a\x00\x00\x1b' + m_call.group(1) + b'\x16')
    stmt = (b'\x0f\x48' + opt + b'\x70\x70\x48' + opt + _sconst('?Character=') + b'\x16' + name_expr + b'\x16')
    new_ms = ms[:ins] + stmt + ms[ins:]
    blob_old = bytes(d[fm['off']:fm['off'] + fm['size']])
    new_blob = blob_old[:40] + struct.pack('<i', len(new_ms)) + new_ms + blob_old[44 + mn:]
    while len(d) % 4:
        d.append(0)
    new_off = len(d)
    d += new_blob
    struct.pack_into('<ii', d, fm['hdr'] + 32, len(new_blob), new_off)

    # (D) TnGame.SelectPieCharacter: take the option as-is instead of searching the level's list
    fp = pk.find('TnGame.SelectPieCharacter', 'Function')
    p0_, pn = script_of(pk, fp)
    ps = bytes(d[p0_:p0_ + pn])
    # L:PossibleCharacters = (GetGRI()).GetPlayableIconicCharacterNames()   (30 bytes)
    m_get = re.search(rb'\x0f\x00(....)\x19\x1b........\x16\x0a\x00\x00\x1b........\x16', ps, re.S)
    assert m_get, 'SelectPieCharacter layout changed'
    m_find = re.search(rb'\x46\x00' + re.escape(m_get.group(1)) + rb'\x05\x00\x00(....)', ps, re.S)
    assert m_get and m_find and m_get.end() - m_get.start() == 30, 'SelectPieCharacter layout changed'
    add = b'\x55\x00' + m_get.group(1) + b'\x05\x00\x00' + m_find.group(1)
    patch = add + b'\x0b' * (30 - len(add))
    d[p0_ + m_get.start():p0_ + m_get.end()] = patch

    # (E) ValidateCharacterSelection always accepts (so the picked character is not rejected by the chapter list)
    fv = pk.find('TnGameReplicationInfo.ValidateCharacterSelection', 'Function')
    v0, vn = script_of(pk, fv)
    vs = bytes(d[v0:v0 + vn])
    assert vs[:3] == b'\x07\x0d\x00' and vs[11:13] == b'\x04\x27', 'Validate layout changed'
    d[v0:v0 + 11] = b'\x0b' * 11

    open(path_out, 'wb').write(d)
    print('  TransGame.xxx: list extended, lobby pick carried into the level, in-level select skipped')
    return bytes(d)


# ----------------------------------------------------------------------------- PCTOC
def update_toc(toc_path, entries):
    """entries: {b'CookedPC\\TransGame.xxx': bytes, ...}"""
    lines = open(toc_path, 'rb').read().split(b'\r\n')
    out = []
    for l in lines:
        for key, data in entries.items():
            if (b'\\' + key + b' ') in l:
                parts = l.split(b' ')
                parts[0] = str(len(data)).encode()
                parts[-1] = hashlib.md5(data).hexdigest().encode()
                l = b' '.join(parts)
        out.append(l)
    open(toc_path, 'wb').write(b'\r\n'.join(out))


# ----------------------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    restore = '--restore' in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    game = args[0]
    tg = os.path.join(game, 'TransGame')
    files = {
        'coal': os.path.join(tg, 'Config', 'PC', 'Cooked', 'Coalesced.ini'),
        'game': os.path.join(tg, 'CookedPC', 'TransGame.xxx'),
        'toc': os.path.join(tg, 'PCTOC.txt'),
    }
    for k, p in files.items():
        if not os.path.exists(p):
            sys.exit('not found: ' + p + '\n(pass the game folder that contains Binaries and TransGame)')
    if restore:
        for p in files.values():
            if os.path.exists(p + '.original'):
                shutil.copy2(p + '.original', p)
                print('restored', p)
        return
    for p in files.values():
        if not os.path.exists(p + '.original'):
            shutil.copy2(p, p + '.original')
            print('backup:', p + '.original')
    print('patching...')
    coal = patch_coalesced(files['coal'] + '.original', files['coal'])
    gam = patch_transgame(files['game'] + '.original', files['game'])
    # start from the pristine TOC so repeated runs stay clean
    shutil.copy2(files['toc'] + '.original', files['toc'])
    update_toc(files['toc'], {b'Config\\PC\\Cooked\\Coalesced.ini': coal, b'CookedPC\\TransGame.xxx': gam})
    print('done. To undo: python install_mod.py "<game dir>" --restore')


if __name__ == '__main__':
    main()
