"""Builds israel.m3u and israel-guide.xml from iptv-org + epgshare01.

Run with no arguments to download fresh sources, or pass local files:
    python build.py [playlist.m3u] [guide.xml.gz|guide.xml]
"""
import gzip, re, sys, urllib.request
import xml.etree.ElementTree as ET

PLAYLIST_URL = "https://raw.githubusercontent.com/iptv-org/iptv/gh-pages/countries/il.m3u"
GUIDE_URL = "https://epgshare01.online/epgshare01/epg_ripper_IL1.xml.gz"

# Channels to leave out (by iptv-org tvg-id), plus whole groups.
EXCLUDE_GROUPS = {"Religious"}
EXCLUDE_IDS = {"RTGint.ru", "HalaTV.il", "i24NEWSFrench.il", "i24NEWSArabic.il"}

# Optional channel order (by tvg-id). Listed channels come first in this order;
# anything not listed follows in the original iptv-org order.
ORDER = []

# iptv-org tvg-id -> epgshare01 guide id
EPG_MAP = {
    "5Plus.il": "ספורט.5.פלוס.il", "5Stars.il": "5STARS.il", "Channel9.il": "ערוץ.9.il",
    "Channel13.il": "רשת.il", "Channel24.il": "ערוץ.24.בשידור.חי.il",
    "ComedyChannel.il": "ערוץ.ההומור.il", "GoodLife.il": "GOOD.LIFE+.il",
    "Hidabroot.il": "ערוץ.הידברות.il", "i24NEWSArabic.il": "i24NEWS.ARABIC.il",
    "i24NEWSFrench.il": "i24NEWS.FRENCH.il", "i24NEWSHebrew.il": "עברית.i24.il",
    "Kan11.il": "כאן.11.il", "KanEducational.il": "כאן.חינוכית.il", "Keshet12.il": "קשת.il",
    "KnessetChannel.il": "ערוץ.הכנסת.il", "Makan33.il": "מכאן.il",
    "Now14.il": "ערוץ.14.שידור.חי.il", "RealityChannel.il": "ערוץ.הריאליטי.il",
    "TeenNick.il": "ערוץ.TeenNick.il", "VacationChannel.il": "ערוץ.הנופש.il",
    "VivaPremium.il": "ויוה.פרימיום.il", "YamTichoni.il": "ים.תיכוני.il", "Zoom.il": "ZOOM.Toon.il",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def read_source(arg, url):
    data = open(arg, "rb").read() if arg else fetch(url)
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def parse_playlist(text):
    """Return list of channels: dict(id, group, extinf, extra_lines, url)."""
    chans, cur = [], None
    for line in text.splitlines():
        if line.startswith("#EXTINF"):
            m_id = re.search(r'tvg-id="([^"]*)"', line)
            m_gr = re.search(r'group-title="([^"]*)"', line)
            cur = {"id": (m_id.group(1) if m_id else "").split("@")[0],
                   "group": m_gr.group(1) if m_gr else "", "extinf": line, "extra": []}
        elif cur is not None and line.startswith("#"):
            cur["extra"].append(line)
        elif cur is not None and line.strip():
            cur["url"] = line.strip()
            chans.append(cur)
            cur = None
    return chans


def main():
    args = sys.argv[1:] + [None, None]
    chans = parse_playlist(read_source(args[0], PLAYLIST_URL).decode("utf-8"))
    chans = [c for c in chans if c["group"] not in EXCLUDE_GROUPS and c["id"] not in EXCLUDE_IDS]
    pos = {cid: i for i, cid in enumerate(ORDER)}
    chans.sort(key=lambda c: pos.get(c["id"], len(ORDER)))  # stable: unlisted keep original order

    out = ["#EXTM3U"]
    for c in chans:
        line = re.sub(r'\s*group-title="[^"]*"', "", c["extinf"])
        line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{c["id"]}"', line)
        out += [line, *c["extra"], c["url"]]
    open("israel.m3u", "w", encoding="utf-8").write("\n".join(out) + "\n")

    keep = {EPG_MAP[c["id"]]: c["id"] for c in chans if c["id"] in EPG_MAP}
    root = ET.fromstring(read_source(args[1], GUIDE_URL))
    new = ET.Element("tv", root.attrib)
    seen = set()
    for ch in root.findall("channel"):
        if ch.get("id") in keep and ch.get("id") not in seen:
            seen.add(ch.get("id")); ch.set("id", keep[ch.get("id")]); new.append(ch)
    n = 0
    for p in root.findall("programme"):
        if p.get("channel") in keep:
            p.set("channel", keep[p.get("channel")]); new.append(p); n += 1
    ET.indent(new)
    ET.ElementTree(new).write("israel-guide.xml", encoding="utf-8", xml_declaration=True)
    print(f"{len(chans)} channels, {len(seen)} with guide, {n} programmes")
    if len(chans) < 5 or n < 100:
        sys.exit("Sanity check failed: sources look broken, not overwriting a good build.")


if __name__ == "__main__":
    main()
