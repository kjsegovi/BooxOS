package org.booxos.display;

import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** Quick Settings tile: black & white (full 300 ppi) or color (150 ppi). */
public class ColorTileService extends TileService {
    @Override
    public void onStartListening() {
        update();
    }

    @Override
    public void onClick() {
        Display.setMono(this, !Display.mono());
        update();
    }

    private void update() {
        Tile tile = getQsTile();
        if (tile == null) return;
        boolean mono = Display.mono();
        tile.setState(mono ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
        tile.setSubtitle(getString(mono ? R.string.mono_on : R.string.mono_off));
        tile.updateTile();
    }
}
