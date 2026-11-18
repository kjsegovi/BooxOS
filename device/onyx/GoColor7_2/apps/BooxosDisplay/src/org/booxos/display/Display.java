package org.booxos.display;

import android.content.ContentResolver;
import android.content.Context;
import android.os.SystemProperties;
import android.provider.Settings;

/** Shared settings for the BooxOS e-ink display tiles. */
final class Display {
    static final String PROP_WARMTH = "persist.booxos.light.warmth";  // 0..32, init -> onyx_bl_ct
    static final String PROP_MONO = "persist.booxos.display.mono";    // SurfaceFlinger cleans on change
    static final int WARMTH_MAX = 32;

    private Display() {}

    static int warmth() {
        return Math.max(0, Math.min(WARMTH_MAX, SystemProperties.getInt(PROP_WARMTH, 0)));
    }

    static void setWarmth(int level) {
        SystemProperties.set(PROP_WARMTH, Integer.toString(Math.max(0, Math.min(WARMTH_MAX, level))));
    }

    static boolean mono() {
        return SystemProperties.getBoolean(PROP_MONO, true);
    }

    /**
     * B&W: Android's monochrome color filter (Kaleido color pixels are 150 ppi; gray
     * content uses the full 300 ppi panel). Color: filter off.
     */
    static void setMono(Context context, boolean on) {
        ContentResolver cr = context.getContentResolver();
        Settings.Secure.putInt(cr, Settings.Secure.ACCESSIBILITY_DISPLAY_DALTONIZER, 0);  // monochromacy
        Settings.Secure.putInt(cr, Settings.Secure.ACCESSIBILITY_DISPLAY_DALTONIZER_ENABLED, on ? 1 : 0);
        SystemProperties.set(PROP_MONO, on ? "1" : "0");
    }
}
