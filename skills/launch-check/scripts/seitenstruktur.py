#!/usr/bin/env python3
"""Seitenstruktur einer Website aus ihrer Sitemap: Woerter, eingehende interne Links, Titel, H1.

Aufruf:  python3 seitenstruktur.py https://example.de [--duenn 0.33] [--paare 3]

Sitemap aus den Sitemap-Zeilen der robots.txt, sonst /sitemap.xml, sonst /sitemap_index.xml
(Sitemap-Index und .gz werden gelesen). Meldet
- VERWAIST: Seite steht in der Sitemap, keine andere Seite der Sitemap verlinkt sie.
- NICHT IN SITEMAP: intern verlinkt, fehlt aber in der Sitemap (Feeds, Blaetterseiten, Dateien und
  WordPress-Technik ausgenommen; noindex-Seiten fehlen dort zu Recht).
- DUENN: Hauptinhalt unter --duenn mal dem Median der Woerter (Vorgabe ein Drittel).
- AEHNLICH: die --paare aehnlichsten Seitenpaare nach Wortschatz des Hauptinhalts (Kosinus).
Das sind Kandidaten, kein Urteil. Nur Standardbibliothek. Liest, was ein Crawler ohne JavaScript sieht.
"""
import argparse, collections, gzip, math, re, statistics, sys, urllib.error, urllib.request
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

STOP = set("""der die das den dem des ein eine einen einem einer und oder aber auch als am an auf aus bei bis
damit dann dass du er es fuer für hat haben ich ihr ihre ihren im in ist ja kann mit nach nicht noch nur ob
sie sind so um uns unser unsere vom von vor was wenn wer wie wir wird zu zum zur sich mehr sehr ueber über
the a an and or of to in on for with is are you your we our it this that""".split())

# Interne Links, die nie in eine Sitemap gehoeren: Dateien, Feeds, Blaetterseiten, WordPress-Technik.
KEIN_INHALT = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|avif|ico|pdf|docx?|xlsx?|pptx?|zip|csv|ics|mp[34]|webm|css|js|xml|txt|json)$"
    r"|/feed$|/page/\d+$|^/wp-|/wp-json|/xmlrpc\.php|/comments$|^/cdn-cgi/", re.I)
NETZFEHLER = (urllib.error.URLError, OSError, ValueError)


def hole(url):
    """Liefert (Text, End-URL nach Weiterleitungen). Kodiert rohe Umlaute in der URL, entpackt gzip."""
    url = quote(url, safe=":/?#[]@!$&'()*+,;=%~")
    req = urllib.request.Request(url, headers={"User-Agent": "seitenstruktur/1.1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        roh = r.read()
        if roh[:2] == b"\x1f\x8b":
            roh = gzip.decompress(roh)
        return roh.decode(r.headers.get_content_charset() or "utf-8", "replace"), r.geturl()


def schluessel(url):
    """Vergleichsschluessel einer internen Seite: dekodierter Pfad, klein, ohne index.html und End-Schraegstrich."""
    pfad = unquote(urlsplit(url).path or "/").lower()
    pfad = re.sub(r"/index\.(html?|php)$", "/", pfad)
    pfad = re.sub(r"^/collections/[^/]+(/products/)", r"\1", pfad)  # Shopify: Produkt ueber Collection
    return pfad.rstrip("/") or "/"


def ohne_www(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


class Seite(HTMLParser):
    AUSSEN = {"nav", "header", "footer"}  # ausserhalb von <main> kein Inhalt
    IMMER_RAUS = {"nav", "footer", "script", "style", "noscript", "template", "svg"}  # auch in <main> nicht

    def __init__(self):
        super().__init__()
        self.links, self.titel, self.h1, self.basis = [], "", [], None
        self.haupt, self.rest = [], []
        self._offen = []  # offene Elemente, die den Text steuern
        self._feld = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "base" and a.get("href") and self.basis is None:
            self.basis = a["href"]
        if "svg" not in self._offen and (tag == "h1" or (tag == "title" and not self.titel)):
            self._feld = tag
            if tag == "h1":
                self.h1.append("")
        if tag == "main" or tag in self.AUSSEN or tag in self.IMMER_RAUS:
            self._offen.append(tag)

    def handle_endtag(self, tag):
        if tag == self._feld:
            self._feld = None
        if tag in self._offen:  # schliesst auch vergessene innere Elemente (<nav> ohne </nav>)
            while self._offen and self._offen.pop() != tag:
                pass

    def handle_data(self, data):
        if self._feld == "title":
            self.titel += data
        elif self._feld == "h1":
            self.h1[-1] += data
        if any(t in self.IMMER_RAUS for t in self._offen):
            return
        if "main" in self._offen:
            self.haupt.append(data)
        elif not any(t in self.AUSSEN for t in self._offen):
            self.rest.append(data)

    def text(self):
        return " ".join(self.haupt) if self.haupt else " ".join(self.rest)


def lies_sitemaps(start):
    """Liest Sitemaps samt Index rekursiv. Liefert (Seiten-URLs, ob ueberhaupt eine lesbar war)."""
    urls, offen, gesehen, gelesen = [], list(reversed(start)), set(), False
    while offen:
        sm = offen.pop()
        if sm in gesehen:
            continue
        gesehen.add(sm)
        try:
            xml, _ = hole(sm)
        except NETZFEHLER as e:
            print(f"HINWEIS: Sitemap {sm} nicht lesbar ({e})")
            continue
        if "<urlset" not in xml and "<sitemapindex" not in xml:
            continue
        gelesen = True
        locs = [x.replace("&amp;", "&") for x in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)]
        if "<sitemapindex" in xml:
            offen += reversed(locs)
        else:
            urls += locs
    return urls, gelesen


def sitemap_urls(basis):
    try:
        robots, _ = hole(urljoin(basis, "/robots.txt"))
        aus_robots = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
    except NETZFEHLER:
        aus_robots = []
    versuche = [aus_robots] if aus_robots else []
    versuche += [[urljoin(basis, "/sitemap.xml")], [urljoin(basis, "/sitemap_index.xml")]]
    for start in versuche:
        urls, gelesen = lies_sitemaps(start)
        if gelesen:
            return urls
    sys.exit("Keine Sitemap gefunden (robots.txt, /sitemap.xml, /sitemap_index.xml). Erst Abschnitt A.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--duenn", type=float, default=0.33, help="Anteil am Median, darunter DUENN")
    ap.add_argument("--paare", type=int, default=3, help="so viele aehnlichste Paare zeigen")
    arg = ap.parse_args()
    basis = arg.url.rstrip("/") + "/"
    b = urlsplit(basis)

    roh = sitemap_urls(basis)
    fremd = sorted({urlsplit(u).netloc for u in roh if ohne_www(urlsplit(u).netloc) != ohne_www(b.netloc)})
    if fremd:
        print(f"HINWEIS: Sitemap nennt Host {', '.join(fremd)}, geprueft wird {b.netloc}")
    sm, gesehen = [], set()
    for u in roh:
        n = urlunsplit((b.scheme, b.netloc, urlsplit(u).path or "/", "", ""))
        if schluessel(n) not in gesehen:
            gesehen.add(schluessel(n))
            sm.append(n)

    # Wohin fuehrt "/"? (Mehrsprachig: / -> /de/). Links auf / zaehlen dann fuer das Ziel.
    try:
        start_ziel = schluessel(hole(basis)[1])
    except NETZFEHLER:
        start_ziel = "/"

    daten, eingehend, verlinkt = {}, collections.defaultdict(set), set()
    for u in sm:
        try:
            html, ende = hole(u)
            p = Seite()
            p.feed(html)
        except NETZFEHLER as e:
            print(f"FEHLER {unquote(urlsplit(u).path)}: {e}")
            continue
        worte = re.findall(r"\w+", p.text().lower())
        daten[u] = (p.titel.strip(), " | ".join(h.strip() for h in p.h1), worte)
        bezug = urljoin(ende, p.basis) if p.basis else ende  # relative Links gegen die End-URL
        for h in p.links:
            z = urljoin(bezug, h.strip())
            if urlsplit(z).scheme not in ("http", "https") or ohne_www(urlsplit(z).netloc) != ohne_www(b.netloc):
                continue
            k = schluessel(z)
            if k == "/":
                k = start_ziel
            verlinkt.add(k)
            if k not in (schluessel(u), schluessel(ende)):
                eingehend[k].add(u)

    if not daten:
        sys.exit("Keine Seite lesbar.")

    def zeige(u):
        return unquote(urlsplit(u).path or "/")

    median = statistics.median(len(w) for _, _, w in daten.values())
    print(f"{len(daten)} Seiten aus der Sitemap, Median {median:.0f} Woerter im Hauptinhalt\n")
    print("Woerter | eingehend | URL | Titel | H1")
    for u, (t, h, w) in daten.items():
        print(f"{len(w):7} | {len(eingehend[schluessel(u)]):9} | {zeige(u)} | {t} | {h}")

    print()
    for u in daten:
        k = schluessel(u)
        if not eingehend[k] and k not in ("/", start_ziel):
            print(f"VERWAIST: {zeige(u)} (keine andere Seite verlinkt sie)")
    for k in sorted(verlinkt - {schluessel(u) for u in sm} - {"/", start_ziel}):
        if not KEIN_INHALT.search(k):
            print(f"NICHT IN SITEMAP: {k}")
    for u, (_, _, w) in daten.items():
        if len(w) < arg.duenn * median:
            print(f"DUENN: {zeige(u)} ({len(w)} Woerter, Median {median:.0f})")

    vek = {u: collections.Counter(x for x in w if x not in STOP and len(x) > 2 and not x.isdigit())
           for u, (_, _, w) in daten.items()}

    def kos(a, c):
        z = sum(a[k] * c[k] for k in a.keys() & c.keys())
        n = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in c.values()))
        return z / n if n else 0.0

    us = [u for u in daten if sum(vek[u].values()) >= 50]
    paare = sorted(((kos(vek[x], vek[y]), x, y) for i, x in enumerate(us) for y in us[i + 1:]), reverse=True)
    for s, x, y in paare[: arg.paare]:
        print(f"AEHNLICH: {s:.2f}  {zeige(x)}  <->  {zeige(y)}")


if __name__ == "__main__":
    main()
