#!/usr/bin/env python3
"""Find two places and the real route between them, and write the /map-route spec.

    python3 scripts/route.py "Times Square, New York" "Empire State Building, New York" --out map-spec.json
    python3 scripts/route.py "London" "Paris" --mode drive --labels "London" "Paris" --out map-spec.json
    python3 scripts/route.py "40.7580,-73.9855" "40.7484,-73.9857" --out map-spec.json      # coordinates work too

Places are found with OpenStreetMap's Nominatim (Photon as a fallback). Routes come from the FOSSGIS OSRM servers
(routing.openstreetmap.de: foot, bike, car), with the public OSRM demo as a fallback for driving. --mode auto picks walk
under 4 km in a straight line, drive under 900 km, and a great-circle flight beyond that (or when there is no road between them).
It prints what it found (check the places are the right ones) and writes a spec that scripts/render.py turns into the video.
No API keys. Please keep it to a few requests a minute: these are free community servers.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = 'animate-skills-map-route/1.0 (a Claude skill; one route per run)'
IMPERIAL = {'us', 'gb', 'lr', 'mm'}


def get(url, timeout=25):
    """GET JSON. Falls back to curl when Python's own TLS can't talk to the server (old macOS Pythons)."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))        # OSRM answers "no route" as JSON with an error status
        except Exception:
            raise e
    except Exception as e:
        if not shutil.which('curl'):
            raise
        r = subprocess.run(['curl', '-sS', '--max-time', str(timeout), '-A', UA, '-H', 'Accept: application/json', url],
                           capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            raise RuntimeError('%s (curl: %s)' % (e, r.stderr.strip()[:200]))
        return json.loads(r.stdout)


def parse_coords(q):
    try:
        a, b = [float(x) for x in q.replace(' ', '').split(',')]
        if -90 <= a <= 90 and -180 <= b <= 180:
            return a, b
    except Exception:
        pass
    return None


def geocode(q):
    c = parse_coords(q)
    if c:
        return {'name': q, 'lat': c[0], 'lon': c[1], 'display': q, 'cc': ''}
    try:
        r = get('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
            {'q': q, 'format': 'jsonv2', 'limit': 1, 'addressdetails': 1}))
        if r:
            x = r[0]
            return {'name': x.get('name') or q.split(',')[0].strip(), 'lat': float(x['lat']), 'lon': float(x['lon']),
                    'display': x.get('display_name', ''), 'cc': (x.get('address') or {}).get('country_code', '')}
    except Exception as e:
        print('  Nominatim failed (%s), trying Photon' % e, file=sys.stderr)
    r = get('https://photon.komoot.io/api/?' + urllib.parse.urlencode({'q': q, 'limit': 1}))
    if not r.get('features'):
        sys.exit('route.py: no place found for "%s". Try a fuller name (add the city and country).' % q)
    f = r['features'][0]
    pr = f.get('properties', {})
    lon, lat = f['geometry']['coordinates']
    disp = ', '.join(str(pr[k]) for k in ('name', 'city', 'state', 'country') if pr.get(k))
    return {'name': pr.get('name') or q.split(',')[0].strip(), 'lat': lat, 'lon': lon, 'display': disp,
            'cc': (pr.get('countrycode') or '').lower()}


def haversine(a, b):
    R = 6371008.8
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def osrm(profile, a, b):
    coords = '%.6f,%.6f;%.6f,%.6f' % (a[0], a[1], b[0], b[1])
    q = '?overview=full&geometries=geojson'
    urls = ['https://routing.openstreetmap.de/routed-%s/route/v1/driving/%s%s' % (profile, coords, q)]
    if profile == 'car':
        urls.append('https://router.project-osrm.org/route/v1/driving/%s%s' % (coords, q))
    errors = []
    for u in urls:
        try:
            r = get(u, timeout=40)
        except Exception as e:
            errors.append('%s: %s' % (u.split('/route')[0], e))
            continue
        if r.get('code') == 'Ok' and r.get('routes'):
            rt = r['routes'][0]
            return rt['geometry']['coordinates'], float(rt['distance']), float(rt['duration'])
        return None                       # the server answered: there is no route (e.g. an ocean between them)
    sys.exit('route.py: the routing servers could not be reached, so no route was drawn:\n  ' + '\n  '.join(errors)
             + '\nCheck the internet connection and try again in a minute (or use --mode fly for a straight flight arc).')


def great_circle(a, b, n=160):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    d = 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    if d < 1e-9:
        return [list(a), list(b)]
    out = []
    for i in range(n + 1):
        f = i / n
        A, B = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
        x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
        y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
        z = A * math.sin(la1) + B * math.sin(la2)
        out.append([math.degrees(math.atan2(y, x)), math.degrees(math.atan2(z, math.hypot(x, y)))])
    for i in range(1, len(out)):          # keep longitudes continuous across the date line
        while out[i][0] - out[i - 1][0] > 180:
            out[i][0] -= 360
        while out[i][0] - out[i - 1][0] < -180:
            out[i][0] += 360
    return out


def thin(coords, keep=1500):
    if len(coords) <= keep:
        return coords
    step = (len(coords) - 1) / (keep - 1)
    return [coords[int(round(i * step))] for i in range(keep)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('origin')
    ap.add_argument('destination')
    ap.add_argument('--mode', default='auto', choices=['auto', 'walk', 'bike', 'drive', 'fly'])
    ap.add_argument('--labels', nargs=2, metavar=('FROM', 'TO'), help='short names to show on the pins')
    ap.add_argument('--title', help='the card text (default: "FROM → TO")')
    ap.add_argument('--style', default='light', choices=['light', 'dark', 'color'])
    ap.add_argument('--units', default='auto', choices=['auto', 'metric', 'imperial'])
    ap.add_argument('--size', default='1080x1920')
    ap.add_argument('--out', required=True, help='spec JSON to write')
    a = ap.parse_args()

    A = geocode(a.origin)
    time.sleep(1.1)                       # Nominatim's fair-use limit: one request a second
    B = geocode(a.destination)
    pa, pb = (A['lon'], A['lat']), (B['lon'], B['lat'])
    straight = haversine(pa, pb)
    mode = a.mode
    if mode == 'auto':
        mode = 'walk' if straight < 4000 else 'drive' if straight < 900000 else 'fly'
    route = None
    if mode != 'fly':
        route = osrm({'walk': 'foot', 'bike': 'bike', 'drive': 'car'}[mode], pa, pb)
        if route and route[1] > 4 * max(straight, 1) and straight > 50000:
            route = None                  # a huge detour (a ferry or no road link): fly instead
        if not route:
            if a.mode != 'auto' or straight < 50000:
                sys.exit('route.py: no %s route found between them. Check the places, or try --mode drive or --mode fly.' % mode)
            print('  no road route between them: drawing a flight instead', file=sys.stderr)
            mode = 'fly'
    if mode == 'fly':
        coords, dist = great_circle(pa, pb), straight
        dur = dist / (850 / 3.6) + 1800
    else:
        coords, dist, dur = route
    units = a.units
    if units == 'auto':
        units = 'imperial' if (A['cc'] in IMPERIAL and B['cc'] in IMPERIAL) else 'metric'
    names = a.labels or [A['name'], B['name']]
    spec = {'size': a.size, 'style': a.style, 'mode': mode, 'units': units,
            'from': {'name': names[0], 'lon': round(pa[0], 6), 'lat': round(pa[1], 6)},
            'to': {'name': names[1], 'lon': round(pb[0], 6), 'lat': round(pb[1], 6)},
            'distance_m': round(dist, 1), 'duration_s': round(dur, 1),
            'route': [[round(x, 6), round(y, 6)] for x, y in thin(coords)]}
    if a.title:
        spec['title'] = a.title
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False)
    print(json.dumps({'from': A['display'], 'to': B['display'], 'mode': mode, 'distance_km': round(dist / 1000, 2),
                      'minutes': round(dur / 60), 'points': len(spec['route']), 'units': units, 'spec': a.out}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
