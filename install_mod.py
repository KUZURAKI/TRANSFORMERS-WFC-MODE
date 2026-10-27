#!/usr/bin/env python3
"""
TRANSFORMERS: War for Cybertron - "All Characters" campaign mod (patcher)

Applied to YOUR copy of the game; nothing from the game is redistributed.

  1. Coalesced.ini   - every campaign chapter (A1-A5 / D1-D5) offers every campaign-capable character
                       of its faction in the lobby; all "LockedCharacter=true" are set to false.
  2. Chapter maps    - (*_Base_m.xxx) each chapter's TnCoopInfo character list gets a definition for every
                       other character of the faction (a copy of the chapter's own definition with another
                       CharacterName), so the in-level character select accepts them.
  3. DLC\\AllCharacters\\AllCharacters.ini
                     - [Engine.PackagesToFullyLoadForDLC]: when a chapter map loads, the robot definition
                       packages (TR_<Name>_ROBODEF_p) of the added characters are loaded too, so the player
                       can actually spawn as them.
  4. PCTOC.txt       - size / md5 of the changed files.

Notes learned the hard way (see README):
  * UnrealScript in this game is compiled into TWFC.exe - changing bytecode in packages has no effect;
    only data (objects, lists, config) changes work.
  * The DLC packages are not loaded when you use "continue campaign" from the main menu - start the
    chapter through "Chapter select".

Originals are backed up next to the files as "*.original" the first time the script runs.
Usage:
    python install_mod.py "D:\\Games\\TRANSFORMERS - War for Cybertron"
    python install_mod.py "<game dir>" --fps60
    python install_mod.py "<game dir>" --restore
"""
import hashlib, os, re, shutil, struct, sys

AUTOBOTS = ['Optimus Prime', 'Optimus', 'Bumblebee', 'Ironhide', 'Ratchet', 'Sideswipe', 'Warpath', 'Jetfire', 'AirRaid']
DECEPTICONS = ['Megatron', 'Starscream', 'Soundwave', 'Breakdown', 'Brawl', 'Barricade', 'Skywarp', 'Thundercracker']

CHAPTERS = {
    'A1_IAC_Base_m': AUTOBOTS, 'A2_KON_BASE_m': AUTOBOTS, 'A3_COR_Base_m': AUTOBOTS,
    'A4_ORB_Base_m': AUTOBOTS, 'A5_TRY_BASE_m': AUTOBOTS,
    'D1_ORB_Base_m': DECEPTICONS, 'D2_COR_Base_m': DECEPTICONS, 'D3A_IAC_Base_m': DECEPTICONS,
    'D3B_IAC_Base_m': DECEPTICONS, 'D5_OME_BASE_m': DECEPTICONS,
}

ROBODEF_PKG = {
    'Optimus Prime': 'TR_Optimus_ROBODEF_p', 'Optimus': 'TR_Optimus_ROBODEF_p', 'Bumblebee': 'TR_BumbleBee_ROBODEF_p',
    'Ironhide': 'TR_Ironhide_ROBODEF_p', 'Ratchet': 'TR_Ratchet_ROBODEF_p', 'Sideswipe': 'TR_Sideswipe_ROBODEF_p',
    'Warpath': 'TR_Warpath_ROBODEF_p', 'Jetfire': 'TR_Jetfire_ROBODEF_p', 'AirRaid': 'TR_AirRaid_ROBODEF_p',
    'Megatron': 'TR_Megatron_ROBODEF_p', 'Starscream': 'TR_StarScream_ROBODEF_p', 'Soundwave': 'TR_Soundwave_ROBODEF_p',
    'Breakdown': 'TR_Breakdown_ROBODEF_p', 'Brawl': 'TR_Brawl_ROBODEF_p', 'Barricade': 'TR_Barricade_ROBODEF_p',
    'Skywarp': 'TR_Skywarp_ROBODEF_p', 'Thundercracker': 'TR_Thunder_ROBODEF_p',
}

DLC_NAME = 'AllCharacters'

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


def patch_coalesced(path_in, path_out, skip=None):
    skip = {k.lower(): v for k, v in (skip or {}).items()}
    d = open(path_in, 'rb').read()
    hdr, files = coalesced_unpack(d)
    assert coalesced_pack(hdr, files) == d, 'Coalesced.ini round-trip failed (unsupported game version?)'

    def find(name):
        for f in files:
            if f[0].decode('latin1').split('\\')[-1].startswith(name):
                return f
        raise KeyError(name)

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
            head = re.match(r'\s*\[(\S+)', sec)
            full = [c for c in full if c not in skip.get(head.group(1).lower() if head else '', [])]
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
    cu = find('TransCustomization.ini')
    t, n = re.subn(r'LockedCharacter=true', 'LockedCharacter=false', cu[1].decode('latin1'))
    cu[1] = t.encode('latin1')
    out = coalesced_pack(hdr, files)
    open(path_out, 'wb').write(out)
    print('  Coalesced.ini: %d campaign maps patched, %d characters unlocked' % (patched, n))
    return out


class Pkg:
    def __init__(s, data):
        s.d = d = data
        assert d[:4] == b'\xc1\x83\x2a\x9e', 'not an Unreal package'
        l, = struct.unpack_from('<i', d, 16)
        s.so = 20 + l
        (s.flags, s.nc, s.no, s.ec, s.eo, s.ic, s.io, s.dep) = struct.unpack_from('<Iiiiiiii', d, s.so)
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
            s.exports.append(dict(idx=i + 1, cls=cls, outer=outer, name=s.names[on], num=onn, size=size, off=off, hdr=p))
            p = q
        s.exp_end = p

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


def _fstr(s):
    b = s.encode('latin1') + b'\x00'
    return struct.pack('<i', len(b)) + b


def _tags(pk, d, p, end):
    out = []
    while p < end:
        ni, _ = struct.unpack_from('<ii', d, p)
        p += 8
        name = pk.names[ni]
        if name == 'None':
            return out
        ti, _ = struct.unpack_from('<ii', d, p)
        p += 8
        typ = pk.names[ti]
        size_pos = p
        size, _ = struct.unpack_from('<ii', d, p)
        p += 8
        if typ in ('StructProperty', 'ByteProperty'):
            p += 8
        if typ == 'BoolProperty':
            out.append((name, typ, size_pos, p, 4))
            p += 4
            continue
        out.append((name, typ, size_pos, p, size))
        p += size
    return out


def _character_name(pk, e):
    t = _tags(pk, pk.d, e['off'] + 4, e['off'] + e['size'])
    s = [x for x in t if x[0] == 'AiCharacterDataResolved'][0]
    c = [x for x in _tags(pk, pk.d, s[3], s[3] + s[4]) if x[0] == 'CharacterName'][0]
    ln, = struct.unpack_from('<i', pk.d, c[3])
    return pk.d[c[3] + 4:c[3] + 3 + ln].decode('latin1')


def _clone_definition(pk, e, new_name):
    blob = bytearray(pk.d[e['off']:e['off'] + e['size']])
    s = [x for x in _tags(pk, blob, 4, len(blob)) if x[0] == 'AiCharacterDataResolved'][0]
    _, _, ssize_pos, svpos, ssize = s
    c = [x for x in _tags(pk, blob, svpos, svpos + ssize) if x[0] == 'CharacterName'][0]
    _, _, csize_pos, cvpos, csize = c
    val = _fstr(new_name)
    out = bytearray(blob[:cvpos]) + val + blob[cvpos + csize:]
    struct.pack_into('<i', out, csize_pos, len(val))
    struct.pack_into('<i', out, ssize_pos, ssize + len(val) - csize)
    struct.pack_into('<i', out, 0, -1)
    return bytes(out)


def patch_chapter_map(path_in, path_out, faction):
    pk = Pkg(open(path_in, 'rb').read())
    d = bytearray(pk.d)
    so, ec, eo, ic, dep = pk.so, pk.ec, pk.eo, pk.ic, pk.dep
    assert pk.exp_end == dep, 'export table end != depends offset (unsupported layout)'

    coop = [e for e in pk.exports if pk.cls_name(e) == 'TnCoopInfo'
            and pk.path(e['idx']).endswith('PersistentLevel.TnWorldInfo.TnCoopInfo')]
    assert len(coop) == 1, 'TnCoopInfo not found'
    coop = coop[0]
    cblob = bytes(d[coop['off']:coop['off'] + coop['size']])
    pc = [x for x in _tags(pk, cblob, 4, len(cblob)) if x[0] == 'PlayableCharacters'][0]
    _, _, psize_pos, pvpos, psize = pc
    cnt, = struct.unpack_from('<i', cblob, pvpos)
    refs = list(struct.unpack_from('<%di' % cnt, cblob, pvpos + 4))
    defs = [pk.exports[r - 1] for r in refs]
    own = [_character_name(pk, e) for e in defs]
    story = {_character_name(pk, e) for e in pk.exports if pk.cls_name(e) == 'TnAiCharacterDefinition'} - set(own)
    extras = [n for n in faction if n not in own and n not in story]
    template = defs[0]

    new_entries, new_refs = b'', []
    entry = bytes(d[template['hdr']:template['hdr'] + 44])
    for k, nme in enumerate(extras):
        blob = _clone_definition(pk, template, nme)
        while len(d) % 4:
            d.append(0)
        off = len(d)
        d += blob
        ent = bytearray(entry)
        struct.pack_into('<i', ent, 16, 900 + k)
        struct.pack_into('<ii', ent, 32, len(blob), off)
        struct.pack_into('<I', ent, 40, 0)
        new_entries += bytes(ent) + b'\x00'
        new_refs.append(ec + 1 + k)

    p = dep
    for _ in range(ec):
        c, = struct.unpack_from('<i', d, p)
        p += 4 + 4 * c
    exp_tab, dep_tab = bytes(d[eo:dep]), bytes(d[dep:p])
    while len(d) % 4:
        d.append(0)
    new_eo = len(d)
    d += exp_tab + new_entries
    new_dep = len(d)
    d += dep_tab + b'\x00\x00\x00\x00' * len(extras)
    new_ec = ec + len(extras)
    struct.pack_into('<ii', d, so + 12, new_ec, new_eo)
    struct.pack_into('<i', d, so + 28, new_dep)
    gp = so + 32 + 16
    gc, = struct.unpack_from('<i', d, gp)
    for g in range(gc):
        ge, = struct.unpack_from('<i', d, gp + 4 + 12 * g)
        if ge == ec:
            struct.pack_into('<i', d, gp + 4 + 12 * g, new_ec)

    allr = refs + new_refs
    arr = struct.pack('<i', len(allr)) + struct.pack('<%di' % len(allr), *allr)
    newc = bytearray(cblob[:pvpos]) + arr + cblob[pvpos + psize:]
    struct.pack_into('<i', newc, psize_pos, len(arr))
    while len(d) % 4:
        d.append(0)
    off = len(d)
    d += newc
    struct.pack_into('<ii', d, new_eo + (coop['hdr'] - eo) + 32, len(newc), off)

    open(path_out, 'wb').write(d)
    return bytes(d), own, extras


def update_toc(toc_path, entries):
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


def write_dlc(game, extras_by_map):
    base = os.path.join(game, 'DLC', DLC_NAME)
    if os.path.isdir(base):
        shutil.rmtree(base)
    os.makedirs(os.path.join(base, 'Config'))
    for m, extras in extras_by_map.items():
        pkgs = []
        for n in extras:
            p = ROBODEF_PKG.get(n)
            if p and p not in pkgs:
                pkgs.append(p)
        if not pkgs:
            continue
        text = '[Engine.PackagesToFullyLoadForDLC]\nMapName=%s\n' % m + ''.join('Package=%s\n' % p for p in pkgs)
        for p in (os.path.join(base, m + '.ini'), os.path.join(base, 'Config', m + '.ini')):
            open(p, 'w', newline='\n').write(text)
    print('  DLC\\%s: one ini per chapter written' % DLC_NAME)


def set_large_address_aware(exe):
    d = bytearray(open(exe, 'rb').read())
    pe, = struct.unpack_from('<I', d, 0x3c)
    assert d[pe:pe + 4] == b'PE\x00\x00'
    ch, = struct.unpack_from('<H', d, pe + 22)
    if ch & 0x20:
        print('  TWFC.exe: already large-address-aware')
        return
    struct.pack_into('<H', d, pe + 22, ch | 0x20)
    open(exe, 'wb').write(d)
    print('  TWFC.exe: large-address-aware (4 GB) enabled')


def set_fps(exe, fps60):
    d = open(exe, 'rb').read()
    cap30, cap60 = bytes.fromhex('d905303fa012c208'), bytes.fromhex('d9052c696112c208')
    old, new = (cap30, cap60) if fps60 else (cap60, cap30)
    if old in d:
        d = d.replace(old, new)
        open(exe, 'wb').write(d)
    assert d.count(new) == 1, 'max tick rate getter not found (unsupported game version?)'
    print('  TWFC.exe: frame rate cap %d FPS' % (60 if fps60 else 30))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    restore = '--restore' in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    game = args[0]
    tg = os.path.join(game, 'TransGame')
    cooked = os.path.join(tg, 'CookedPC')
    coal = os.path.join(tg, 'Config', 'PC', 'Cooked', 'Coalesced.ini')
    toc = os.path.join(tg, 'PCTOC.txt')
    tgame = os.path.join(cooked, 'TransGame.xxx')
    maps = {m: os.path.join(cooked, m + '.xxx') for m in CHAPTERS}
    exe = os.path.join(game, 'Binaries', 'TWFC.exe')
    for p in [coal, toc, exe] + list(maps.values()):
        if not os.path.exists(p):
            sys.exit('not found: ' + p + '\n(pass the game folder that contains Binaries and TransGame)')

    all_files = [coal, toc, tgame, exe] + list(maps.values())
    if restore:
        for p in all_files:
            if os.path.exists(p + '.original'):
                shutil.copy2(p + '.original', p)
                print('restored', p)
        dlc = os.path.join(game, 'DLC', DLC_NAME)
        if os.path.isdir(dlc):
            shutil.rmtree(dlc)
            print('removed', dlc)
        return

    for p in [coal, toc, exe] + list(maps.values()):
        if not os.path.exists(p + '.original'):
            shutil.copy2(p, p + '.original')
            print('backup:', p + '.original')
    if os.path.exists(tgame + '.original'):
        shutil.copy2(tgame + '.original', tgame)

    print('patching...')
    toc_entries = {}
    if os.path.exists(tgame + '.original'):
        toc_entries[b'CookedPC\\TransGame.xxx'] = open(tgame, 'rb').read()
    extras_by_map, skip = {}, {}
    for m, path in maps.items():
        data, own, extras = patch_chapter_map(path + '.original', path, CHAPTERS[m])
        extras_by_map[m] = extras
        skip[m] = [n for n in CHAPTERS[m] if n not in own and n not in extras]
        toc_entries[('CookedPC\\' + m + '.xxx').encode()] = data
        print('  %s: chapter %s + added %s' % (m, own, extras))
    toc_entries[b'Config\\PC\\Cooked\\Coalesced.ini'] = patch_coalesced(coal + '.original', coal, skip)
    write_dlc(game, extras_by_map)
    set_large_address_aware(exe)
    set_fps(exe, '--fps60' in sys.argv)
    shutil.copy2(toc + '.original', toc)
    update_toc(toc, toc_entries)
    print('done. Start chapters through "Chapter select" (not "continue").')
    print('To undo: python install_mod.py "<game dir>" --restore')


if __name__ == '__main__':
    main()
