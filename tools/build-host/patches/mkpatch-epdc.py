#!/usr/bin/env python3
# Applies the BooxOS e-ink edits to a pristine frameworks/native tree.
# Run from frameworks/native, then `git diff` the three files into
# frameworks_native-0001-epdc-update-list.patch.
import sys

def edit(path, pairs):
    s = open(path).read()
    for old, new in pairs:
        if s.count(old) != 1:
            sys.exit(f"{path}: anchor found {s.count(old)}x: {old[:70]!r}")
        s = s.replace(old, new)
    open(path, 'w').write(s)

SF = 'services/surfaceflinger/'

# --- CompositionEngine: publish per-frame inputs for the e-ink policy.
edit(SF + 'CompositionEngine/src/Output.cpp', [
("""#include "TracedOrdinal.h"
""", """#include "TracedOrdinal.h"

#include <atomic>
#include <algorithm>
#include <functional>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace android::booxos {
// BOOXOS: e-ink refresh policy inputs, read by HidlComposer before each present:
// bounding-box area (px) of the region recomposed for the frame being presented,
// its bounds, the area of the whole output, and a signature of the set of apps
// owning big visible windows (activity windows covering >= epdc_switch_pct % of
// the screen). The policy compares it, once the screen is quiet, with the set at
// the last clean: a different set means an app switch. Scrolling changes
// geometry every frame and popups/toolbars change windows, but not this set;
// brief blips during transitions revert before the screen goes quiet.
std::atomic<int64_t> gFrameDirtyArea{0};
std::atomic<int32_t> gFrameDirtyLeft{0}, gFrameDirtyTop{0}, gFrameDirtyRight{0},
        gFrameDirtyBottom{0};
std::atomic<int64_t> gFrameScreenArea{0};
std::atomic<uint64_t> gAppSetSig{0};
} // namespace android::booxos
"""),
("""    outputState.undefinedRegion = undefinedRegion;
    outputState.dirtyRegion.orSelf(coverage.dirtyRegion);
}
""", """    outputState.undefinedRegion = undefinedRegion;
    outputState.dirtyRegion.orSelf(coverage.dirtyRegion);
    {
        // BOOXOS: see gAppSetSig.
        const Rect screen = outputState.layerStackSpace.getContent();
        const int64_t screenArea = int64_t{screen.getWidth()} * screen.getHeight();
        const int64_t pct = base::GetIntProperty("debug.booxos.epdc_switch_pct",
                base::GetIntProperty("ro.surface_flinger.booxos_epdc_switch_pct", 50));
        const bool log = base::GetBoolProperty("debug.booxos.epdc_log", false);
        std::vector<std::string> packages;
        for (auto* layer : getOutputLayersOrderedByZ()) {
            const Rect b = layer->getState().visibleRegion.getBounds();
            if (int64_t{b.getWidth()} * b.getHeight() * 100 < pct * screenArea) continue;
            // Activity windows are named "<package>/<activity>#<seq>".
            const std::string_view name = layer->getLayerFE().getDebugName();
            const size_t slash = name.find('/');
            if (slash == std::string_view::npos) continue;
            packages.emplace_back(name.substr(0, slash));
        }
        // The set of apps, each counted once (an app with two windows is one app).
        std::sort(packages.begin(), packages.end());
        packages.erase(std::unique(packages.begin(), packages.end()), packages.end());
        uint64_t sig = 1469598103934665603ull;
        std::string names;
        for (const auto& pkg : packages) {
            sig = (sig ^ std::hash<std::string>{}(pkg)) * 1099511628211ull;
            if (log) {
                names += pkg;
                names += "; ";
            }
        }
        if (packages.empty()) return;  // mid-transition: no app window yet
        if (android::booxos::gAppSetSig.exchange(sig) != sig) {
            ALOGI_IF(log, "BOOXOS: visible apps now: %s", names.c_str());
        }
    }
}
"""),
("""    auto& outputState = editState();
    outputState.dirtyRegion.clear();

    auto frame = presentFrame();
""", """    auto& outputState = editState();
    {
        // BOOXOS: see gFrameDirtyArea.
        const Rect dirty = getDirtyRegion().getBounds();
        const Rect screen = outputState.layerStackSpace.getContent();
        android::booxos::gFrameDirtyArea.store(int64_t{dirty.getWidth()} * dirty.getHeight());
        android::booxos::gFrameDirtyLeft.store(dirty.left);
        android::booxos::gFrameDirtyTop.store(dirty.top);
        android::booxos::gFrameDirtyRight.store(dirty.right);
        android::booxos::gFrameDirtyBottom.store(dirty.bottom);
        android::booxos::gFrameScreenArea.store(int64_t{screen.getWidth()} * screen.getHeight());
    }
    outputState.dirtyRegion.clear();

    auto frame = presentFrame();
"""),
])

# --- HidlComposerHal.h: command writer + hooks.
edit(SF + 'DisplayHardware/HidlComposerHal.h', [
("""        explicit CommandWriter(uint32_t initialMaxSize) : CommandWriterBase(initialMaxSize) {}
        ~CommandWriter() override {}
""", """        explicit CommandWriter(uint32_t initialMaxSize) : CommandWriterBase(initialMaxSize) {}
        ~CommandWriter() override {}

        // BOOXOS: Onyx EPDC update list for the stock (Onyx-modified) QTI
        // composer: opcode 0x802, payload = item count, then 5 words per item
        // {left, top, right, bottom, mode}. The composer clamps the rect to the
        // display and turns each item into an e-ink panel update at present.
        void setDisplayEpdc(const std::vector<int32_t>& items) {
            beginCommand(static_cast<uint32_t>(0x802u << 16),
                         static_cast<uint16_t>(1 + items.size()));
            write(static_cast<uint32_t>(items.size() / 5));
            for (int32_t v : items) writeSigned(v);
            endCommand();
        }
"""),
("""    void registerCallback(const sp<IComposerCallback>& callback);
""", """    void registerCallback(const sp<IComposerCallback>& callback);

    // BOOXOS: queue one full-screen e-ink update before each present. Returns
    // the update kind (see BooxosUpdate in the .cpp), or -1 if none queued;
    // pass that to commitBooxosEpdc() once the present has happened.
    int writeBooxosEpdc();
    void commitBooxosEpdc(int kind);
"""),
])

# --- HidlComposerHal.cpp: refresh policy + front light.
POLICY = r'''// BOOXOS: e-ink refresh policy for the Onyx EPDC (GoColor7_2).
//
// The Onyx vendor composer only refreshes the panel for regions SurfaceFlinger
// lists with each present (stock: EpdcManager). Normal frames send one
// full-screen item; the panel only drives pixels that changed. Each frame is:
//   normal  epdc_mode (default 260 = A2 + dither: smooth, but ghosts)
//   motion  optional: frames closer than epdc_motion_ms apart use
//           epdc_motion_mode (off by default)
//   clean   once the screen has been quiet for epdc_idle_ms, after an app switch
//           (epdc_clean_on_switch; see gAppSetSig in Output.cpp) or once
//           partial updates changed epdc_clean_pct % of the screen. Gentle
//           (epdc_settle_mode, little flash) by default; every
//           epdc_hard_every-th clean is hard (epdc_full_mode, flashes). With
//           epdc_regional, a clean only covers the area that changed since the
//           last clean. epdc_settle_after_motion also cleans after a motion burst.
// epdc_flags is ORed into every mode word.
// Live experiments behind the defaults: work/eink-live-experiments-2026-11-18.md
//
// Settings: debug.booxos.<name> (live tuning) overrides
// ro.surface_flinger.booxos_<name>. A negative epdc_mode disables all of this;
// a negative motion/settle/full mode disables that kind.
namespace {

enum BooxosUpdate { kNormal = 0, kMotion = 1, kSettle = 2, kFull = 3 };

int32_t booxosSetting(const char* name, int32_t fallback) {
    const std::string n(name);
    return base::GetIntProperty("debug.booxos." + n,
                                base::GetIntProperty("ro.surface_flinger.booxos_" + n, fallback));
}

struct BooxosEpdcPolicy {
    std::mutex mutex;
    std::condition_variable cv;
    std::chrono::steady_clock::time_point lastPresent;
    int64_t ghostArea = 0;     // px changed by partial updates since the last clean
    uint32_t motionFrames = 0; // motion frames since the last clean
    int32_t rl = 0, rt = 0, rr = 0, rb = 0;  // union of dirty rects since the last clean
    uint32_t cleans = 0;       // cleans so far (every epdc_hard_every-th is hard)
    bool geometryPending = false;
    int pending = -1;          // kSettle/kFull requested for the next frame, or -1
    bool workerStarted = false;
    std::string mono;          // persist.booxos.display.mono as last seen
    uint64_t appSet = 0;       // gAppSetSig at the last clean (or first frame)
};

BooxosEpdcPolicy& booxosPolicy() {
    static auto* policy = new BooxosEpdcPolicy;
    return *policy;
}

// Asks SurfaceFlinger (this process) to composite one more frame, like
// `service call SurfaceFlinger 1004` (which also sends the interface token).
// Called off the binder and main threads, so the calling uid is our own (system).
void booxosRequestFrame() {
    sp<IBinder> sf = defaultServiceManager()->checkService(String16("SurfaceFlinger"));
    if (sf == nullptr) return;
    Parcel data, reply;
    data.writeInterfaceToken(sf->getInterfaceDescriptor());  // CHECK_INTERFACE
    const status_t err = sf->transact(1004, data, &reply);
    ALOGW_IF(err != NO_ERROR, "BOOXOS: e-ink redraw request failed: %d", err);
}

void booxosEpdcWorker() {
    pthread_setname_np(pthread_self(), "booxos_epdc");
    auto& p = booxosPolicy();
    std::unique_lock lock(p.mutex);
    for (;;) {
        p.cv.wait(lock, [&] {
            return p.pending < 0 && (p.motionFrames > 0 || p.geometryPending || p.ghostArea > 0);
        });
        const auto idle = std::chrono::milliseconds(std::max(booxosSetting("epdc_idle_ms", 600), 50));
        const auto quietAt = p.lastPresent + idle;
        if (std::chrono::steady_clock::now() < quietAt) {
            p.cv.wait_until(lock, quietAt);
            continue;  // re-check: more frames may have arrived
        }
        const int64_t pct = booxosSetting("epdc_clean_pct", 0);
        const int64_t screen = android::booxos::gFrameScreenArea.load();
        const bool hardOk = booxosSetting("epdc_full_mode", -1) >= 0;
        const bool gentleOk = booxosSetting("epdc_settle_mode", -1) >= 0;
        const uint64_t appSet = android::booxos::gAppSetSig.load();
        if (p.appSet == 0) p.appSet = appSet;
        const bool switched = appSet != 0 && appSet != p.appSet;
        if (switched) {
            p.appSet = appSet;
            ALOGI_IF(base::GetBoolProperty("debug.booxos.epdc_log", false),
                     "BOOXOS: app switch -> clean");
        }
        const bool clean = ((switched || p.geometryPending) &&
                            booxosSetting("epdc_clean_on_switch", 0) > 0) ||
                (pct > 0 && screen > 0 && p.ghostArea * 100 >= pct * screen) ||
                (p.motionFrames > 0 && booxosSetting("epdc_settle_after_motion", 0) > 0);
        if (clean && (hardOk || gentleOk)) {
            const uint32_t hardEvery = std::max(booxosSetting("epdc_hard_every", 0), 0);
            ++p.cleans;
            p.pending = (hardOk && (!gentleOk || (hardEvery > 0 && p.cleans % hardEvery == 0)))
                    ? kFull
                    : kSettle;
        } else {
            // Nothing to redraw yet: forget the switch, sleep until the next present.
            p.geometryPending = false;
            p.motionFrames = 0;
            const auto seen = p.lastPresent;
            p.cv.wait(lock, [&] { return p.lastPresent != seen; });
            continue;
        }
        lock.unlock();
        booxosRequestFrame();
        lock.lock();
    }
}

// Front light: Android drives the composer's (dummy DSI) panel brightness; the
// real light is the Onyx backlight (0..max). Slider at its minimum = light off.
void booxosSetFrontLight(float brightness) {
    static int fd = -2;
    static int last = -1;
    if (fd == -2) {
        fd = open("/sys/class/backlight/onyx_bl_br/brightness", O_WRONLY | O_CLOEXEC);
        ALOGW_IF(fd < 0, "BOOXOS: front light not writable: %s", strerror(errno));
    }
    if (fd < 0) return;
    const int max = std::clamp(booxosSetting("light_max", 32), 1, 255);
    const float off = booxosSetting("light_off_permille", 40) / 1000.f;
    int level = 0;
    if (brightness > off) {
        level = std::clamp(static_cast<int>(std::lround(brightness * max)), 1, max);
    }
    if (level == last) return;
    const std::string s = std::to_string(level);
    if (TEMP_FAILURE_RETRY(pwrite(fd, s.c_str(), s.size(), 0)) < 0) {
        ALOGW("BOOXOS: front light write failed: %s", strerror(errno));
        return;
    }
    ALOGI("BOOXOS: front light %d/%d (brightness %.3f)", level, max, brightness);
    last = level;
}

} // namespace

int HidlComposer::writeBooxosEpdc() {
    const int32_t normalMode = booxosSetting("epdc_mode", -1);
    if (normalMode < 0) return -1;
    auto& p = booxosPolicy();
    int kind = kNormal;
    std::vector<int32_t> rect = {0, 0, 32767, 32767};
    {
        std::lock_guard lock(p.mutex);
        if (!p.workerStarted) {
            p.workerStarted = true;
            std::thread(booxosEpdcWorker).detach();
        }
        const int32_t motionMs = booxosSetting("epdc_motion_ms", 300);
        if (p.pending >= 0) {
            kind = p.pending;
            if (booxosSetting("epdc_regional", 0) > 0 && p.rr > p.rl && p.rb > p.rt) {
                rect = {p.rl, p.rt, p.rr, p.rb};
            }
        } else if (motionMs > 0 && booxosSetting("epdc_motion_mode", -1) >= 0 &&
                   std::chrono::steady_clock::now() - p.lastPresent <
                           std::chrono::milliseconds(motionMs)) {
            kind = kMotion;
        }
    }
    int32_t mode = normalMode;
    if (kind == kMotion) mode = booxosSetting("epdc_motion_mode", normalMode);
    if (kind == kSettle) mode = booxosSetting("epdc_settle_mode", normalMode);
    if (kind == kFull) mode = booxosSetting("epdc_full_mode", normalMode);
    if (mode < 0) {
        kind = kNormal;
        mode = normalMode;
    }
    mode |= booxosSetting("epdc_flags", 0);
    rect.push_back(mode);
    mWriter.setDisplayEpdc(rect);
    return kind;
}

void HidlComposer::commitBooxosEpdc(int kind) {
    if (kind < 0) return;
    auto& p = booxosPolicy();
    const std::string mono = base::GetProperty("persist.booxos.display.mono", "");
    {
        std::lock_guard lock(p.mutex);
        if (mono != p.mono) {
            // B&W/Color switched: redraw cleanly in the new look.
            if (!p.mono.empty() || !mono.empty()) p.geometryPending = true;
            p.mono = mono;
        }
        switch (kind) {
            case kFull:
            case kSettle:
                p.ghostArea = 0;
                p.motionFrames = 0;
                p.geometryPending = false;
                p.rl = p.rt = p.rr = p.rb = 0;
                break;
            case kMotion:
                p.motionFrames++;
                [[fallthrough]];
            default: {
                p.ghostArea += android::booxos::gFrameDirtyArea.load();
                const int32_t l = android::booxos::gFrameDirtyLeft.load();
                const int32_t t = android::booxos::gFrameDirtyTop.load();
                const int32_t r = android::booxos::gFrameDirtyRight.load();
                const int32_t b = android::booxos::gFrameDirtyBottom.load();
                if (r > l && b > t) {
                    if (p.rr > p.rl && p.rb > p.rt) {
                        p.rl = std::min(p.rl, l);
                        p.rt = std::min(p.rt, t);
                        p.rr = std::max(p.rr, r);
                        p.rb = std::max(p.rb, b);
                    } else {
                        p.rl = l, p.rt = t, p.rr = r, p.rb = b;
                    }
                }
                break;
            }
        }
        if (p.pending == kind) p.pending = -1;
        p.lastPresent = std::chrono::steady_clock::now();
    }
    p.cv.notify_all();
}

Error HidlComposer::presentDisplay(Display display, int* outPresentFence) {
    ATRACE_NAME("HwcPresentDisplay");
    mWriter.selectDisplay(display);
    const int booxosEpdc = writeBooxosEpdc();
    mWriter.presentDisplay();

    Error error = execute();
    if (error != Error::NONE) {
        return error;
    }
    commitBooxosEpdc(booxosEpdc);
'''

edit(SF + 'DisplayHardware/HidlComposerHal.cpp', [
("""#include <android/binder_manager.h>
""", """#include <android-base/properties.h>
#include <android/binder_manager.h>
#include <binder/IServiceManager.h>
#include <binder/Parcel.h>
"""),
("""#include <algorithm>
#include <cinttypes>
""", """#include <algorithm>
#include <atomic>
#include <chrono>
#include <cinttypes>
#include <cmath>
#include <condition_variable>
#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>

namespace android::booxos {
// BOOXOS: set by CompositionEngine (Output.cpp).
extern std::atomic<int64_t> gFrameDirtyArea;
extern std::atomic<int64_t> gFrameScreenArea;
extern std::atomic<int32_t> gFrameDirtyLeft, gFrameDirtyTop, gFrameDirtyRight, gFrameDirtyBottom;
extern std::atomic<uint64_t> gAppSetSig;
} // namespace android::booxos
"""),
("""Error HidlComposer::presentDisplay(Display display, int* outPresentFence) {
    ATRACE_NAME("HwcPresentDisplay");
    mWriter.selectDisplay(display);
    mWriter.presentDisplay();

    Error error = execute();
    if (error != Error::NONE) {
        return error;
    }
""", POLICY),
("""    mWriter.selectDisplay(display);
    mWriter.presentOrvalidateDisplay();

    Error error = execute();
    if (error != Error::NONE) {
        return error;
    }

    mReader.takePresentOrValidateStage(display, state);

    if (*state == 1) { // Present succeeded
        mReader.takePresentFence(display, outPresentFence);
    }
""", """    mWriter.selectDisplay(display);
    const int booxosEpdc = writeBooxosEpdc();
    mWriter.presentOrvalidateDisplay();

    Error error = execute();
    if (error != Error::NONE) {
        return error;
    }

    mReader.takePresentOrValidateStage(display, state);

    if (*state == 1) { // Present succeeded
        mReader.takePresentFence(display, outPresentFence);
        commitBooxosEpdc(booxosEpdc);
    }
"""),
("""Error HidlComposer::setDisplayBrightness(Display display, float brightness, float,
                                         const DisplayBrightnessOptions&) {
    if (!mClient_2_3) {
""", """Error HidlComposer::setDisplayBrightness(Display display, float brightness, float,
                                         const DisplayBrightnessOptions&) {
    booxosSetFrontLight(brightness);  // BOOXOS: brightness slider -> front light
    if (!mClient_2_3) {
"""),
])
print("ok")
