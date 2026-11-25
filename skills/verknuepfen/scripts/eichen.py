"""Eichung der Schwelle fuer Schritt 4 (semantische Nachbarn). Liest eine Paarliste, fragt je Paar den
Kosinus-Score ueber qmd ab und schlaegt die Schwelle mit den wenigsten Fehlern vor. Schreibt nichts.

    python3 -I eichen.py [--vault V] [--einstellungen DATEI] PAARLISTE.md

Paarliste: Zeilen "- [[A]] | [[B]] | verwandt" bzw. "nicht"; andere Zeilen zaehlen nicht. A und B sind
Vault-Pfade ohne .md oder eindeutige Namen. Gewertet wird wie in nachbarn(): score >= Schwelle ist verwandt.
"""
import argparse
import math
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I kennt das Skriptverzeichnis nicht
import nachbarn as nb  # noqa: E402
import verknuepfen as vk  # noqa: E402

# Gemessen 17.11.2026: das Minimum der Top 50 lag bei rund 0,48, die Haelfte der echten Paare bekam 0,0.
# Mit 2000 liefert qmd alle Dokumente ab rund 0,30 (1,9 s je Abfrage).
EICH_N = 2000
PAAR = re.compile(r"^\s*-\s+\[\[([^\[\]]+)\]\]\s*\|\s*\[\[([^\[\]]+)\]\]\s*\|\s*(.*?)\s*$")
KLASSEN = {"verwandt": True, "nicht": False}


def fehler(werte, schwelle):
    """Verwandte unter der Schwelle plus nicht verwandte auf oder ueber ihr (Regel: nb.ueber_schwelle)."""
    return sum(1 for s, verwandt in werte if nb.ueber_schwelle(s, schwelle) != verwandt)


def _auf_raster(mitte, lo, hi):
    """Mitte auf zwei Stellen; liegt der gerundete Wert ausserhalb von (lo, hi], der Nachbar im Raster."""
    s = round(mitte, 2)
    if s <= lo:
        s = round(s + 0.01, 2)
    if s > hi:
        s = round(s - 0.01, 2)
    return s


def schwelle_waehlen(werte):
    """Schwelle mit den wenigsten Fehlern; bei Gleichstand die Mitte des breitesten Bereichs, zwei Stellen.
    Bereiche liegen zwischen benachbarten Scores, an den Raendern bis 0 und 1 (Kosinus). Die Fehler werden an
    der gerundeten Schwelle gezaehlt, damit das Runden keinen Wert auf die falsche Seite schiebt."""
    werte = [(float(s), bool(v)) for s, v in werte]
    if not werte:
        raise ValueError("keine Paare")
    if len({v for _, v in werte}) < 2:
        raise ValueError("Paarliste braucht verwandte und nicht verwandte Paare (nur eine Klasse)")
    scores = sorted({s for s, _ in werte})
    kandidaten = []
    for lo, hi in zip(scores, scores[1:]):
        s = _auf_raster((lo + hi) / 2, lo, hi)
        kandidaten.append((fehler(werte, s), -(hi - lo), s))
    # Raender: alles verwandt (Schwelle <= kleinster Score) und nichts verwandt (Schwelle > groesster Score).
    # Breite bis 0 bzw. 1 (Kosinus); liegt der Score schon dort, Breite 0 und der naechste Rasterwert.
    if scores[0] > 0.0:
        unten = _auf_raster(scores[0] / 2, 0.0, scores[0])
    else:
        unten = math.floor(round(scores[0] * 100, 6)) / 100
    kandidaten.append((fehler(werte, unten), -max(scores[0], 0.0), unten))
    if scores[-1] < 1.0:
        oben = _auf_raster((scores[-1] + 1.0) / 2, scores[-1], 1.0)
    else:
        oben = round(math.floor(round(scores[-1] * 100, 6)) / 100 + 0.01, 2)
        while oben <= scores[-1]:
            oben = round(oben + 0.01, 2)
    kandidaten.append((fehler(werte, oben), -max(1.0 - scores[-1], 0.0), oben))
    return min(kandidaten)[2]


def paare_lesen(text, warnungen=None):
    """[(A, B, verwandt)] in NFC, in Reihenfolge der Liste. Zeilen im Paarformat mit anderer Klasse als
    verwandt/nicht landen als "unbekannte Klasse: ..." in warnungen (falls uebergeben)."""
    res = []
    for zeile in unicodedata.normalize("NFC", text).splitlines():
        m = PAAR.match(zeile)
        if not m:
            continue
        if m.group(3) not in KLASSEN:
            if warnungen is not None:
                warnungen.append("unbekannte Klasse: %s" % zeile.strip())
            continue
        res.append((m.group(1).strip(), m.group(2).strip(), KLASSEN[m.group(3)]))
    return res


def score_paar(v, a, b, einst, runner=nb.qmd_runner):
    """Bester Score von b unter den Vektortreffern zum Text von a (n=EICH_N), 0.0 wenn b nicht dabei ist.
    Umgeht die Schwelle-Sperre von nachbarn() absichtlich; die YAML-Pruefung macht der Aufrufer."""
    g = einst["graph"]
    abfrage = nb.abfrage_text(v.texts[a])
    if not abfrage:
        raise nb.NachbarnFehler("Notiz ohne Text: %s" % a)
    treffer = nb.vsearch_lesen(runner(g["qmd_index"], abfrage, g["qmd_frist"], n=EICH_N), v.root)
    b = unicodedata.normalize("NFC", b)
    return max((s for r, s, _ in treffer if r == b), default=0.0)


def aufloesen(v, ziel, muster):
    """(rel, None) oder (None, Grund). Mehrdeutige Namen ohne Pfad werden nicht geraten."""
    # wie Resolver.resolve: Alias, Anker und fuehrender Schraegstrich zaehlen nicht zum Namen
    stamm = re.split(r"[#^]", ziel.split("|", 1)[0], maxsplit=1)[0].strip().lower().lstrip("/")
    if stamm.endswith(".md"):
        stamm = stamm[:-3]
    if "/" not in stamm and len(v.resolver.by_stem.get(stamm, [])) > 1:
        return None, "mehrdeutig: %s" % ziel
    rel = v.resolver.resolve(ziel, "")
    if rel is None or rel not in v.texts:
        return None, "Notiz fehlt: %s" % ziel
    if nb.ist_ausgeschlossen(rel, muster):
        return None, "vom Vektorindex ausgeschlossen: %s" % ziel
    if not nb.abfrage_text(v.texts[rel]):
        return None, "Notiz ohne Text: %s" % ziel
    return rel, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Schwelle fuer semantische Nachbarn eichen (schreibt nichts).")
    ap.add_argument("--vault", default=None, help="Vorgabe: Einstellung vault")
    ap.add_argument("--einstellungen", help="Einstellungsdatei statt der Vorgabe")
    ap.add_argument("paarliste", metavar="PAARLISTE.md")
    a = ap.parse_args(argv)
    try:
        vk.vl.einstellungen_vorab_pruefen()
        vault = vk.vl.vault_waehlen(a.vault)
    except vk.vl.EinstellungsFehler as ex:
        print(ex, file=sys.stderr)
        return 2
    if not os.path.isdir(vault):
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    grund = nb.python_grund()
    if grund:
        print("Eichung nicht möglich: %s" % grund, file=sys.stderr)
        return 1
    if a.einstellungen is not None and not os.path.isfile(os.path.expanduser(a.einstellungen)):
        print("Einstellungsdatei nicht gefunden: %s" % a.einstellungen, file=sys.stderr)
        return 1
    einst = nb.einstellungen_laden(a.einstellungen)
    for w in einst["warnungen"]:
        print("Warnung: %s" % w, file=sys.stderr)
    g = einst["graph"]
    grund = nb.yaml_grund(einst)
    if grund:
        print("Eichung nicht möglich: %s (%s)" % (grund, nb.qmd_yaml_pfad(g["qmd_index"])), file=sys.stderr)
        return 1
    warnungen = []
    try:
        with open(os.path.expanduser(a.paarliste), encoding="utf-8") as fh:
            paare = paare_lesen(fh.read(), warnungen)
    except (OSError, ValueError) as ex:
        print("Paarliste nicht lesbar: %s" % ex, file=sys.stderr)
        return 1
    for w in warnungen:
        print(w, file=sys.stderr)
    v = vk.load_vault(vault)
    muster = g.get("ausschluss", [])
    werte = []
    for name_a, name_b, verwandt in paare:
        rel_a, grund = aufloesen(v, name_a, muster)
        rel_b, grund_b = (None, None) if grund else aufloesen(v, name_b, muster)
        if grund or grund_b:
            print("übersprungen: %s (%s | %s)" % (grund or grund_b, name_a, name_b))
            continue
        try:
            s = score_paar(v, rel_a, rel_b, einst, runner=nb.qmd_runner)
        except nb.NachbarnFehler as ex:
            print("Eichung abgebrochen: %s" % ex, file=sys.stderr)
            return 1
        werte.append((s, verwandt))
        print("%.3f %s %s | %s" % (s, "verwandt" if verwandt else "nicht", name_a, name_b))
    if werte and all(s == 0.0 for s, _ in werte):
        print("Keine Schwelle: alle Scores 0 – Index passt nicht zum Vault?", file=sys.stderr)
        return 1
    try:
        schwelle = schwelle_waehlen(werte)
    except ValueError as ex:
        print("Keine Schwelle: %s" % ex, file=sys.stderr)
        return 1
    k = len(werte) - fehler(werte, schwelle)
    print("Schwelle: %.2f" % schwelle)
    print("Trefferquote: %d/%d (%.0f %%)" % (k, len(werte), 100.0 * k / len(werte)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
