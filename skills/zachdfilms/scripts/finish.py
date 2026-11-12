#!/usr/bin/env python3
"""Finish a /zachdfilms explainer: put the what-if question on the generated clip(s) and write one MP4.

    python3 scripts/finish.py --clip moon.mp4 --title "What if the Moon|disappeared?" --out what-if-moon.mp4
    python3 scripts/finish.py --clip s1.mp4 --clip s2.mp4 --caption "" --caption "The tides would shrink" \
                              --title "What if the Moon|disappeared?" --out what-if-moon.mp4

The question is set like the big 3D what-if explainers: heavy white type with a black outline, the last line in yellow,
sliding in over the first third of a second, on the first clip ("|" breaks the line). Later clips can each carry a short
caption (give one --caption per --clip, in order; "" for none). A soft dark gradient sits behind the question so it reads
on bright shots. Output: 1080x1920 unless --size, H.264 + AAC, the clips' own sound kept (silence where a clip has none)
and levelled to --loudness LUFS (default -16, about what short-form apps play at). Needs ffmpeg with the drawtext filter.
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(os.path.dirname(HERE), 'assets', 'fonts', 'ArchivoBlack-Regular.ttf')
YELLOW, WHITE = '#FFD36B', '#FFFFFF'


def find_ffmpeg():
    p = shutil.which('ffmpeg')
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit('finish.py: ffmpeg not found. Install it (macOS: brew install ffmpeg), or: python3 -m pip install imageio-ffmpeg')


def advances(font_path):
    """Advance widths (in em) per character, read straight from the font's cmap and hmtx tables (no extra packages)."""
    d = open(font_path, 'rb').read()
    tables = {}
    for i in range(struct.unpack('>H', d[4:6])[0]):
        tag, _, off, ln = struct.unpack('>4sIII', d[12 + 16 * i:28 + 16 * i])
        tables[tag] = (off, ln)
    upem = struct.unpack('>H', d[tables[b'head'][0] + 18:tables[b'head'][0] + 20])[0]
    nhm = struct.unpack('>H', d[tables[b'hhea'][0] + 34:tables[b'hhea'][0] + 36])[0]
    ho = tables[b'hmtx'][0]
    adv = [struct.unpack('>H', d[ho + 4 * i:ho + 4 * i + 2])[0] for i in range(nhm)]
    co = tables[b'cmap'][0]
    cmap = {}
    for i in range(struct.unpack('>H', d[co + 2:co + 4])[0]):
        pid, eid, so = struct.unpack('>HHI', d[co + 4 + 8 * i:co + 12 + 8 * i])
        st = co + so
        if struct.unpack('>H', d[st:st + 2])[0] != 4 or (pid, eid) not in ((3, 1), (0, 3), (0, 4)):
            continue
        n = struct.unpack('>H', d[st + 6:st + 8])[0] // 2
        ends = struct.unpack('>%dH' % n, d[st + 14:st + 14 + 2 * n])
        starts = struct.unpack('>%dH' % n, d[st + 16 + 2 * n:st + 16 + 4 * n])
        deltas = struct.unpack('>%dh' % n, d[st + 16 + 4 * n:st + 16 + 6 * n])
        ro = st + 16 + 6 * n
        ranges = struct.unpack('>%dH' % n, d[ro:ro + 2 * n])
        for k in range(n):
            for c in range(starts[k], min(ends[k], 0xFFFE) + 1):
                if ranges[k] == 0:
                    gid = (c + deltas[k]) & 0xFFFF
                else:
                    a = ro + 2 * k + ranges[k] + 2 * (c - starts[k])
                    gid = struct.unpack('>H', d[a:a + 2])[0]
                    gid = (gid + deltas[k]) & 0xFFFF if gid else 0
                cmap[c] = gid
        break
    return lambda ch: adv[min(cmap.get(ord(ch), 0), len(adv) - 1)] / upem


def probe(ff, path):
    ffprobe = os.path.join(os.path.dirname(ff), 'ffprobe' + ('.exe' if ff.endswith('.exe') else ''))
    if os.path.exists(ffprobe):
        r = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path], capture_output=True, text=True)
        if r.returncode == 0:
            j = json.loads(r.stdout)
            v = next((s for s in j['streams'] if s['codec_type'] == 'video'), None)
            a = any(s['codec_type'] == 'audio' for s in j['streams'])
            num, den = (v.get('r_frame_rate') or '24/1').split('/')
            return {'fps': float(num) / float(den or 1), 'audio': a, 'dur': float(j['format'].get('duration', 0))}
    r = subprocess.run([ff, '-hide_banner', '-i', path], capture_output=True, text=True)   # no ffprobe: read ffmpeg's banner
    e = r.stderr
    import re
    m = re.search(r'(\d+(?:\.\d+)?) fps', e)
    dm = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', e)
    dur = int(dm.group(1)) * 3600 + int(dm.group(2)) * 60 + float(dm.group(3)) if dm else 0
    return {'fps': float(m.group(1)) if m else 24.0, 'audio': 'Audio:' in e, 'dur': dur}


def esc(path):
    return path.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--clip', action='append', required=True, help='a generated clip (repeat for several shots, in order)')
    ap.add_argument('--title', required=True, help='the what-if question; "|" breaks the line, the last line is yellow')
    ap.add_argument('--caption', action='append', default=[], help='one per --clip, in order ("" for none)')
    ap.add_argument('--size', default='1080x1920')
    ap.add_argument('--loudness', type=float, default=-16.0, help='target loudness in LUFS (0 keeps the sound as it is)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ff = find_ffmpeg()
    W, H = [int(x) for x in a.size.lower().split('x')]
    U = min(W / 1080, H / 1350)
    width_of = advances(FONT)
    tmp = tempfile.mkdtemp(prefix='zach-')
    infos = [probe(ff, c) for c in a.clip]
    fps = infos[0]['fps'] or 24

    def text_filters(lines, top, size, colors, fade=True):
        out = []
        for i, (line, col) in enumerate(zip(lines, colors)):
            tf = os.path.join(tmp, 't%d_%d.txt' % (len(os.listdir(tmp)), i))
            with open(tf, 'w', encoding='utf-8') as f:
                f.write(line)
            y = '%.1f+%.1f*(1-min(t/0.35\\,1))' % (top + i * size * 1.12, 22 * U) if fade else '%.1f' % (top + i * size * 1.12)
            alpha = 'min(t/0.35\\,1)' if fade else '1'
            out.append("drawtext=fontfile='%s':textfile='%s':fontsize=%d:fontcolor=%s:borderw=%d:bordercolor=black@0.92:"
                       "shadowcolor=black@0.55:shadowx=0:shadowy=%d:x=(w-text_w)/2:y=%s:alpha=%s"
                       % (esc(FONT), esc(tf), size, col, max(4, round(size * 0.13)), round(6 * U), y, alpha))
        return out

    lines = [s.strip() for s in a.title.replace('\n', '|').split('|') if s.strip()]
    if len(lines) == 1 and len(lines[0]) > 16:          # one long line: break it near the middle, on a space
        words, best = lines[0].split(), None
        for k in range(1, len(words)):
            l1, l2 = ' '.join(words[:k]), ' '.join(words[k:])
            score = max(len(l1), len(l2))
            if best is None or score < best[0]:
                best = (score, [l1, l2])
        lines = best[1] if best else lines
    em = max(sum(width_of(c) for c in l) for l in lines)
    size = int(min(100 * U, W * 0.88 / max(em, 0.1)))
    colors = [WHITE] * (len(lines) - 1) + [YELLOW] if len(lines) > 1 else [WHITE]
    top = H * 0.152 - size * 0.8

    parts, fc = [], []
    for i, (clip, info) in enumerate(zip(a.clip, infos)):
        chain = ['scale=%d:%d:force_original_aspect_ratio=increase' % (W, H), 'crop=%d:%d' % (W, H), 'fps=%g' % fps, 'setsar=1', 'format=yuv420p']
        if i == 0:
            gh = int(top + len(lines) * size * 1.12 + 220 * U)    # a soft dark band behind the question, fading in with it
            fc.append("color=c=black:s=%dx%d:r=%g,format=rgba,geq=r='0':g='0':b='0':a='150*pow(1-Y/H\\,1.5)',fade=t=in:st=0:d=0.35:alpha=1[grad]" % (W, gh, fps))
            fc.append('[%d:v]%s[base0]' % (i, ','.join(chain)))
            fc.append('[base0][grad]overlay=0:0:shortest=1[v0pre]')
            chain = ['null'] + text_filters(lines, top, size, colors)
            src = '[v0pre]'
        else:
            src = '[%d:v]' % i
        cap = a.caption[i] if i < len(a.caption) else ''
        if cap:
            cs = int(min(64 * U, W * 0.86 / max(sum(width_of(c) for c in cap), 0.1)))
            chain += text_filters([cap], H * 0.70, cs, [WHITE])
        fc.append('%s%s[v%d]' % (src, ','.join(chain), i))
        if info['audio']:
            fc.append('[%d:a]aresample=48000,aformat=channel_layouts=stereo[a%d]' % (i, i))
        else:
            fc.append('anullsrc=r=48000:cl=stereo,atrim=0:%.3f[a%d]' % (max(info['dur'], 0.1), i))
        parts.append('[v%d][a%d]' % (i, i))
    fc.append('%sconcat=n=%d:v=1:a=1[v][acat]' % (''.join(parts), len(a.clip)))
    fc.append('[acat]%s[a]' % ('loudnorm=I=%g:TP=-1.5:LRA=11,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo' % a.loudness if a.loudness else 'anull'))
    cmd = [ff, '-v', 'error', '-y']
    for c in a.clip:
        cmd += ['-i', c]
    cmd += ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', a.out]
    r = subprocess.run(cmd)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        sys.exit('finish.py: ffmpeg failed (does your ffmpeg have the drawtext filter? run: ffmpeg -filters | grep drawtext)')
    print('video: %s (%d clip%s, %dx%d, title "%s")' % (os.path.abspath(a.out), len(a.clip), '' if len(a.clip) == 1 else 's', W, H, ' / '.join(lines)))


if __name__ == '__main__':
    main()
