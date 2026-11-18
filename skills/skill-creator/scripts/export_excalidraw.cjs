#!/usr/bin/env node
/*
 * export_excalidraw.cjs — Rendert ein Excalidraw-Diagramm als PNG.
 *
 * Der Skill-Lifecycle verlangt pro Skill ein Diagramm als .excalidraw UND .png.
 * Dieses Skript erzeugt das PNG mit der offiziellen Exportfunktion von
 * Excalidraw (@excalidraw/utils) in einem Headless-Chromium (Playwright).
 * Schriften und Geometrie entsprechen damit dem Export aus dem Editor.
 *
 * Aufruf:
 *   node export_excalidraw.cjs <diagramm.excalidraw> [ziel.png] [--scale N]
 *
 *   ziel.png  Default: gleicher Pfad mit .png statt .excalidraw
 *   --scale   Default: 4 (ergibt ~4.000 px Breite wie die bestehenden Diagramme)
 *
 * Voraussetzungen: Node, Playwright mit Chromium (global per npm oder lokal),
 * Netzzugriff auf cdn.jsdelivr.net. Exit-Code 1 im Fehlerfall.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Feste Version: neue Releases haben die Signatur schon einmal geaendert
// (0.1.5 erwartet { data, config } statt flacher Optionen).
const UTILS = 'https://cdn.jsdelivr.net/npm/@excalidraw/utils@0.1.5';

function fail(msg) {
  console.error(`FEHLER: ${msg}`);
  process.exit(1);
}

// Playwright zuerst lokal suchen, dann im globalen npm-Verzeichnis.
function loadPlaywright() {
  try {
    return require('playwright');
  } catch (_) {
    try {
      const root = execSync('npm root -g', { encoding: 'utf8' }).trim();
      return require(path.join(root, 'playwright'));
    } catch (_) {
      fail('Playwright nicht gefunden. Installieren: npm i -g playwright && npx playwright install chromium');
    }
  }
}

function parseArgs(argv) {
  const args = { scale: 4, positional: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--scale') args.scale = Number(argv[++i]);
    else args.positional.push(argv[i]);
  }
  const [input, output] = args.positional;
  if (!input) fail('Aufruf: node export_excalidraw.cjs <diagramm.excalidraw> [ziel.png] [--scale N]');
  if (!(args.scale > 0)) fail('--scale braucht eine positive Zahl.');
  return {
    input,
    output: output || input.replace(/\.excalidraw$/, '') + '.png',
    scale: args.scale,
  };
}

async function main() {
  const { input, output, scale } = parseArgs(process.argv.slice(2));
  let scene;
  try {
    scene = JSON.parse(fs.readFileSync(input, 'utf8'));
  } catch (e) {
    fail(`'${input}' ist keine lesbare Excalidraw-Datei (${e.message}).`);
  }
  if (!Array.isArray(scene.elements)) fail(`'${input}' enthaelt keine elements-Liste.`);

  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    page.on('pageerror', (e) => console.error('[browser]', e.message));
    await page.setContent('<!doctype html><meta charset="utf-8"><body></body>');
    const dataUrl = await page.evaluate(async ({ scene, scale, UTILS }) => {
      // Schriften (Virgil, Cascadia, Excalifont) laedt utils von hier nach.
      window.EXCALIDRAW_ASSET_PATH = UTILS + '/dist/prod/';
      const { exportToBlob } = await import(UTILS + '/+esm');
      const blob = await exportToBlob({
        data: {
          elements: scene.elements,
          appState: { ...scene.appState, exportBackground: true },
          files: scene.files || {},
        },
        config: { mimeType: 'image/png', padding: 20, scale, theme: 'light' },
      });
      return await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(blob);
      });
    }, { scene, scale, UTILS });
    fs.writeFileSync(output, Buffer.from(dataUrl.split(',')[1], 'base64'));
  } finally {
    await browser.close();
  }
  console.log(`PNG geschrieben: ${output}`);
}

main().catch((e) => fail(e.message));
