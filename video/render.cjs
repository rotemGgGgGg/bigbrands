// Shared frame-by-frame renderer for the video pages in this folder.
// Each page exposes window.seek(t) (may return a promise; it is awaited, its value is ignored), window.ready, window.FPS, window.DURATION and (optionally) window.W_PX / window.H_PX.
//
//   node video/render.cjs <page dir> <out.mp4>                -> PNG frames + MP4 with <page dir>/audio/mix.wav
//   node video/render.cjs <page dir> --stills 1.5,8,14        -> renders/stills/<name>_<t>.png
//   SUBFRAMES=3 node video/render.cjs ...                       -> motion blur: 3 renders per frame over a 180° shutter, averaged
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const dir = path.resolve(process.argv[2]);
const name = path.basename(dir);
const stillsAt = process.argv.indexOf('--stills');

(async () => {
  const t0 = Date.now();
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(dir, 'index.html'));
  const meta = await page.evaluate(async () => { await window.ready; return { fps: window.FPS, dur: window.DURATION, w: window.W_PX || 1920, h: window.H_PX || 1080 }; });
  await page.setViewportSize({ width: meta.w, height: meta.h });

  if (stillsAt > 0) {
    const out = path.join(ROOT, 'renders', 'stills');
    fs.mkdirSync(out, { recursive: true });
    for (const t of process.argv[stillsAt + 1].split(',').map(Number)) {
      await page.evaluate(async t => { await window.seek(t); }, t);
      await page.screenshot({ path: path.join(out, `${name}_${t.toFixed(2)}.png`) });
    }
    await browser.close();
    console.log(`stills in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    return;
  }

  const outFile = path.resolve(process.argv[3]);
  const frames = path.join(ROOT, 'renders', 'frames', name);
  fs.rmSync(frames, { recursive: true, force: true });
  fs.mkdirSync(frames, { recursive: true });
  const n = Math.round(meta.dur * meta.fps);
  const sub = Math.max(1, parseInt(process.env.SUBFRAMES || '1', 10));
  const dt = sub > 1 ? 0.5 / (meta.fps * (sub - 1)) : 0;          // 180° shutter that ends on the frame time
  for (let i = 0, j = 0; i < n; i++) {
    for (let k = 0; k < sub; k++, j++) {
      await page.evaluate(async t => { await window.seek(t); }, Math.max(0, i / meta.fps - (sub - 1 - k) * dt));
      await page.screenshot({ path: path.join(frames, `f_${String(j).padStart(6, '0')}.png`) });
    }
  }
  await browser.close();
  const tFrames = (Date.now() - t0) / 1000;

  execFileSync('ffmpeg', ['-v', 'error', '-y',
    '-framerate', String(meta.fps * sub), '-i', path.join(frames, 'f_%06d.png'),
    ...(sub > 1 ? ['-vf', `tmix=frames=${sub},select='eq(mod(n\\,${sub})\\,${sub - 1})',setpts=N/${meta.fps}/TB`] : []),
    '-i', path.join(dir, 'audio', 'mix.wav'),
    '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-r', String(meta.fps),
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-t', String(meta.dur), '-movflags', '+faststart', outFile], { stdio: 'inherit' });
  console.log(`${meta.w}x${meta.h}@${meta.fps} x${sub} | frames: ${n} in ${tFrames.toFixed(1)}s (${(tFrames / n * 1000).toFixed(0)} ms/frame) | total with encode: ${((Date.now() - t0) / 1000).toFixed(1)}s`);
})();
