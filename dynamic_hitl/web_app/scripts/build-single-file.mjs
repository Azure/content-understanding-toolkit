// Builds the site, then folds the emitted JS/CSS back into one self-contained HTML file.
// Output: dist-standalone/dynamic-hitl-explainer.html — no other files, no server, no
// network at view time. The regular `npm run build` output in dist/ is left alone.
import { build } from 'vite';
import { readFile, writeFile, rm, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const stageDir = path.join(root, '.single-file-build');
const outDir = path.join(root, 'dist-standalone');
const outFile = path.join(outDir, 'dynamic-hitl-explainer.html');

// A literal </script> or <!-- inside a string in the bundle would terminate the host tag early.
const escapeForInlineScript = (code) =>
  code.replace(/<\/script/gi, '<\\/script').replace(/<!--/g, '<\\!--');

const readAsset = async (url) => {
  const relative = url.replace(/^\.?\//, '').split('?')[0];
  return readFile(path.join(stageDir, relative), 'utf8');
};

const isLocal = (url) => url && !/^(https?:)?\/\//i.test(url) && !url.startsWith('data:');

async function main() {
  await rm(stageDir, { recursive: true, force: true });

  await build({
    root,
    configFile: path.join(root, 'vite.config.ts'),
    logLevel: 'warn',
    build: {
      outDir: stageDir,
      emptyOutDir: true,
      // One chunk in, one chunk out.
      cssCodeSplit: false,
      modulePreload: { polyfill: false },
      chunkSizeWarningLimit: 4096,
      rollupOptions: {
        output: {
          inlineDynamicImports: true,
          manualChunks: undefined,
        },
      },
    },
  });

  let html = await readFile(path.join(stageDir, 'index.html'), 'utf8');

  // Preloads are meaningless once everything lives in the document.
  html = html.replace(/\s*<link[^>]+rel="modulepreload"[^>]*>/gi, '');

  const scriptTags = [...html.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*>\s*<\/script>/gi)];
  for (const [tag, src] of scriptTags) {
    if (!isLocal(src)) continue;
    const code = escapeForInlineScript(await readAsset(src));
    // Function replacement: `$&` and friends occur naturally in minified code.
    html = html.replace(tag, () => `<script type="module">\n${code}\n</script>`);
  }

  const styleTags = [...html.matchAll(/<link\b[^>]*\brel="stylesheet"[^>]*>/gi)];
  for (const tag of styleTags) {
    const href = /\bhref="([^"]+)"/i.exec(tag[0])?.[1];
    if (!isLocal(href)) continue;
    const css = await readAsset(href);
    html = html.replace(tag[0], () => `<style>\n${css}\n</style>`);
  }

  const leftover = [
    ...html.matchAll(/<(?:script|link)\b[^>]*\b(?:src|href)="(\.?\/[^"]+)"[^>]*>/gi),
  ];
  if (leftover.length) {
    throw new Error(`Unbundled asset references remain: ${leftover.map((m) => m[1]).join(', ')}`);
  }

  // The whole point of this build: opening it on a plane must look identical.
  const remote = [
    ...html.matchAll(/<(?:script|link|img|iframe|source)\b[^>]*\b(?:src|href)="((?:https?:)?\/\/[^"]+)"/gi),
    ...html.matchAll(/@import\s+(?:url\()?["']?(https?:\/\/[^"')]+)/gi),
  ];
  if (remote.length) {
    throw new Error(
      `Page still reaches the network, so it is not offline-safe: ${remote.map((m) => m[1]).join(', ')}`,
    );
  }

  await mkdir(outDir, { recursive: true });
  await writeFile(outFile, html, 'utf8');
  await rm(stageDir, { recursive: true, force: true });

  const kb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(0);
  console.log(`${path.relative(root, outFile).replace(/\\/g, '/')} — ${kb} kB, self-contained and offline.`);
}

main().catch(async (error) => {
  await rm(stageDir, { recursive: true, force: true });
  console.error(error);
  process.exit(1);
});
