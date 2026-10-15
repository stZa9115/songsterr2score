#!/usr/bin/env python3
"""
songsterr2score.py  --  Songsterr 網頁 (另存的 .html) -> 五線譜/四線譜
輸入 : 用瀏覽器「另存網頁」存下的 Songsterr 譜頁 (.html)
輸出 : <name>.musicxml          (MuseScore 等軟體可開，含五線譜+TAB 兩個譜表)
       <name>_both.ly/.pdf      (五線譜+TAB 合併)
       <name>_staff.ly/.pdf     (只有五線譜)
       <name>_tab.ly/.pdf       (只有 TAB)
       PDF 需要安裝 LilyPond (https://lilypond.org)；找不到就只輸出 .ly 與 .musicxml
用法 : uv run python -m songsterr2score 譜.html [更多.html 或資料夾 ...] [-o 輸出資料夾] [--bars 1-16] [--name 譜名]
需求 : Python 3.10+ 與 uv sync
"""
import re, sys, json, html as htmllib, shutil, argparse, subprocess, pathlib
from svgpathtools import parse_path

NAMES = ['c','cis','d','dis','e','f','fis','g','gis','a','ais','b']
XSTEP = [('C',0),('C',1),('D',0),('D',1),('E',0),('F',0),('F',1),('G',0),('G',1),('A',0),('A',1),('B',0)]
DUR_LY = {1:'16',2:'8',3:'8.',4:'4',6:'4.',8:'2',12:'2.',16:'1'}
DUR_XML = {1:('16th',0),2:('eighth',0),3:('eighth',1),4:('quarter',0),6:('quarter',1),8:('half',0),12:('half',1),16:('whole',0)}

class SongsterrError(Exception):
    """無法轉換：不是 Songsterr 譜頁、找不到譜面、譜名為空等。訊息為繁中。"""

# ---------------------------------------------------------------- 讀 HTML
def split_lines(html):
    st = [m.start() for m in re.finditer(r'<svg viewBox="[^"]*" data-testid="multitrack-line-group-\d+"', html)]
    st.append(len(html))
    return [re.sub(r'<defs>.*?</defs>', '', html[st[i]:st[i+1]], flags=re.S) for i in range(len(st)-1)]

def read_json(html, key):
    """頁面內嵌 JSON 中第一個 "key": 之後的值；讀不到時回傳 None"""
    i = html.find('"%s":' % key)
    if i < 0: return None
    try: return json.JSONDecoder().raw_decode(html, i+len(key)+3)[0]
    except ValueError: return None

def read_tracks(html):
    t = read_json(html, 'tracks')
    return t if isinstance(t, list) else []

def page_title(html):
    m = re.search(r'<title>(.*?)</title>', html, re.S)
    return htmllib.unescape(m.group(1)).split('|')[0].strip() if m else ''

def default_name(html):
    """預設譜名「曲名 - 藝人」，取自 meta.current；讀不到時退回 <title> 中 | 之前的文字"""
    meta = read_json(html, 'meta')
    cur = meta.get('current') if isinstance(meta, dict) else None
    if isinstance(cur, dict) and cur.get('title') and cur.get('artist'):
        return '%s - %s' % (cur['title'].strip(), cur['artist'].strip())
    return page_title(html)

def safe_filename(name):
    """Windows 不允許的字元換成 _，去除首尾空白與句點"""
    return re.sub(r'^[\s.]+|[\s.]+$', '', re.sub(r'[\\/:*?"<>|]', '_', name))

def line_counts(html):
    """(實際譜行數, 應有譜行數)；未渲染的譜行只留下佔位元素"""
    have = len(set(re.findall(r'data-testid="multitrack-line-group-(\d+)"', html)))
    return have, len(re.findall(r'data-player-key="tab" data-line-unit-index="\d+"', html))

def glyphs_of(d):
    out = []
    for sp in parse_path(d).continuous_subpaths():
        x0, x1, y0, y1 = sp.bbox()
        out.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, w=x1-x0, h=y1-y0, n=len(sp), holes=[]))
    out.sort(key=lambda g: -g['w']*g['h'])
    gl = []
    for g in out:
        for G in gl:
            if G['x0']-.01 <= g['x0'] and g['x1'] <= G['x1']+.01 and G['y0']-.01 <= g['y0'] and g['y1'] <= G['y1']+.01:
                G['holes'].append(g); break
        else: gl.append(g)
    gl.sort(key=lambda g: g['x0'])
    return gl

def classify(g):
    w, h, n, nh = g['w'], g['h'], g['n'], len(g['holes'])
    if abs(w-3) < .6 and abs(h-3) < .6: return 'dot'
    if abs(w-8) < 1.5 and abs(h-24) < 3: return 'qrest'
    if abs(w-12) < 1.5 and abs(h-6) < 1.5: return 'wrest'      # 半/全休止符
    if abs(w-9) < 1.5 and abs(h-15) < 3: return 'erest'
    if abs(h-10) < .8:
        if nh == 0:
            if w < 5: return '1'
            return {16:'3', 14:'5', 15:'5', 11:'2', 8:'7'}.get(n, '?')
        if nh == 2: return '8'
        if nh == 1:
            hh = g['holes'][0]; off = hh['y0']-g['y0']
            if hh['h'] < 3.5: return '4'
            if hh['w'] < 2.6 and hh['h'] > 6: return '0'
            return '6' if off >= 3.5 else '9'
    return '?'

def parse_html(html, warn):
    tracks = read_tracks(html)
    m = re.search(r'data-part-id="(\d+)"', html)
    part = int(m.group(1)) if m else None
    tr = next((t for t in tracks if t.get('partId') == part), None)
    tuning = (tr or {}).get('tuning')
    title = page_title(html) or 'Songsterr'
    lines = split_lines(html)
    if not lines: raise SongsterrError("找不到譜面 (multitrack-line-group)；請確認是 Songsterr 譜頁並在完整載入後另存。")
    have, want = line_counts(html)
    if want and have != want: warn('頁面只包含 %d/%d 行譜，請用 tools/collect-songsterr.js 收集完整譜面' % (have, want))
    if not tuning:
        n = len(re.findall(r'class="-0AoUa_tuning"', lines[0]))
        tuning = [43,38,33,28] if n == 4 else [64,59,55,50,45,40]
        warn('讀不到調弦，改用預設 %s' % tuning)
    ns = len(tuning)
    meas = {}      # 小節號 -> events
    allm = []      # 所有小節號 (含空小節)
    sigs = []      # (小節號, 分子, 分母)
    tempo = None
    prev_last = 0
    for L in lines:
        markers = [(float(a), int(b)) for a, b in re.findall(r'<text x="([\d.-]+)" y="-8" class="j6szJq_number">(\d+)<', L)]
        nums = [b for _, b in markers]
        if nums:
            if nums[0] != prev_last+1: warn('第 %d 小節前可能缺少譜行 (頁面可能未完整載入)' % nums[0])
            prev_last = nums[-1]; allm += nums
        for x, a, b in re.findall(r'<text x="([\d.-]+)" y="[\d.-]+" [^>]*class="ai7mjG_signature">(\d+)</text>\s*<text x="[\d.-]+" y="[\d.-]+" [^>]*class="ai7mjG_signature">(\d+)<', L):
            owner = [mn for mx, mn in markers if mx <= float(x)+1]
            sigs.append((owner[-1] if owner else (nums[0] if nums else 1), int(a), int(b)))
        t = re.search(r'ai7mjG_tempoText">=\s*(\d+)', L)
        if t and tempo is None: tempo = int(t.group(1))
        stems = [float(v) for v in re.findall(r'M([\d.]+),50v18', L)]
        beams = [(int(float(y)), float(x), float(x)+float(w)) for x, y, w in re.findall(r'M([\d.]+),(\d+)v2h([\d.]+)v-2z', L)]
        for d, mn in re.findall(r'<path d="([^"]*)"[^>]*data-notes-measure="(\d+)"', L):
            mn = int(mn); evs = []; cur = None; dots = []
            for g in glyphs_of(d):
                c = classify(g)
                if c == '?':
                    warn('第 %d 小節有無法辨識的符號 (%.0fx%.0f)，已略過' % (mn, g['w'], g['h'])); continue
                if c.isdigit():
                    if cur and abs((g['y0']+g['y1'])-(cur['y0']+cur['y1'])) < 1 and g['x0']-cur['x1'] < 3:
                        cur['txt'] += c; cur['x1'] = g['x1']
                    else:
                        cur = dict(kind='note', txt=c, x0=g['x0'], x1=g['x1'], y0=g['y0'], y1=g['y1'], dots=0); evs.append(cur)
                elif c == 'dot': dots.append(g)
                else: evs.append(dict(kind=c, x0=g['x0'], x1=g['x1'], dots=0))
            for dt in dots:
                best = None
                for e in evs:
                    if e['x1'] <= dt['x0']+1 and dt['x0']-e['x1'] < 9: best = e
                if best: best['dots'] += 1
                else: warn('第 %d 小節有找不到對象的附點' % mn)
            for e in evs:
                if e['kind'] == 'note':
                    s = [v for v in stems if e['x0']-1 <= v <= e['x1']+1]
                    e['stem'] = s[0] if s else None
                    if s:
                        lv = sum(1 for y in (66, 61) if any(yy == y and a-.1 <= s[0] <= b+.1 for yy, a, b in beams))
                        e['base'] = {0:4, 1:2, 2:1}[lv]
                    else: e['base'] = None
                else: e['base'] = {'qrest':4, 'erest':2, 'wrest':None}[e['kind']]
            meas[mn] = evs
    return dict(title=title, tuning=tuning, meas=meas, allm=sorted(set(allm) | set(meas)), sigs=sigs, tempo=tempo or 120, ns=ns)

# ---------------------------------------------------------------- 節奏
def measure_units(sigs, mn):
    a, b = 4, 4
    for m, x, y in sigs:
        if m <= mn: a, b = x, y
    return a*16//b, (a, b)

def finalize(song, warn):
    """每個事件補上 units / string / fret / midi"""
    tun = song['tuning']
    for mn in song['allm']:
        total, _ = measure_units(song['sigs'], mn)
        evs = sorted(song['meas'].get(mn, []), key=lambda e: e['x0'])
        song['meas'][mn] = evs
        for e in evs:
            if e['base'] is not None: e['u'] = e['base']*3//2 if e['dots'] else e['base']
        unk = [e for e in evs if e['base'] is None]
        known = sum(e['u'] for e in evs if e['base'] is not None)
        rem = total-known
        if unk:
            if len(unk) == 1: unk[0]['u'] = rem
            else:
                for e in unk: e['u'] = rem//len(unk)
                warn('第 %d 小節有 %d 個無符桿音符/休止符，時值為估計' % (mn, len(unk)))
            for e in unk:
                if e['u'] not in DUR_LY:
                    warn('第 %d 小節時值 %d/16 無法表示，改用最接近值' % (mn, e['u']))
                    e['u'] = min(DUR_LY, key=lambda k: abs(k-e['u']))
        if evs and sum(e['u'] for e in evs) != total:
            warn('第 %d 小節拍數不符 (%d/%d 個十六分音符)，請對照原譜' % (mn, sum(e['u'] for e in evs), total))
        if not evs: song['meas'][mn] = [dict(kind='wrest', u=total, x0=0, dots=0)]
        for e in song['meas'][mn]:
            if e['kind'] == 'note':
                si = min(range(song['ns']), key=lambda i: abs((e['y0']+e['y1'])/2-(0.5+12*i)))
                e['string'] = si; e['fret'] = int(e['txt']); e['midi'] = tun[si]+e['fret']
    return song

# ---------------------------------------------------------------- LilyPond
def ly_pitch(m):
    k = (m//12-1)-3
    return NAMES[m % 12] + ("'"*k if k > 0 else ","*(-k))

def ly_measure(song, mn):
    out = []
    for e in song['meas'][mn]:
        d = DUR_LY[e['u']]
        if e['kind'] == 'note': out.append('%s%s\\%d' % (ly_pitch(e['midi']), d, e['string']+1))
        elif e['u'] == measure_units(song['sigs'], mn)[0]: out.append('R%s' % d)
        else: out.append('r%s' % d)
    return ' '.join(out)

def build_ly(song, first, last, mode, per_line=4):
    bass = song['ns'] <= 5
    body = []; lastsig = None
    for mn in range(first, last+1):
        if mn not in song['meas']: continue
        sg = measure_units(song['sigs'], mn)[1]
        if sg != lastsig: body.append('\\time %d/%d' % sg); lastsig = sg
        body.append(ly_measure(song, mn)+' | %% %d' % mn)
        if (mn-first+1) % per_line == 0 and mn != last: body.append('\\break')
    tun = ' '.join(ly_pitch(m) for m in reversed(song['tuning']))
    clef = 'bass_8' if bass else 'treble_8'
    name = 'Bass' if bass else 'Guitar'
    label = {'both':'notation + tab', 'staff':'staff', 'tab':'tab'}[mode]
    title = song['title'].replace('"', "'")
    ly = '\\version "2.24.0"\n\\header { title = "%s" subtitle = "%s, bars %d-%d" tagline = ##f }\n' % (title, label, first, last)
    ly += '\\paper { indent = 0\\mm paper-width = 210\\mm paper-height = 297\\mm ragged-last = ##t }\n'
    ly += 'mus = { \\tempo 4 = %d \\set Score.currentBarNumber = #%d\n%s\n\\bar "|." }\n' % (song['tempo'], first, '\n'.join(body))
    staff = '\\new Staff \\with { instrumentName = "%s" } { \\clef "%s" \\mus }' % (name, clef)
    tab = '\\new TabStaff \\with { stringTunings = \\stringTuning <%s> } { \\clef moderntab \\mus }' % tun
    sc = {'both':'<< %s %s >>' % (staff, tab), 'staff':staff, 'tab':tab}[mode]
    ly += '\\score { %s \\layout { \\context { \\Voice \\override StringNumber.stencil = ##f } \\context { \\Score \\override BarNumber.break-visibility = ##(#f #t #t) } } }\n' % sc
    return ly

# ---------------------------------------------------------------- MusicXML
def build_xml(song, first, last):
    bass = song['ns'] <= 5
    ns = song['ns']
    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
         '<score-partwise version="3.1"><work><work-title>%s</work-title></work>' % song['title'].replace('&','&amp;').replace('<','&lt;'),
         '<part-list><score-part id="P1"><part-name>%s</part-name></score-part></part-list><part id="P1">' % ('Bass' if bass else 'Guitar')]
    lastsig = None
    for mn in range(first, last+1):
        if mn not in song['meas']: continue
        total, sg = measure_units(song['sigs'], mn)
        o.append('<measure number="%d">' % mn)
        if mn == first or sg != lastsig:
            attr = '<attributes>'
            if mn == first:
                attr += '<divisions>4</divisions><key><fifths>0</fifths></key>'
            attr += '<time><beats>%d</beats><beat-type>%d</beat-type></time>' % sg
            if mn == first:
                attr += '<staves>2</staves>'
                attr += '<clef number="1"><sign>F</sign><line>4</line></clef><clef number="2"><sign>TAB</sign><line>5</line></clef>'
                attr += '<staff-details number="2"><staff-lines>%d</staff-lines>' % ns
                for i, m in enumerate(reversed(song['tuning'])):
                    st, al = XSTEP[m % 12]
                    attr += '<staff-tuning line="%d"><tuning-step>%s</tuning-step>%s<tuning-octave>%d</tuning-octave></staff-tuning>' % (i+1, st, '<tuning-alter>1</tuning-alter>' if al else '', m//12-1)
                attr += '</staff-details>'
                if bass: attr += '<transpose><diatonic>0</diatonic><chromatic>0</chromatic><octave-change>-1</octave-change></transpose>'
            attr += '</attributes>'
            o.append(attr)
            if mn == first:
                o.append('<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>%d</per-minute></metronome></direction-type><sound tempo="%d"/></direction>' % (song['tempo'], song['tempo']))
            lastsig = sg
        for staff in (1, 2):
            for e in song['meas'][mn]:
                typ, dots = DUR_XML[e['u']]
                x = '<note>'
                if e['kind'] == 'note':
                    m = e['midi']+(12 if (bass and staff == 1) else 0)
                    st, al = XSTEP[m % 12]
                    x += '<pitch><step>%s</step>%s<octave>%d</octave></pitch>' % (st, '<alter>1</alter>' if al else '', m//12-1)
                else:
                    x += '<rest measure="yes"/>' if e['u'] == total else '<rest/>'
                x += '<duration>%d</duration><voice>%d</voice><type>%s</type>' % (e['u'], staff, typ)
                x += '<dot/>'*dots + '<staff>%d</staff>' % staff
                if e['kind'] == 'note':
                    x += '<notations><technical><string>%d</string><fret>%d</fret></technical></notations>' % (ns-e['string'], e['fret'])
                o.append(x+'</note>')
            if staff == 1: o.append('<backup><duration>%d</duration></backup>' % total)
        o.append('</measure>')
    o.append('</part></score-partwise>')
    return '\n'.join(o)

# ---------------------------------------------------------------- 主程式
def find_lilypond(user):
    cands = [user] if user else []
    cands += [shutil.which('lilypond'), shutil.which('lilypond.exe')]
    for base in (r'C:\Program Files\LilyPond', r'C:\Program Files (x86)\LilyPond', r'C:\LilyPond'):
        p = pathlib.Path(base)
        if p.exists(): cands += [str(x) for x in p.glob('**/lilypond.exe')]
    return next((c for c in cands if c and pathlib.Path(c).exists()), None)

def convert(path, outdir, bars, lily, name=None):
    """轉換一個 html；name 為譜名 (預設 default_name)。回傳 (輸出檔路徑, 警告)"""
    path, outdir = pathlib.Path(path), pathlib.Path(outdir)
    warns = []
    warn = lambda s: (warns.append(s), print('  [注意]', s))
    print('讀取', path.name)
    html = path.read_text(encoding='utf-8', errors='replace')
    song = finalize(parse_html(html, warn), warn)
    song['title'] = (name if name is not None else default_name(html)).strip()
    stem = safe_filename(song['title'])
    if not stem: raise SongsterrError('譜名不可為空')
    allm = song['allm']
    first, last = (bars if bars else (min(allm), max(allm)))
    first, last = max(first, min(allm)), min(last, max(allm))
    outdir.mkdir(parents=True, exist_ok=True)
    files = [outdir/(stem+'.musicxml')]
    files[0].write_text(build_xml(song, first, last), encoding='utf-8')
    for mode in ('both', 'staff', 'tab'):
        f = outdir/('%s_%s.ly' % (stem, mode))
        f.write_text(build_ly(song, first, last, mode), encoding='utf-8')
        files.append(f)
        if lily:
            r = subprocess.run([lily, '-s', '-o', str(outdir/('%s_%s' % (stem, mode))), str(f)], capture_output=True, encoding='utf-8', errors='replace')
            if r.returncode: warn('LilyPond 轉 %s 失敗: %s' % (mode, r.stderr.strip()[-200:]))
            else: files.append(f.with_suffix('.pdf'))
    print('  %d 弦 調弦 MIDI %s | 小節 %d-%d | 輸出 -> %s' % (song['ns'], song['tuning'], first, last, outdir))
    if not lily: print('  (找不到 LilyPond，只輸出 .musicxml 與 .ly；安裝 LilyPond 後重跑即可得到 PDF)')
    return files, warns

def main():
    ap = argparse.ArgumentParser(description='Songsterr 另存 HTML -> 五線譜/TAB')
    ap.add_argument('inputs', nargs='+', help='.html 檔或含 .html 的資料夾')
    ap.add_argument('-o', '--out', help='輸出資料夾 (預設: 與 html 同資料夾下的 output)')
    ap.add_argument('--bars', help='只轉換小節範圍，例如 1-16')
    ap.add_argument('--lilypond', help='lilypond 執行檔路徑 (預設自動尋找)')
    ap.add_argument('--name', help='譜名，作為 PDF 標題與輸出檔名 (預設「曲名 - 藝人」)；只能用於單一檔案')
    a = ap.parse_args()
    bars = tuple(int(x) for x in a.bars.split('-')) if a.bars else None
    files = []
    for i in a.inputs:
        p = pathlib.Path(i)
        files += sorted(p.glob('*.html')) if p.is_dir() else [p]
    if a.name is not None and len(files) != 1: ap.error('--name 只能用於單一檔案')
    lily = find_lilypond(a.lilypond)
    failed = 0
    for f in files:
        out = pathlib.Path(a.out) if a.out else f.parent/'output'
        try: convert(f, out, bars, lily, a.name)
        except (SongsterrError, OSError) as e:
            print('  [錯誤]', f.name, e); failed += 1
    if failed: sys.exit(1)

if __name__ == '__main__':
    main()
