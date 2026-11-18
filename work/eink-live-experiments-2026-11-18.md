# E-ink live experiments — 2026-11-18 (bring-up 18, user watching)

Method: `debug.booxos.epdc_mode` set live, with a full redraw forced by `service call SurfaceFlinger 1004` (root). Test card: Jelly browser at `http://localhost:8080` via `adb reverse`, showing color bars, a gray ramp, 1-px lines and text from 9 to 20 px. The composer logs `update_to_display ... flags = %x` for most updates, which confirmed the flags reached the kernel.

## Mode-word flags (vendor composer → kernel flags)
| Mode word (on 34) | Kernel flag | Result |
|---|---|---|
| bit6 (0x40) | 0x1000 | no visible change |
| bit19 (0x80000) | 0x80000 | text looked crisper; **color kept** |
| bits20+21 (0x300000) | 0x8 | no visible change |
| bit22 (0x400000) | 0x400000 | text looked crisper; **color kept** (stock ORs this optionally) |
| bit28 (0x10000000) | 0x10000000 | no visible change |
| raw 0x10/0x20/0x40/0x80/0x100020 | raw | **screen blanked** (clear/fill ops) |

- **No controller B&W switch found.** The kernel's `onyx_epdc_extbuf_convert_gray` vs `_convert_gray_for_cfa` paths were not reached by any mode-word flag.
- Android grayscale (daltonizer mono) made **no visible difference to text**. Black text is gray content and already renders at full 300 ppi under the Kaleido filter.
- Conclusion: a B&W toggle helps images only (grayscale at full resolution instead of 150 ppi color), not text.

## Text
- Bold text (`font_weight_adjustment=300`) plus high-contrast text: **better, keep**.
- Density 320 vs 300: **keep 320**.

## Waveforms for everyday updates (auto-clean off, 30 s of use each)
| Mode | Result |
|---|---|
| 5 (auto, bring-up 18 default) | heavy ghosting, "nauseating" flashing on scroll and app open/close |
| 4 (wf4 + REGAL flag) | far worse: almost no refresh, layered ghosting |
| 2 (GC16 partial) | same as 5 |
| 1 (wf1) | worse / broken |
| 3 (wf3) | same as 5, ghosting remains |
| **260 = 4 + bit8 (A2 + dither Y1)** | **much calmer scrolling** (ghosts, but a clean follows) |

## Clean redraws (after ghosting from A2 scrolling)
| Mode | Result |
|---|---|
| 34 (GC16 full) | fully clean, **harsh flash** |
| 35 (wf3 full) | gentle, **partly clean** |

The user also noted: after a clean in Settings, going to the home screen still showed ghosting, so an app-switch clean is needed.

## Resulting policy (to implement)
- Motion burst (frames close together): 260.
- Isolated update: a quality partial waveform.
- Burst ends: gentle settle redraw (35).
- App switch / geometry change, or lots of accumulated change: harsh clean (34).
- All of it live-tunable.

## Round 2 (afternoon): the policy the user picked
Tried and rejected:
- Motion detection (A2 only while frames come fast, quality waveform for isolated updates) plus a settle redraw after motion: "not smooth anymore, a lot of flashing".
- App-switch detection from SurfaceFlinger geometry changes: scrolling rebuilds geometry every frame with the whole screen dirty, so it fired on every scroll stop.
- App-switch detection from the set of big visible layers: popups and toolbars, and apps with two windows, counted as switches.

**Chosen** (user: "near perfect"):
- Every update: **260** (A2 + dither).
- Cleanup **only on an app switch**. The switch is detected as a change in the *set of apps* owning big activity windows (`<pkg>/<activity>` layer names, each counted once). It is compared once the screen has been quiet for 300 ms against the set at the last cleanup, so transition blips don't count.
- The cleanup covers only the area changed since the last cleanup. It is gentle (35) normally and hard (34) every 4th time.
- Area-based cleanup (`epdc_clean_pct`) is off.

Verified from the logs: no cleanup while scrolling Settings or turning pages in Readest; exactly one when going home.
