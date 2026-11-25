"""Tests fuer vault_lint.py. Jeder Test baut sich einen Wegwerf-Vault.

    python3 -I -m unittest discover -s ~/.claude/skills/lint/scripts
"""
import atexit
import contextlib
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

# Vorspann VOR dem Import: HOME und Einstellungsdatei zeigen in einen Wegwerf-Ordner, damit weder
# ein Test noch eine Mutation die echte Konfiguration oder den echten Vault liest. Subprozesse erben
# os.environ und damit diese Werte.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="vault-lint-home-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import vault_lint as vl  # noqa: E402

HEUTE = datetime.date(2026, 10, 15)
DIENST = "02 Projekte/Dienst"


@contextlib.contextmanager
def mit_einstellungen(**werte):
    """Temp-Einstellungsdatei mit diesen Werten, per CLAUDE_SKILLS_EINSTELLUNGEN aktiv."""
    d = tempfile.mkdtemp(prefix="vault-lint-einst-")
    try:
        pfad = os.path.join(d, "einstellungen.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(werte, fh)
        with mock.patch.dict(os.environ, {"CLAUDE_SKILLS_EINSTELLUNGEN": pfad}):
            yield pfad
    finally:
        shutil.rmtree(d, ignore_errors=True)
FM = "---\ntags: [test]\nsource: claude\n---\n"


def projekt(name, hub_fm="status: aktiv\nphase: umsetzung\naktualisiert: 2026-10-10\n", hub_body="", ordner="02 Projekte"):
    base = f"{ordner}/{name}"
    files = {
        f"{base}/{name} - PMO HUB.md": f"---\ntags: [p]\n{hub_fm}---\n# {name}\n{hub_body}",
        f"{base}/Projekt-Governance.md": FM,
    }
    for sub in vl.PROJECT_SUBDIRS:
        files[f"{base}/{sub}/.keep"] = ""
    return files


class VaultTest(unittest.TestCase):
    def bau(self, files):
        d = tempfile.mkdtemp(prefix="vault-lint-test-")
        self.addCleanup(shutil.rmtree, d)
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(content)
        return vl.analyse(d, HEUTE)


class Orphans(VaultTest):
    def test_punkt_im_namen_ist_keine_dateiendung(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "[[Handoff Build 1.4.0]] und [[Live-Check terminplaner-app.de]]\n",
            "03 Bereiche/A/Handoff Build 1.4.0.md": FM,
            "03 Bereiche/A/Live-Check terminplaner-app.de.md": FM,
        })
        self.assertNotIn("03 Bereiche/A/Handoff Build 1.4.0.md", r["orphans"])
        self.assertNotIn("03 Bereiche/A/Live-Check terminplaner-app.de.md", r["orphans"])
        self.assertEqual(r["broken_links"], {})

    def test_echte_dateiendung_wird_aufgeloest(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "![[bild.png]] [[Tabelle.base]]\n",
            "07 Anhaenge/bild.png": "x",
            "Tabelle.base": "views: []\n",
        })
        self.assertEqual(r["broken_links"], {})

    def test_link_in_code_zaehlt_nicht(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "Inline `[[Ziel]]`\n\n```\n[[Ziel]]\n```\n",
            "03 Bereiche/A/Ziel.md": FM,
        })
        self.assertIn("03 Bereiche/A/Ziel.md", r["orphans"])

    def test_index_und_report_retten_keine_waise(self):
        r = self.bau({
            "Index.md": FM + "[[Nur im Index]]\n",
            "Lint-Reports/2026-10-15 Vault Lint Report.md": FM + "[[Nur im Report]]\n",
            "log.md": "[[Im Log]] [[2026-10-15 Vault Lint Report]]\n",
            "03 Bereiche/A/Nur im Index.md": FM,
            "03 Bereiche/A/Nur im Report.md": FM,
            "03 Bereiche/A/Im Log.md": FM,
        })
        self.assertIn("03 Bereiche/A/Nur im Index.md", r["orphans"])
        self.assertIn("03 Bereiche/A/Nur im Report.md", r["orphans"])
        self.assertNotIn("03 Bereiche/A/Im Log.md", r["orphans"])
        self.assertNotIn("Lint-Reports/2026-10-15 Vault Lint Report.md", r["orphans"])

    def test_info_string_schliesst_keinen_codeblock(self):
        # Wie Obsidian: ```dataview kann einen ```markdown-Block nicht schliessen.
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "```markdown\n[[Drinnen]]\n```dataview\nx\n```\n- [[Draussen]]\n```\ncode\n```\n",
            "03 Bereiche/A/Drinnen.md": FM,
            "03 Bereiche/A/Draussen.md": FM,
        })
        self.assertIn("03 Bereiche/A/Drinnen.md", r["orphans"])
        self.assertNotIn("03 Bereiche/A/Draussen.md", r["orphans"])

    def test_inline_code_mit_doppelten_backticks(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "Inline: `` `code` ``, `**fett**`, Links `[text](url)` und `[[Nix]]`, echt [[Ziel]]\n",
            "03 Bereiche/A/Ziel.md": FM,
        })
        self.assertEqual(r["broken_links"], {})
        self.assertNotIn("03 Bereiche/A/Ziel.md", r["orphans"])

    def test_markdown_link_ohne_endung_ist_notizlink(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "[Tool](url) [Web](https://example.org) [Hier](#abschnitt) [Ziel](Ziel)\n",
            "03 Bereiche/A/Ziel.md": FM,
        })
        self.assertEqual(r["broken_links"], {"03 Bereiche/A/Quelle.md": [{"link": "url", "line": 5}]})
        self.assertNotIn("03 Bereiche/A/Ziel.md", r["orphans"])

    def test_pfadlink_mit_alias_und_abschnitt(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "[[Paket/README|Paket]] [[Ziel#Abschnitt|x]] [[Ziel2^block]]\n",
            "04 Ressourcen/Research/Paket/README.md": FM,
            "03 Bereiche/A/Ziel.md": FM,
            "03 Bereiche/A/Ziel2.md": FM,
        })
        for p in ("04 Ressourcen/Research/Paket/README.md", "03 Bereiche/A/Ziel.md", "03 Bereiche/A/Ziel2.md"):
            self.assertNotIn(p, r["orphans"])

    def test_markdown_link_und_frontmatter_link_zaehlen(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": "---\ntags: [t]\nprojekt: \"[[Fm Ziel]]\"\n---\n[Text](Md%20Ziel.md)\n",
            "03 Bereiche/A/Md Ziel.md": FM,
            "03 Bereiche/A/Fm Ziel.md": FM,
        })
        self.assertNotIn("03 Bereiche/A/Md Ziel.md", r["orphans"])
        self.assertNotIn("03 Bereiche/A/Fm Ziel.md", r["orphans"])

    def test_ausnahmen(self):
        r = self.bau({
            "05 Daily Notes/2026-10-15.md": "kein frontmatter\n",
            "00 Kontext/Branding.md": FM,
            "03 Bereiche/Planung/Planung.md": FM,
            "Briefings/2026-10-15.md": "maschine\n",
            "Agentic OS Tasks.md": "- [ ] x\n",
            "memory/regel.md": "---\nname: regel\n---\n",
            "06 Archiv/Alt.md": FM,
            "CLAUDE.md": "x\n",
            "AGENTS.md": "x\n",
        })
        self.assertEqual(r["orphans"], [])
        self.assertNotIn("Briefings/2026-10-15.md", r["no_frontmatter"])
        self.assertNotIn("Agentic OS Tasks.md", r["no_frontmatter"])
        self.assertNotIn("memory/regel.md", r["no_tags"])
        self.assertIn("05 Daily Notes/2026-10-15.md", r["no_frontmatter"])

    def test_frag_dateien_und_archiv_ohne_frontmatter_pruefung(self):
        r = self.bau({
            "03 Bereiche/Studio/Lauf/frag_liq.md": "| a | b |\n",
            "03 Bereiche/Studio/Lauf/fragment.md": "kein frontmatter\n",
            "06 Archiv/Sicherung/MEMORY.md": "- [Regel](regel.md)\n",
            "06 Archiv/Sicherung/regel.md": "---\nname: regel\n---\n",
        })
        # frag_*.md: Tabellenstuecke fuer die Montage, weder Waise noch Frontmatter-Fund
        self.assertNotIn("03 Bereiche/Studio/Lauf/frag_liq.md", r["orphans"])
        self.assertNotIn("03 Bereiche/Studio/Lauf/frag_liq.md", r["no_frontmatter"])
        # ohne Unterstrich gilt die Ausnahme nicht
        self.assertIn("03 Bereiche/Studio/Lauf/fragment.md", r["orphans"])
        self.assertIn("03 Bereiche/Studio/Lauf/fragment.md", r["no_frontmatter"])
        # 06 Archiv/: Sicherungen bleiben bytegleich, kein Frontmatter- oder tags-Fund
        self.assertNotIn("06 Archiv/Sicherung/MEMORY.md", r["no_frontmatter"])
        self.assertNotIn("06 Archiv/Sicherung/regel.md", r["no_tags"])

    def test_erwaehnung_ohne_link_wird_gemeldet(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "Entwurf liegt in `assets/2026-10-14 AV-Vertrag Entwurf.md`\n",
            "03 Bereiche/A/assets/2026-10-14 AV-Vertrag Entwurf.md": FM,
        })
        hits = r["mentions"]["03 Bereiche/A/assets/2026-10-14 AV-Vertrag Entwurf.md"]
        self.assertEqual(hits[0]["source"], "03 Bereiche/A/Quelle.md")
        self.assertEqual(hits[0]["line"], 5)

    def test_generischer_name_sucht_den_ordner(self):
        r = self.bau({
            "03 Bereiche/A/Quelle.md": FM + "Material in `Research/2026-10-12 Store-Auftritt/`\n",
            "04 Ressourcen/Research/2026-10-12 Store-Auftritt/README.md": FM,
        })
        hits = r["mentions"]["04 Ressourcen/Research/2026-10-12 Store-Auftritt/README.md"]
        self.assertEqual([h["source"] for h in hits], ["03 Bereiche/A/Quelle.md"])


class Projekte(VaultTest):
    def test_sauberes_projekt_ohne_befund(self):
        files = projekt("Alpha")
        files["02 Projekte/Alpha/Fehlerlog.md"] = FM
        files["02 Projekte/Alpha/Financials.md"] = FM
        r = self.bau(files)
        p = r["projects"]["02 Projekte/Alpha"]
        self.assertEqual(p["whitelist_violations"], [])
        self.assertEqual(p["missing"], [])
        self.assertEqual(p["missing_subdirs"], [])

    def test_readme_im_wurzel_ist_verstoss(self):
        files = projekt("Alpha")
        files["02 Projekte/Alpha/README.md"] = FM
        files["02 Projekte/Alpha/notizen.md"] = FM
        r = self.bau(files)
        p = r["projects"]["02 Projekte/Alpha"]
        self.assertEqual(p["whitelist_violations"], ["README.md", "notizen.md"])
        self.assertTrue(p["readme"])

    def test_container_prueft_nur_die_unterprojekte(self):
        files = projekt("Sub1", ordner="02 Projekte/_Kunde")
        files["02 Projekte/_Kunde/Sub2/Sub2 - PMO HUB.md"] = FM
        r = self.bau(files)
        self.assertEqual(r["containers"], [{"name": "_Kunde", "subprojects": ["Sub1", "Sub2"]}])
        self.assertNotIn("02 Projekte/_Kunde", r["projects"])
        self.assertEqual(r["projects"]["02 Projekte/_Kunde/Sub1"]["missing"], [])
        self.assertEqual(r["projects"]["02 Projekte/_Kunde/Sub2"]["missing"], ["Projekt-Governance.md"])

    def test_altes_hub_schema_ist_naming_befund(self):
        files = projekt("Alpha")
        del files["02 Projekte/Alpha/Alpha - PMO HUB.md"]
        files["02 Projekte/Alpha/Alpha - Hub.md"] = FM
        r = self.bau(files)
        p = r["projects"]["02 Projekte/Alpha"]
        self.assertEqual(p["naming"], [{"file": "Alpha - Hub.md", "suggest": "Alpha - PMO HUB.md"}])
        self.assertEqual(p["missing"], ["PMO HUB"])
        self.assertEqual(p["whitelist_violations"], [])

    def test_kaputter_hublink_mit_zeile(self):
        r = self.bau(projekt("Alpha", hub_body="\n- [[Gibt es nicht]]\n"))
        hub = r["projects"]["02 Projekte/Alpha"]["hubs"]["Alpha - PMO HUB.md"]
        self.assertEqual(hub["broken"], [{"link": "Gibt es nicht", "line": 9}])

    def test_pre_backlog_als_absatz_und_veraltet(self):
        body = ("\n## Backlog\n\nKein Tool. Pre-Backlog Action Items:\n\n- [ ] eins\n- [x] erledigt\n- [ ] zwei\n"
                "\n## Notizen\n\n- [ ] gehoert nicht dazu\n")
        r = self.bau(projekt("Alpha", hub_fm="status: aktiv\naktualisiert: 2026-09-01\n", hub_body=body))
        hub = r["projects"]["02 Projekte/Alpha"]["hubs"]["Alpha - PMO HUB.md"]
        self.assertEqual(hub["pre_backlog_open"], 2)
        self.assertEqual(hub["age_days"], 44)
        self.assertTrue(hub["pre_backlog_stale"])

    def test_markdown_in_assets(self):
        files = projekt("Alpha")
        files["02 Projekte/Alpha/Research/assets/notiz.md"] = FM
        files["02 Projekte/Alpha/assets/entwurf.md"] = FM
        r = self.bau(files)
        md = r["projects"]["02 Projekte/Alpha"]["md_in_assets"]
        self.assertEqual(md, [{"path": "02 Projekte/Alpha/Research/assets/notiz.md", "research": True},
                              {"path": "02 Projekte/Alpha/assets/entwurf.md", "research": False}])

    def test_decisions_frontmatter(self):
        files = projekt("Alpha")
        files["02 Projekte/Alpha/Decisions/D1.md"] = "---\ntype: entscheidung\nstatus: entschieden\nentschieden_am:\n---\n"
        files["02 Projekte/Alpha/Decisions/D2.md"] = "---\ntype: entscheidung\nstatus: entschieden\nentschieden_am: 2026-10-01\n---\n"
        files["02 Projekte/Alpha/Decisions/D3.md"] = "---\nstatus: offen\n---\n"
        r = self.bau(files)
        dec = r["projects"]["02 Projekte/Alpha"]["decisions"]
        self.assertEqual(dec, [{"path": "02 Projekte/Alpha/Decisions/D1.md", "problems": ["entschieden_am leer"]},
                               {"path": "02 Projekte/Alpha/Decisions/D3.md", "problems": ["type fehlt oder nicht entscheidung"]}])

    def test_abgeschlossenes_projekt_und_index(self):
        files = projekt("Alt", hub_fm="status: abgeschlossen\naktualisiert: 2026-08-01\n")
        files.update(projekt("Neu", hub_fm="status: aktiv\nphase: konzeption\naktualisiert: 2026-10-14\n"))
        files.update(projekt("Mitte", hub_fm="status: aktiv\nphase: umsetzung\naktualisiert: 2026-10-02\n"))
        r = self.bau(files)
        self.assertEqual(r["closed_projects"], ["02 Projekte/Alt"])
        self.assertEqual([p["hub"] for p in r["index"]["projects_active"]],
                         ["Neu - PMO HUB", "Mitte - PMO HUB"])


class Hygiene(VaultTest):
    def test_inbox_wurzel_und_bereiche(self):
        r = self.bau({
            "01 Inbox/a.md": FM, "01 Inbox/b.md": FM,
            "Unbenannt.base": "views: []\n",
            "HANDOFF-x.md": FM,
            "CLAUDE.md": "x",
            "03 Bereiche/Ohne/Notiz.md": FM,
            "03 Bereiche/Mit/Mit - Uebersicht.md": FM,
            "04 Ressourcen/Themen/Seite.md": FM,
        })
        self.assertEqual(r["inbox"], ["01 Inbox/a.md", "01 Inbox/b.md"])
        self.assertEqual(r["root_strays"], ["HANDOFF-x.md", "Unbenannt.base"])
        self.assertEqual({b["name"]: b["start"] for b in r["index"]["bereiche"]},
                         {"Mit": "Mit - Uebersicht", "Ohne": None})
        self.assertEqual(r["synthesis_missing"], ["Themen"])


TESTDATEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdaten")
ENT = "04 Ressourcen/Entitäten"


def ent(typ, extra=""):
    return f"---\ntags: [entitaet]\ntype: {typ}\n{extra}---\n# Notiz\n"


class Graph(VaultTest):
    def test_fm_list_formen(self):
        self.assertEqual(vl.fm_list("a: []\nb: x", "a"), [])
        self.assertEqual(vl.fm_list('a: ["[[X]]", "y, z"]', "a"), ["[[X]]", "y, z"])
        self.assertEqual(vl.fm_list('a:\n  - "[[X]]"\n  - [[Y]]\nb: 1', "a"), ["[[X]]", "[[Y]]"])
        self.assertEqual(vl.fm_list("a:\n  - x\nb:\n  - y", "a"), ["x"])
        self.assertEqual(vl.fm_list("a: [[[X, Y]], 'b']", "a"), ["[[X, Y]]", "b"])
        self.assertEqual(vl.fm_list('a: "[[X]]"', "a"), ["[[X]]"])
        self.assertIsNone(vl.fm_list("b: 1", "a"))
        self.assertIsNone(vl.fm_list(None, "a"))

    def test_fm_end_line(self):
        self.assertEqual(vl.fm_end_line("---\na: 1\nb: 2\n---\nText\n"), 4)
        self.assertEqual(vl.fm_end_line("Text\n---\n"), 0)

    def test_entitaeten_register(self):
        r = self.bau({
            f"{ENT}/Kappa.md": ent("werkzeug", 'aliases: ["Kappa Tool", "kappa"]\n'),
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt"),
            f"{ENT}/_Vorlage Entität.md": ent(""),
            f"{ENT}/_Muster.md": ent("person"),
            "03 Bereiche/A/Spec.md": FM + "Beispiel:\n\n```yaml\n---\ntype: firma\n---\n```\n\ntype: firma\n",
        })
        e = r["graph"]["entities"]
        self.assertEqual(set(e), {f"{ENT}/Kappa.md", "02 Projekte/Omega/Omega - PMO HUB.md"})
        self.assertEqual(e["02 Projekte/Omega/Omega - PMO HUB.md"],
                         {"type": "projekt", "names": ["Omega - PMO HUB", "Omega"]})
        self.assertEqual(e[f"{ENT}/Kappa.md"], {"type": "werkzeug", "names": ["Kappa", "Kappa Tool"]})
        self.assertEqual(r["graph"]["L4"], [])

    def test_l3_fehlervault(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L3", "fehler"), HEUTE)
        self.assertEqual(r["graph"]["L3"], [{"from": f"{ENT}/Sigma Muster.md", "to": f"{ENT}/Rho GmbH.md", "line": 8}])

    def test_l3_sauber(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L3", "sauber"), HEUTE)
        self.assertEqual(len(r["graph"]["entities"]), 2)
        self.assertEqual(r["graph"]["L3"], [])

    def test_l3_frontmatter(self):
        # Link nur im Frontmatter: kein Fund; B kennt A nur per Frontmatter: kein Fund
        r = self.bau({
            f"{ENT}/Sigma.md": ent("person", 'kunde_von: ["[[Omega - PMO HUB]]"]\n'),
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt"),
        })
        self.assertEqual(r["graph"]["L3"], [])
        r = self.bau({
            f"{ENT}/Sigma.md": ent("person") + "Siehe [[Omega - PMO HUB]].\n",
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt", 'entschieden_in: ["[[Sigma]]"]\n'),
        })
        self.assertEqual(r["graph"]["L3"], [])
        # Gegenprobe: ohne Rueckverweis ein Fund, Zeile des ersten Links, ein Fund je Paar
        r = self.bau({
            f"{ENT}/Sigma.md": ent("person") + "\n[[Omega - PMO HUB]]\nnochmal [[Omega - PMO HUB]]\n",
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt"),
        })
        self.assertEqual(r["graph"]["L3"], [{"from": f"{ENT}/Sigma.md", "to": "02 Projekte/Omega/Omega - PMO HUB.md",
                                             "line": 7}])
        # Selbstlink ist kein Fund
        r = self.bau({f"{ENT}/Sigma.md": ent("person") + "[[Sigma]]\n"})
        self.assertEqual(r["graph"]["L3"], [])

    def test_l3_zeile_markdownlink_vor_wikilink(self):
        r = self.bau({
            f"{ENT}/Sigma.md": ent("person") + "\n[B](Omega%20-%20PMO%20HUB.md)\n\n[[Omega - PMO HUB]]\n",
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt"),
        })
        self.assertEqual([f["line"] for f in r["graph"]["L3"]], [7])

    def test_l3_beide_enden_entitaeten(self):
        r = self.bau({
            f"{ENT}/Sigma.md": ent("person") + "[[Normal]]\n",
            "03 Bereiche/A/Normal.md": FM + "Text\n",
            "03 Bereiche/A/Quelle.md": FM + "[[Sigma]]\n",
        })
        self.assertEqual(r["graph"]["L3"], [])

    def test_l5_typfilter(self):
        d = DIENST
        with mit_einstellungen(dienst_ordner=DIENST):
            r = self.bau({
                f"{ENT}/Fa.md": ent("firma") + f"[[Dienst A]]\n",
                "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt") + "[[Dienst A]]\n",
                f"{ENT}/Kappa.md": ent("werkzeug") + "[[Dienst A]]\n",
                f"{d}/Dienst A.md": FM + "[[Fa]] [[Omega - PMO HUB]] [[Kappa]]\n",
                f"{d}/Fb.md": ent("firma"),
                f"{d}/Pb - PMO HUB.md": ent("projekt"),
                f"{d}/Kb.md": ent("werkzeug"),
            })
        self.assertEqual(r["graph"]["L5"], [])

    def test_l5_fehlervault(self):
        with mit_einstellungen(dienst_ordner=DIENST):
            r = vl.analyse(os.path.join(TESTDATEN, "L5", "fehler"), HEUTE)
        self.assertEqual(r["graph"]["L5"], [{"person": f"{ENT}/Sigma Muster.md",
                                             "andere": DIENST + "/Fachnotiz.md",
                                             "richtung": "in"}])

    def test_l5_sauber(self):
        with mit_einstellungen(dienst_ordner=DIENST):
            r = vl.analyse(os.path.join(TESTDATEN, "L5", "sauber"), HEUTE)
        self.assertEqual(r["graph"]["L5"], [])

    def test_l5_laeuft_ohne_dienst_ordner(self):
        """Keine Einstellungsdatei: L5 laeuft durch, nichts gilt als dienstlich, kein Fehler."""
        r = vl.analyse(os.path.join(TESTDATEN, "L5", "fehler"), HEUTE)
        self.assertEqual(r["graph"]["L5"], [])
        self.assertIn(f"{ENT}/Sigma Muster.md", r["graph"]["entities"])
        self.assertIn("  L5 Grenze Dienstliches: 0", vl.summary(r, "graph"))

    def test_l5_richtungen(self):
        d = DIENST
        with mit_einstellungen(dienst_ordner=DIENST):
            r = self.bau({
                f"{ENT}/Sigma.md": ent("person") + "Siehe [[Dienst A]] und nochmal [[Dienst A]].\n",
                f"{d}/Dienst A.md": FM + "Text\n",
                f"{d}/Frau Zeta.md": ent("person"),
                f"{d}-Alt/Privat.md": FM + "[[Sigma]]\n",
                f"{ENT}/Tau.md": ent("person") + "[[Privat]]\n",
            })
        self.assertEqual(sorted((f["richtung"], f["person"], f["andere"]) for f in r["graph"]["L5"]), [
            ("aus", f"{ENT}/Sigma.md", f"{d}/Dienst A.md"),
            ("liegt_in", f"{d}/Frau Zeta.md", f"{d}/Frau Zeta.md"),
        ])
        with mit_einstellungen(dienst_ordner=DIENST):
            r = self.bau({
                f"{ENT}/Sigma.md": ent("person"),
                f"{d}/Dienst A.md": FM + "[[Sigma]]\n",
            })
        self.assertEqual([f["richtung"] for f in r["graph"]["L5"]], ["in"])

    def test_l4_fehlervault(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L4", "fehler"), HEUTE)
        self.assertEqual(r["graph"]["L4"], [{
            "kind": "typ", "entity": f"{ENT}/Rho GmbH.md", "feld": "kunde_von", "seite": "ziel",
            "ziel": f"{ENT}/Kappa.md", "ist": "werkzeug", "erwartet": "projekt"}])

    def test_l4_sauber(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L4", "sauber"), HEUTE)
        self.assertEqual(len(r["graph"]["entities"]), 3)
        self.assertEqual(r["graph"]["L4"], [])

    def test_l4_fundarten(self):
        r = self.bau({
            f"{ENT}/Kappa.md": ent("werkzeug", 'kunde_von: "[[Omega - PMO HUB]]"\n'),
            f"{ENT}/Sigma.md": ent("person", 'aliases: [KAPPA]\nkunde_von:\n  - "[[Gibt es nicht]]"\n  - Omega\n'),
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt", "nutzt: []\nentschieden_in: [\"[[Kappa]]\"]\n"),
        })
        f = r["graph"]["L4"]
        self.assertEqual(sorted((x["kind"], x.get("seite", "")) for x in f),
                         [("doppelt", ""), ("fehlt", ""), ("kein_link", ""), ("typ", "quelle"), ("typ", "ziel")])
        by = {(x["kind"], x.get("seite", "")): x for x in f}
        self.assertEqual(by[("typ", "quelle")], {"kind": "typ", "entity": f"{ENT}/Kappa.md",
                                                 "feld": "kunde_von", "seite": "quelle", "ist": "werkzeug"})
        self.assertEqual(by[("fehlt", "")], {"kind": "fehlt", "entity": f"{ENT}/Sigma.md",
                                             "feld": "kunde_von", "ziel": "[[Gibt es nicht]]"})
        self.assertEqual(by[("kein_link", "")], {"kind": "kein_link", "entity": f"{ENT}/Sigma.md",
                                                 "feld": "kunde_von", "wert": "Omega"})
        self.assertEqual(by[("doppelt", "")], {"kind": "doppelt", "name": "kappa",
                                               "entities": [f"{ENT}/Kappa.md", f"{ENT}/Sigma.md"]})
        self.assertEqual(by[("typ", "ziel")], {
            "kind": "typ", "entity": "02 Projekte/Omega/Omega - PMO HUB.md", "feld": "entschieden_in",
            "seite": "ziel", "ziel": f"{ENT}/Kappa.md", "ist": "werkzeug", "erwartet": "keine Entität"})

    def test_summary_graph(self):
        r = self.bau({
            f"{ENT}/Rho.md": ent("firma", 'kunde_von: ["[[Kappa]]"]\n'),
            f"{ENT}/Kappa.md": ent("werkzeug"),
        })
        s = vl.summary(r, "graph")
        self.assertIn("[7] Graph: 2 Entitäten (person 0, firma 1, projekt 0, werkzeug 1)", s)
        self.assertIn("  L4 Widersprüche: 1", s)
        self.assertNotIn("[1]", s)

    def test_register_ohne_archiv(self):
        r = self.bau({
            f"{ENT}/Kappa.md": ent("werkzeug"),
            "06 Archiv/Kappa.md": ent("werkzeug"),
            "Briefings/Kappa.md": ent("werkzeug"),
            "memory/Kappa.md": ent("werkzeug"),
        })
        self.assertEqual(set(r["graph"]["entities"]), {f"{ENT}/Kappa.md"})
        self.assertEqual(r["graph"]["L4"], [])

    def test_name_key(self):
        self.assertEqual(vl.name_key("  Straße "), "strasse")
        self.assertEqual(vl.name_key("Go\u0308ller"), vl.name_key("GÖLLER"))
        # Aliase statt Dateinamen: APFS faltet Straße/STRASSE schon im Dateinamen
        r = self.bau({f"{ENT}/Alpha.md": ent("werkzeug", 'aliases: ["Straße"]\n'),
                      f"{ENT}/Beta.md": ent("werkzeug", 'aliases: ["STRASSE"]\n')})
        d = [f for f in r["graph"]["L4"] if f["kind"] == "doppelt"]
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["name"], "strasse")

    def test_entschieden_in_keine_notiz(self):
        r = self.bau({
            f"{ENT}/Kappa.md": ent("werkzeug", 'entschieden_in: ["[[bild.png]]"]\n'),
            "bild.png": "",
        })
        self.assertEqual(r["graph"]["L4"], [{
            "kind": "typ", "entity": f"{ENT}/Kappa.md", "feld": "entschieden_in", "seite": "ziel",
            "ziel": "bild.png", "ist": "keine Notiz", "erwartet": "keine Entität"}])

    def test_mention_text(self):
        t = ("---\ntype: x\naliases: [Kappa]\n---\nA [[Kappa]] b\n[Kappa](https://k.io) c\n"
             "https://kappa.io/x d\n`Kappa` e\nKappa f\n")
        out = vl.mention_text(t).split("\n")
        self.assertEqual(len(out), len(t.split("\n")))
        self.assertNotIn("Kappa", "\n".join(out[:8]))
        self.assertNotIn("kappa", "\n".join(out[:8]))
        self.assertIn("Kappa f", out[8])

    def l1(self, files):
        return self.bau(files)["graph"]["L1"]

    def test_l1_fehlervault(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L1", "fehler"), HEUTE)
        f = r["graph"]["L1"]
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["note"], f[0]["entity"], f[0]["line"]),
                         ("03 Bereiche/Notizen/Arbeitsnotiz.md", f"{ENT}/Kappa.md", 6))

    def test_l1_sauber(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L1", "sauber"), HEUTE)
        self.assertEqual(r["graph"]["L1"], [])

    def test_l2_fehlervault(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L2", "fehler"), HEUTE)
        self.assertEqual(r["graph"]["L2"], [f"{ENT}/Kappa.md"])

    def test_l2_sauber(self):
        r = vl.analyse(os.path.join(TESTDATEN, "L2", "sauber"), HEUTE)
        self.assertEqual(r["graph"]["L2"], [])

    def test_l1_keine_falschen_treffer(self):
        satz = "Kappa nutzt Omega\n"
        selbst = "Kappa ist ein Werkzeug\n"
        text = (FM + "[[Kappa Tool - Übersicht]]\n[Kappa](https://kappa.io)\nhttps://kappa.io/x\n"
                "`Kappa`\nKappa-Admin\nkappa-git\nKappas\nAdmin-Kappa\n")
        f = self.l1({
            f"{ENT}/Kappa.md": ent("werkzeug", 'aliases: ["Kappa Tool"]\n') + selbst,
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt"),
            "03 Bereiche/A/Test.md": text,
            "03 Bereiche/A/Hub.md": FM + "Siehe [[Omega - PMO HUB|Omega]]\n",
            "memory/n.md": FM + satz,
            "06 Archiv/n.md": FM + satz,
            "Briefings/n.md": FM + satz,
            "Index.md": satz,
            f"{ENT}/_Vorlage Entität.md": ent("") + satz,
        })
        self.assertEqual(f, [])

    def test_l1_link_irgendwo_genuegt(self):
        f = self.l1({
            f"{ENT}/Kappa.md": ent("werkzeug"),
            "03 Bereiche/A/n1.md": "---\ntags: [t]\nnutzt: [\"[[Kappa]]\"]\n---\nKappa im Text\n",
            "03 Bereiche/A/n2.md": FM + "Erst [[Kappa]], dann Kappa nochmal\n",
        })
        self.assertEqual(f, [])

    def test_l1_echte_treffer(self):
        f = self.l1({
            f"{ENT}/Kappa.md": ent("werkzeug", 'aliases: ["Kappa Tool"]\n'),
            "02 Projekte/Omega/Omega - PMO HUB.md": ent("projekt"),
            f"{ENT}/Frau Göller.md": ent("person"),
            "03 Bereiche/A/n1.md": FM + "KAPPA im Text\n",
            "03 Bereiche/A/n2.md": FM + "Wir nutzen Kappa Tool heute\n",
            "03 Bereiche/A/n3.md": FM + "Omega laeuft\n",
            "03 Bereiche/A/n4.md": FM + "Mail an Frau Go\u0308ller\n",
            "03 Bereiche/A/n5.md": FM + "Kappa eins\nKappa zwei\n",
            # Alias statt Dateiname: APFS faltet Straße/STRASSE
            f"{ENT}/Sigma.md": ent("person", 'aliases: ["Straße"]\n'),
            "03 Bereiche/A/n6.md": FM + "Die STRASSE ist gesperrt\n",
            f"{ENT}/Tau.md": ent("person", 'aliases: ["Gasse"]\n'),
            "03 Bereiche/A/n7.md": FM + "Die GAßE ist eng\n",
        })
        got = {(x["note"][-6:-3], x["entity"].rsplit("/", 1)[-1][:-3]): (x["name"], x["line"]) for x in f}
        self.assertEqual(got, {
            ("/n1", "Kappa"): ("Kappa", 5), ("/n2", "Kappa"): ("Kappa Tool", 5),
            ("/n3", "Omega - PMO HUB"): ("Omega", 5), ("/n4", "Frau Göller"): ("Frau Göller", 5),
            ("/n5", "Kappa"): ("Kappa", 5), ("/n6", "Sigma"): ("Straße", 5),
            ("/n7", "Tau"): ("Gasse", 5)})
        self.assertEqual(len(f), 7)
        self.assertTrue(all(x["text"] for x in f))

    def test_l1_person_in_dienstnotiz_kein_fund(self):
        dienst = DIENST + "/Dienstnotiz.md"
        nachbar = DIENST + "-Alt/Notiz.md"
        with mit_einstellungen(dienst_ordner=DIENST):
            f = self.l1({
                f"{ENT}/Herr Zeta.md": ent("person"),
                f"{ENT}/Zeta GmbH.md": ent("firma"),
                dienst: FM + "Herr Zeta von der Zeta GmbH hat angerufen\n",
                "03 Bereiche/A/normal.md": FM + "Herr Zeta ruft an\n",
                nachbar: FM + "Herr Zeta ruft an\n",
            })
        got = {(x["note"], x["entity"].rsplit("/", 1)[-1][:-3]) for x in f}
        self.assertEqual(got, {(dienst, "Zeta GmbH"),
                               ("03 Bereiche/A/normal.md", "Herr Zeta"),
                               (nachbar, "Herr Zeta")})

    def test_l1_nutzt_is_dienst(self):
        from unittest import mock
        files = {f"{ENT}/Herr Zeta.md": ent("person"),
                 "03 Bereiche/A/n.md": FM + "Herr Zeta ruft an\n"}
        self.assertEqual(len(self.l1(files)), 1)
        with mock.patch.object(vl, "is_dienst", return_value=True):
            self.assertEqual(self.l1(files), [])

    def test_summary_l1_l2(self):
        r = self.bau({
            f"{ENT}/Kappa.md": ent("werkzeug"),
            "03 Bereiche/A/n1.md": FM + "Kappa\n",
        })
        s = vl.summary(r, "graph")
        self.assertIn("  L1 Unverlinkte Erwähnungen: 1 in 1 Notizen", s)
        self.assertIn("    Kappa: 1 (erste: n1:5)", s)
        self.assertIn("  L2 Entitäten ohne eingehenden Link: 1", s)
        self.assertIn("Kappa", s.split("L2 Entitäten")[1])


    def test_l1_erste_zeile_ueber_alle_namen(self):
        f = self.l1({f"{ENT}/Kappa.md": ent("werkzeug", 'aliases: ["Kappa Tool"]\n'),
                     "03 Bereiche/A/n.md": FM + "Kappa eins\nKappa Tool zwei\n"})
        self.assertEqual([(x["name"], x["line"]) for x in f], [("Kappa", 5)])

    def test_l2_auch_bei_orphan_exempt(self):
        r = self.bau({"03 Bereiche/Kappa/Kappa.md": ent("werkzeug")})
        self.assertNotIn("03 Bereiche/Kappa/Kappa.md", r["orphans"])
        self.assertEqual(r["graph"]["L2"], ["03 Bereiche/Kappa/Kappa.md"])

    def test_summary_l3_l5(self):
        d = DIENST
        with mit_einstellungen(dienst_ordner=DIENST):
            r = self.bau({f"{ENT}/Sigma.md": ent("person") + "[[Rho]] und [[Dienst A]]\n",
                          f"{ENT}/Rho.md": ent("firma"),
                          f"{d}/Dienst A.md": FM + "Text\n"})
        s = vl.summary(r, "graph")
        self.assertIn("  L3 Fehlende Rückverweise: 1\n    Sigma -> Rho (Z.6)", s)
        self.assertIn("  L5 Grenze Dienstliches: 1\n    Sigma: Dienst A (aus)", s)

    def test_summary_kuerzt_mit_rest_zeile(self):
        files = {f"{ENT}/Z.md": ent("person") + "".join("[[F%d]]\n" % i for i in range(12))}
        for i in range(12):
            files[f"{ENT}/F{i}.md"] = ent("firma")
        r = self.bau(files)
        self.assertEqual(len(r["graph"]["L3"]), 12)
        s = vl.summary(r, "graph")
        self.assertIn("    … +2\n  L4", s)
        r["graph"]["L1"] = [{"note": "n%d.md" % i, "entity": "E%d.md" % i, "name": "E", "line": 1, "text": ""}
                            for i in range(17)]
        self.assertIn("    … +2\n  L2", vl.summary(r, "graph"))
        r["graph"]["L4"] = [{"kind": "doppelt", "name": "x%d" % i, "entities": ["a", "b"]} for i in range(7)]
        self.assertIn("    … +2\n  L5", vl.summary(r, "graph"))


class Cli(unittest.TestCase):
    def lauf(self, *args, einst=None):
        d = tempfile.mkdtemp(prefix="vault-lint-cli-")
        self.addCleanup(shutil.rmtree, d)
        pfad = os.path.join(d, "einstellungen.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write("{}" if einst is None else einst)
        env = dict(os.environ, CLAUDE_SKILLS_EINSTELLUNGEN=pfad, HOME=d)
        return subprocess.run([sys.executable, "-I", os.path.join(HIER, "vault_lint.py"), *args],
                              capture_output=True, text=True, env=env, cwd=d, timeout=60), pfad, d

    def test_cli_ohne_vault_exit2(self):
        r, pfad, _ = self.lauf()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Vault-Pfad fehlt", r.stderr)
        self.assertIn(pfad, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_cli_kaputte_einstellungen_exit2(self):
        v = tempfile.mkdtemp(prefix="vault-lint-cli-vault-")
        self.addCleanup(shutil.rmtree, v)
        for args in ([], ["--vault", v]):   # auch mit --vault: kaputte Datei nie still uebergehen
            r, pfad, _ = self.lauf(*args, einst="{kaputt")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn(pfad, r.stderr)
            self.assertIn("nicht lesbar", r.stderr)
            self.assertNotIn("Traceback", r.stderr)

    def test_cli_falscher_typ_exit2(self):
        v = tempfile.mkdtemp(prefix="vault-lint-cli-vault-")
        self.addCleanup(shutil.rmtree, v)
        for schluessel in ("vault", "dienst_ordner"):
            for wert in (5, ["a"], {"a": 1}, True):
                with self.subTest(schluessel=schluessel, wert=wert):
                    r, pfad, _ = self.lauf("--vault", v, einst=json.dumps({schluessel: wert}))
                    self.assertEqual(r.returncode, 2, r.stderr)
                    self.assertIn(schluessel, r.stderr)
                    self.assertIn("String", r.stderr)
                    self.assertIn(pfad, r.stderr)
                    self.assertNotIn("Traceback", r.stderr)
                    self.assertEqual(r.stdout, "")

    def test_cli_richtiger_typ_bleibt_gruen(self):
        v = tempfile.mkdtemp(prefix="vault-lint-cli-vault-")
        self.addCleanup(shutil.rmtree, v)
        for einst in ({"vault": v, "dienst_ordner": DIENST}, {"dienst_ordner": ""}):
            r, _, _ = self.lauf("--vault", v, einst=json.dumps(einst))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_cli_null_zaehlt_wie_fehlend(self):
        v = tempfile.mkdtemp(prefix="vault-lint-cli-vault-")
        self.addCleanup(shutil.rmtree, v)
        r, _, _ = self.lauf("--vault", v, einst=json.dumps({"vault": None, "dienst_ordner": None}))
        self.assertEqual(r.returncode, 0, r.stderr)
        r, pfad, _ = self.lauf(einst=json.dumps({"vault": None}))   # ohne --vault: wie fehlender Schluessel
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Vault-Pfad fehlt", r.stderr)

    def test_cli_vault_aus_einstellung(self):
        v = tempfile.mkdtemp(prefix="vault-lint-cli-vault-")
        self.addCleanup(shutil.rmtree, v)
        os.makedirs(os.path.join(v, "03 Bereiche", "A"))
        with open(os.path.join(v, "03 Bereiche", "A", "n.md"), "w", encoding="utf-8") as fh:
            fh.write(FM)
        r, _, d = self.lauf("--json", "out.json", "--heute", "2026-10-15", einst=json.dumps({"vault": v}))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(d, "out.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["vault"], v)


class NoteLinks(unittest.TestCase):
    def test_note_links_wiki_markdown_extern_zeile(self):
        res = vl.Resolver(["A/Quelle.md", "A/Ziel.md", "B/Kappa.md"])
        text = ("---\nx: [[Kappa]]\n---\nText [[Ziel|Alias]]\n"
                "`[[Kappa]]` und [Link](Ziel.md) [Web](https://kappa.io)\n"
                "```\n[[Kappa]]\n```\n[[Fehlt]]\n")
        self.assertEqual(vl.note_links("A/Quelle.md", text, res), [
            ("Kappa", "B/Kappa.md", 2),
            ("Ziel|Alias", "A/Ziel.md", 4),
            ("Fehlt", None, 9),
            ("Ziel.md", "A/Ziel.md", 5),
        ])


class IsDienst(unittest.TestCase):
    def test_is_dienst(self):
        d = DIENST
        with mit_einstellungen(dienst_ordner=DIENST):
            self.assertTrue(vl.is_dienst(d + "/Notiz.md"))
            self.assertTrue(vl.is_dienst(d + "/Unter/Notiz.md"))
            self.assertFalse(vl.is_dienst(d + "X/Notiz.md"))
            self.assertFalse(vl.is_dienst(d))
            self.assertFalse(vl.is_dienst("03 Bereiche/" + d + "/Notiz.md"))

    def test_ohne_dienst_ordner_nie_dienstlich(self):
        with mit_einstellungen(vault="/irgendwo"):
            self.assertEqual(vl.dienst_ordner(), "")
            self.assertFalse(vl.is_dienst(DIENST + "/a.md"))
            self.assertFalse(vl.is_dienst("/a.md"))
        with mit_einstellungen(dienst_ordner=""):
            self.assertFalse(vl.is_dienst(DIENST + "/a.md"))
            self.assertFalse(vl.is_dienst("/a.md"))

    def test_dienst_ordner_nfd_wert_wird_nfc(self):
        import unicodedata
        nfd = unicodedata.normalize("NFD", "02 Projekte/Beh\u00f6rde")
        nfc_ = unicodedata.normalize("NFC", nfd)
        self.assertNotEqual(nfd, nfc_)
        with mit_einstellungen(dienst_ordner=nfd):
            self.assertEqual(vl.dienst_ordner(), nfc_)
            self.assertTrue(vl.is_dienst(nfc_ + "/Akte.md"))

    def test_dienst_praefix_ohne_schraegstrich(self):
        with mit_einstellungen(dienst_ordner=DIENST):
            self.assertFalse(vl.is_dienst("02 Projekte/DienstX/a.md"))
            self.assertTrue(vl.is_dienst(DIENST + "/a.md"))
        with mit_einstellungen(dienst_ordner=DIENST + "/"):   # Schraegstrich am Ende zaehlt nicht
            self.assertEqual(vl.dienst_ordner(), DIENST)
            self.assertTrue(vl.is_dienst(DIENST + "/a.md"))
            self.assertFalse(vl.is_dienst("02 Projekte/DienstX/a.md"))

    def test_einstellungen_frisch_gelesen(self):
        with mit_einstellungen(dienst_ordner=DIENST) as pfad:
            self.assertTrue(vl.is_dienst(DIENST + "/a.md"))
            with open(pfad, "w", encoding="utf-8") as fh:
                json.dump({"dienst_ordner": "03 Bereiche/Amt"}, fh)
            self.assertFalse(vl.is_dienst(DIENST + "/a.md"))
            self.assertTrue(vl.is_dienst("03 Bereiche/Amt/a.md"))

    def test_l5_nutzt_is_dienst(self):
        from unittest import mock
        ents = {"P.md": {"type": "person"}}
        self.assertEqual(vl.l5_dienst(ents, {}), [])
        with mock.patch.object(vl, "is_dienst", return_value=True):
            self.assertEqual(vl.l5_dienst(ents, {}), [{"person": "P.md", "andere": "P.md", "richtung": "liegt_in"}])


if __name__ == "__main__":
    unittest.main()
