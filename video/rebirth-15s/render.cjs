// Frame-by-frame renderer: drives the page's paused GSAP timeline in headless Chromium,
// saves one PNG per frame, then assembles them with the mixed audio via FFmpeg.
//
//   node render.cjs                      -> renders/frames/*.png + renders/test.mp4
//   node render.cjs --stills 2.5,7.5,13  -> renders/stills/still_<t>.png only
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const PAGE = 'file://' + path.join(__dirname, 'index.html');
const AUDIO = path.join(__dirname, 'audio', 'mix.wav');
const OUT = path.join(ROOT, 'renders');

(async () => {
  const stillsArg = process.argv.indexOf('--stills');
  const stills = stillsArg > 0 ? process.argv[stillsArg + 1].split(',').map(Number) : null;
  const t0 = Date.now();

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(PAGE);
  const { fps, duration } = await page.evaluate(async () => { await window.ready; return { fps: window.FPS, duration: window.DURATION }; });

  if (stills) {
    fs.mkdirSync(path.join(OUT, 'stills'), { recursive: true });
    for (const t of stills) {
      await page.evaluate(t => window.seek(t), t);
      await page.screenshot({ path: path.join(OUT, 'stills', `still_${t.toFixed(2)}.png`) });
    }
    await browser.close();
    console.log(`stills: ${stills.length} in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    return;
  }

  const frames = path.join(OUT, 'frames');
  fs.rmSync(frames, { recursive: true, force: true });
  fs.mkdirSync(frames, { recursive: true });
  const n = Math.round(duration * fps);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.seek(t), i / fps);
    await page.screenshot({ path: path.join(frames, `f_${String(i).padStart(5, '0')}.png`) });
  }
  await browser.close();
  const tFrames = (Date.now() - t0) / 1000;

  execFileSync('ffmpeg', ['-v', 'error', '-y',
    '-framerate', String(fps), '-i', path.join(frames, 'f_%05d.png'),
    '-i', AUDIO,
    '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(fps),
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-t', String(duration), '-movflags', '+faststart',
    path.join(OUT, 'test.mp4')], { stdio: 'inherit' });
  const tAll = (Date.now() - t0) / 1000;
  console.log(`frames: ${n} in ${tFrames.toFixed(1)}s (${(tFrames / n * 1000).toFixed(0)} ms/frame) | total with encode: ${tAll.toFixed(1)}s`);
})();
