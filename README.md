# Cat Feeder Donation Orchestrator

This project provides the backend, browser overlays, and Arduino sketch required to automate
cat feeding rewards whenever your viewers donate on Twitch, YouTube, TikTok, or any other
platform. Donations are queued to avoid overlap, rendered with configurable animations and
sounds, and mapped to one of five motors that dispense different treats.

## Features

- ✅ **Configurable delayed queue** to serialize donation alerts and motor triggers.
- ✅ **Animated HTML overlay** with tier-specific sounds, icons, and messaging.
- ✅ **Sleep mode** that disables physical dispensing during quiet hours.
- ✅ **REST API** to ingest donations from any source and query recent events.
- ✅ **Arduino Nano sketch** that listens for serial commands and toggles five motors.

## Project layout

```
├── arduino/
│   └── cat_feeder.ino        # Arduino Nano sketch
├── config/
│   └── settings.json         # Donation tiers, queue delay, sleep mode, serial config
├── src/cat_feeder/
│   ├── __main__.py           # CLI entrypoint for launching the FastAPI server
│   ├── arduino.py            # Serial communication wrapper
│   ├── config.py             # Settings loader
│   ├── donation_manager.py   # Queue orchestration and alert dispatching
│   ├── models.py             # Pydantic-free dataclasses
│   ├── server.py             # FastAPI application and websocket endpoints
│   └── sleep.py              # Sleep window helpers
├── static/                   # Overlay assets (CSS, JS, optional sounds/animations)
└── templates/                # HTML templates for overlay and sleep status pages
```

## Requirements

- Python 3.11+
- Arduino Nano with five relays or motor drivers wired to digital pins 2–6.
- Optional: audio (`.mp3`, `.wav`) and CSS animation files stored under `static/`.

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the overlay server

```bash
python -m cat_feeder --host 0.0.0.0 --port 8000
```

The server exposes:

- `POST /donations` – enqueue a donation. Example payload:

  ```json
  {
    "username": "Example",
    "platform": "Twitch",
    "raw_amount": "7 €",
    "value": 7,
    "message": "Tier 2 cheer!"
  }
  ```

- `GET /overlay` – browser source for OBS/Streamlabs.
- `GET /sleep-status` – static page indicating whether sleep mode is currently active.
- `GET /sleep-mode` – JSON sleep mode status for automations.
- `GET /donations/recent` – last processed donations.
- `WS /ws/alerts` – websocket used by the overlay to receive donations sequentially.

For production, point OBS to `http://<server>:8000/overlay` and load `sleep-status` on a
separate monitor or dashboard.

## Donation tiers & configuration

Edit `config/settings.json` to define:

- `queue_delay_seconds` – minimum delay between alerts.
- `sleep_mode` – timezone-aware quiet hours.
- `tiers` – per-tier messaging, animation class, sound file, and motor index.
- `serial` – toggle Arduino integration and specify port/baud rate.

Place tier-specific sounds in `static/sounds/` and optional CSS animation files in
`static/animations/`. Relative paths inside the configuration are resolved relative to the
`static/` directory. For example, `sounds/tier2.mp3` resolves to `static/sounds/tier2.mp3`.

## Arduino deployment

1. Open `arduino/cat_feeder.ino` inside the Arduino IDE.
2. Connect your Nano, select the proper board and port.
3. Upload the sketch.
4. Wire motors/servos/relays to the pins listed in the sketch (default: D2–D6).
5. Confirm the Nano appears as a serial device (e.g., `/dev/ttyUSB0`). Update the path inside
   `config/settings.json` if necessary.

The sketch listens for newline-terminated commands like `MOTOR:2` and keeps each motor active for
one second. Adjust `MOTOR_DURATION_MS` in the sketch if you need longer dispensing times.

## Sleep mode

The Python service disables Arduino triggers during the configured quiet hours. The overlay still
shows donation alerts, but no motors run. Check `/sleep-status` to confirm whether sleep mode is
currently active.

## Integration tips

- Pair the API with services like StreamElements, Streamlabs, or custom bots to forward donation
  events.
- Use a scheduler or cron job to toggle `serial.enabled` if you physically disconnect the feeder.
- Extend `static/js/overlay.js` to integrate with custom animations (e.g., Lottie) by loading
  additional scripts within the `applyAnimation` helper.

## Development

Run uvicorn with hot reload:

```bash
uvicorn cat_feeder.server:app --reload
```

Submit test donations with `httpie` or `curl`:

```bash
http POST http://localhost:8000/donations \
  username=Example platform=Twitch raw_amount="20 subs" value:=20 message="Tier 5 hype!"
```

## License

MIT
