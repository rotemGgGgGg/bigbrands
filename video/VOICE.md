# The RTM voice: Viktor

Approved by the client on 2026-10-28 ("יש לו רגש, נשמע אמין"). Use this for every RTM ad unless told otherwise.

| Setting | Value |
|---|---|
| Service | ElevenLabs (account plan: Starter or higher) |
| Voice | **Viktor M - Smart & Kind Guy**, ElevenLabs voice library, native Israeli Hebrew |
| Voice ID | `8sZ9Z3Jy28CGLLCmKEHn` |
| Model | `eleven_v3` (`language_code: he`) |
| Stability | `0.0` ("Creative", the most expressive) |
| Similarity | `0.85` |
| Endpoint | `/v1/text-to-speech/{voice}/with-timestamps` (gives word timings for sync) |

## How to write the script

- Spoken Hebrew, short sentences, talk to the viewer ("אתם").
- Put English emotion cues in square brackets before the line; they shape the delivery and are not spoken:
  `[excited]`, `[curious]`, `[playful]`, `[warm]`, `[cheerfully]`, `[laughs]`.
- Use `!`, `?` and `...` in the script; they change the intonation. (On-screen text still follows the brand guide: no exclamation marks.)
- Numbers in words: "תשעים ותשע שקל", not "99".

## How a take is chosen

Run `python3 video/tools/voice.py script.txt out_dir`. It makes 5 takes, keeps only takes where speech-to-text hears
every word, and picks the one with the widest pitch movement (the approved take had a p10-p90 spread of
10.3 semitones; the flat, "sad" take had 6.8).

The approved reference take is `video/rtm-guess/audio/src/viktor_take_c2.mp3` (script in that folder's build notes).

## Lessons so far

- Always check the words, not only the energy: one lively take turned "תכלת" into "חלת", and every take of
  "מסתוריים" came out sounding like "היסטוריים". The machine now only picks takes where every word is heard.
- Scripts full of questions and surprise come out livelier than calm, "warm" lines. If a batch is flat, rewrite
  the lines with more `?` and `[excited]` before generating more takes.
- Reels made so far: `rtm-guess` (10.3 st, approved), `rtm-gift` (9.87 st), `rtm-which` (9.45 st).
