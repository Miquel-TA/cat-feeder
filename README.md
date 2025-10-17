# Cat Feeder

Production-ready donation-driven cat feeder integrating TikTok Live alerts, OBS overlays, and an Arduino Nano.

## Features

- Connects to TikTok Live (via [`tiktoklive`](https://github.com/TikTokLive/TikTokLive)) to capture gifts, subscriptions, and follows.
- Persists every donation in SQLite for auditing and recovery.
- Queues alerts with configurable spacing to avoid overlap.
- Serves animated HTML overlays for OBS and a sleep-mode dashboard via FastAPI.
- Triggers one of five Arduino-controlled motors depending on donation tier.
- Sleep mode schedule ensures the feeder stays silent overnight while still displaying on-stream alerts.

## Getting Started

1. Install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a configuration file (optional) or export environment variables:

   ```bash
   export TIKTOK_USERNAME=your_tiktok_username
   export ARDUINO_PORT=/dev/ttyUSB0  # or COM3 on Windows
   ```

   Additional configuration values are documented in `src/cat_feeder/config.py`.

3. Run the service:

   ```bash
   python -m cat_feeder.main
   ```

   The web server listens on `http://0.0.0.0:8000`:

   - `http://localhost:8000/overlay` – OBS browser source (1920x1080 transparent background).
   - `http://localhost:8000/sleep` – sleep-mode monitor page.

4. Add a browser source in OBS pointing at the overlay URL.

5. Upload the Arduino sketch in `arduino/cat_feeder.ino` to your Arduino Nano.

## Sleep Mode

Sleep mode is configured by start/end times (24-hour clock) in the configured timezone. During sleep mode the overlay still displays alerts, but Arduino triggers are suppressed to keep the shelter quiet.

## Reliability

- Automatic reconnection to TikTok Live on network hiccups.
- Serial auto-detection if the Arduino changes ports.
- Durable SQLite logging for all donations.

## Development

```bash
ruff check .
pytest
```

Tests and linting are not provided but hooks are ready for integration.
