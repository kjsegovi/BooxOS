package org.booxos.display;

import android.app.UiModeManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.provider.Settings;

/** Applies BooxOS first-boot defaults that have no resource overlay. */
public class BootReceiver extends BroadcastReceiver {
    private static final String KEY_DONE = "defaults_v1";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        SharedPreferences prefs = context.getSharedPreferences("booxos", Context.MODE_PRIVATE);
        if (!prefs.getBoolean(KEY_DONE, false)) {
            // Darker, crisper text on e-ink (user tested 2026-11-18): bold + high contrast.
            Settings.Secure.putInt(context.getContentResolver(),
                    Settings.Secure.FONT_WEIGHT_ADJUSTMENT, 300);
            Settings.Secure.putInt(context.getContentResolver(),
                    Settings.Secure.ACCESSIBILITY_HIGH_TEXT_CONTRAST_ENABLED, 1);
            // Light theme: dark backgrounds ghost more on e-ink.
            UiModeManager ui = context.getSystemService(UiModeManager.class);
            if (ui != null) ui.setNightMode(UiModeManager.MODE_NIGHT_NO);
            prefs.edit().putBoolean(KEY_DONE, true).apply();
        }
        // Keep the color filter in step with the B&W setting (default B&W).
        Display.setMono(context, Display.mono());
    }
}
