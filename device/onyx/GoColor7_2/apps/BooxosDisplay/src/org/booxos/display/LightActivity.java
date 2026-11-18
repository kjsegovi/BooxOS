package org.booxos.display;

import android.app.Activity;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.SeekBar;

/** Brightness (drives the front light through SurfaceFlinger) and warmth sliders. */
public class LightActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.light);

        SeekBar brightness = findViewById(R.id.brightness);
        brightness.setProgress(Settings.System.getInt(getContentResolver(),
                Settings.System.SCREEN_BRIGHTNESS, 102));
        brightness.setOnSeekBarChangeListener(new Listener() {
            @Override
            public void onProgressChanged(SeekBar bar, int value, boolean fromUser) {
                if (fromUser) {
                    Settings.System.putInt(getContentResolver(),
                            Settings.System.SCREEN_BRIGHTNESS, value);
                }
            }
        });

        SeekBar warmth = findViewById(R.id.warmth);
        warmth.setProgress(Display.warmth());
        warmth.setOnSeekBarChangeListener(new Listener() {
            @Override
            public void onProgressChanged(SeekBar bar, int value, boolean fromUser) {
                if (fromUser) Display.setWarmth(value);
            }
        });

        findViewById(R.id.done).setOnClickListener(v -> finish());
    }

    private abstract static class Listener implements SeekBar.OnSeekBarChangeListener {
        @Override public void onStartTrackingTouch(SeekBar bar) {}
        @Override public void onStopTrackingTouch(SeekBar bar) {}
    }
}
