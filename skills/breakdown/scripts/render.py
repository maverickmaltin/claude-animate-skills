#!/usr/bin/env python3
"""Turn this skill's animation spec into a video.

    python3 scripts/render.py SPEC.json --out video.mp4           # the video (1080x1920, 30 fps unless the spec says otherwise)
    python3 scripts/render.py SPEC.json --still 2.5 --out f.png   # one frame at 2.5 s, to check the look quickly
    python3 scripts/render.py SPEC.json --still end --out f.png   # the last frame
    python3 scripts/render.py SPEC.json --html page.html          # a standalone page that plays the animation in any browser
    python3 scripts/render.py --check                             # what this computer has (Playwright, a browser, ffmpeg)

SPEC.json is the skill's spec (see SKILL.md and examples/). SPEC can also be inline JSON. The animation itself is
assets/template.html: it reads the spec, draws frame t when window.render(t) is called, and loops on its own when the page
is opened in a browser. Image paths in the spec (keys "photo", "image", "logo") are embedded, so the page is self-contained.

Needs Python 3.8+, Playwright (pip install playwright) with a Chromium browser (Google Chrome is used when installed,
otherwise run: python3 -m playwright install chromium) and ffmpeg (on the PATH, or: pip install imageio-ffmpeg).
"""
import argparse
import base64
import functools
import http.server
import json
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS)
TEMPLATE = os.path.join(SKILL_DIR, 'assets', 'template.html')
FILE_KEYS = ('photo', 'image', 'logo', 'background_image')


def say(*a):
    print(*a, flush=True)


def find_ffmpeg():
    p = shutil.which('ffmpeg')
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    with open(path, 'rb') as f:
        return 'data:%s;base64,%s' % (mime, base64.b64encode(f.read()).decode('ascii'))


def load_spec(arg):
    if arg.lstrip().startswith('{'):
        spec, base = json.loads(arg), os.getcwd()
    else:
        with open(arg, encoding='utf-8') as f:
            spec = json.load(f)
        base = os.path.dirname(os.path.abspath(arg))

    def embed(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, str) and k in FILE_KEYS and v and not v.startswith(('data:', 'http://', 'https://')):
                    p = os.path.expanduser(v if os.path.isabs(v) else os.path.join(base, v))
                    if not os.path.isfile(p):
                        sys.exit('render.py: the %s file was not found: %s' % (k, v))
                    o[k] = data_uri(p)
                else:
                    embed(v)
        elif isinstance(o, list):
            for v in o:
                embed(v)
    embed(spec)
    return spec


def build_html(spec):
    with open(TEMPLATE, encoding='utf-8') as f:
        html = f.read()
    if '/*SPEC*/null' not in html:
        sys.exit('render.py: assets/template.html has no /*SPEC*/null placeholder')
    blob = json.dumps(spec, ensure_ascii=False).replace('</', '<\\/')
    return html.replace('/*SPEC*/null', blob, 1)


def size_of(spec):
    s = str(spec.get('size', '1080x1920')).lower().replace('×', 'x')
    try:
        w, h = [int(round(float(x))) for x in s.split('x')]
        return w - w % 2, h - h % 2
    except Exception:
        return 1080, 1920


def serve(root):
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    handler = functools.partial(Quiet, directory=root)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return port


def launch(p, gpu):
    args = ['--force-color-profile=srgb', '--font-render-hinting=none', '--hide-scrollbars', '--mute-audio',
            '--ignore-gpu-blocklist', '--enable-webgl']
    if gpu and sys.platform == 'darwin':
        args.append('--use-angle=metal')
    elif gpu and sys.platform.startswith('win'):
        args.append('--use-angle=d3d11')
    else:
        args += ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    errors = []
    for kw in ({'channel': 'chrome'}, {}, {'channel': 'msedge'}):
        try:
            return p.chromium.launch(headless=True, args=args, **kw), kw.get('channel', 'chromium')
        except Exception as e:
            errors.append(str(e).strip().splitlines()[0][:160])
    sys.exit('render.py: no browser found. Install Google Chrome, or run: python3 -m playwright install chromium\n  '
             + '\n  '.join(errors))


def check():
    info = {'python': sys.version.split()[0], 'playwright': False, 'browser': None, 'ffmpeg': find_ffmpeg()}
    try:
        from playwright.sync_api import sync_playwright
        info['playwright'] = True
        with sync_playwright() as p:
            for kw in ({'channel': 'chrome'}, {}, {'channel': 'msedge'}):
                try:
                    b = p.chromium.launch(headless=True, **kw)
                    info['browser'] = kw.get('channel', 'chromium')
                    b.close()
                    break
                except Exception:
                    pass
    except Exception:
        pass
    info['ready'] = bool(info['playwright'] and info['browser'] and info['ffmpeg'])
    if not info['ready']:
        fix = []
        if not info['playwright']:
            fix.append('python3 -m pip install playwright')
        if not info['browser']:
            fix.append('python3 -m playwright install chromium')
        if not info['ffmpeg']:
            fix.append('python3 -m pip install imageio-ffmpeg')
        info['fix'] = fix
    say(json.dumps(info, indent=1))
    return 0 if info['ready'] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', nargs='?', help='spec JSON file (or inline JSON)')
    ap.add_argument('--out', help='output .mp4 (or .png with --still)')
    ap.add_argument('--still', default=None, help='render the single frame at this time in seconds (or "end") as a PNG')
    ap.add_argument('--html', help='also write a standalone HTML page that plays the animation')
    ap.add_argument('--fps', type=int, default=None, help='frames per second (default: spec "fps" or 30)')
    ap.add_argument('--size', default=None, help='WIDTHxHEIGHT, e.g. 1080x1920 (vertical), 1920x1080, 1080x1080')
    ap.add_argument('--no-gpu', action='store_true', help='software WebGL (slower; use if 3D pages render black)')
    ap.add_argument('--check', action='store_true', help='report what this computer has and exit')
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    if not a.spec:
        ap.error('give a spec JSON file')
    spec = load_spec(a.spec)
    if a.size:
        spec['size'] = a.size
    w, h = size_of(spec)
    spec['size'] = '%dx%d' % (w, h)
    fps = a.fps or int(spec.get('fps', 30))
    html = build_html(spec)
    if a.html:
        with open(a.html, 'w', encoding='utf-8') as f:
            f.write(html)
        say('page:', os.path.abspath(a.html))
    if not a.out:
        return
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ff = find_ffmpeg()
    if a.still is None and not ff:
        sys.exit('render.py: ffmpeg not found. Install it (macOS: brew install ffmpeg), or run: python3 -m pip install imageio-ffmpeg')
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sys.exit('render.py: Playwright is not installed. Run: python3 -m pip install playwright')

    root = tempfile.mkdtemp(prefix='animate-')
    with open(os.path.join(root, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    port = serve(root)
    t_start = time.time()
    with sync_playwright() as p:
        browser, which = launch(p, gpu=not a.no_gpu)
        page = browser.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
        page.set_default_timeout(180000)
        page.add_init_script('window.__RENDERER__ = true;')
        page.on('console', lambda m: say('  page %s: %s' % (m.type, m.text)) if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: say('  page error:', e))
        page.goto('http://127.0.0.1:%d/index.html' % port)
        page.wait_for_function('window.ready === true || !!window.renderError', timeout=180000)
        err = page.evaluate('window.renderError || null')
        if err:
            sys.exit('render.py: the page could not start: %s' % err)
        duration = float(page.evaluate('window.DURATION || 6'))

        def frame(t, kind='jpeg'):
            page.evaluate('t => Promise.resolve(window.render(t))', t)
            return page.screenshot(type=kind, quality=95) if kind == 'jpeg' else page.screenshot(type='png')

        if a.still is not None:
            st = duration if str(a.still).lower() in ('end', 'last') else float(a.still)
            png = frame(min(max(st, 0), duration), 'png')
            with open(out, 'wb') as f:
                f.write(png)
            say('still:', out)
        else:
            n = int(round(duration * fps))
            cmd = [ff, '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'mjpeg', '-i', '-',
                   '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                   '-r', str(fps), '-movflags', '+faststart', out]
            enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            say('rendering %d frames (%.2f s at %d fps, %dx%d, %s)...' % (n, n / fps, fps, w, h, which))
            for i in range(n):
                enc.stdin.write(frame(i / fps))
                if i and i % (fps * 2) == 0:
                    say('  %d/%d frames' % (i, n))
            enc.stdin.close()
            if enc.wait() != 0:
                sys.exit('render.py: ffmpeg failed')
            say('video: %s (%.2f s, %dx%d, %d fps, rendered in %.0f s)' % (out, n / fps, w, h, fps, time.time() - t_start))
        # headless Chrome can hang while closing after many frames: leave without waiting for it
        sys.stdout.flush()
        os._exit(0)


if __name__ == '__main__':
    main()
