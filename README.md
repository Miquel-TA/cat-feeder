# Cat Feeder Automation

This project runs the interactive cat shelter stream that reacts to donations across
Twitch, YouTube, TikTok and other platforms via the Streamlabs socket API. Donations
are queued, displayed with custom animations/sounds, persisted to a database and used
to drive five food motors on an Arduino Nano.

## Features

* Configurable delayed queue that guarantees a minimum spacing between alerts.
* FastAPI powered overlay pages for OBS / streaming software.
  * `http://<host>:8080/` – donation overlay with animations and audio.
  * `http://<host>:8080/sleep` – live sleep-mode indicator page.
* Resilient Streamlabs socket listener with exponential back-off.
* Sleep mode window that pauses the Arduino motors automatically overnight.
* SQLite persistence for long-term donation history.
* Production-ready asyncio architecture with graceful shutdown and reconnection.

## Getting Started

1. Copy the sample configuration and update it with your credentials:

   ```bash
   cp config.example.yaml config.yaml
   ```

   Edit `config.yaml` and set:

   * `sources.streamlabs.socket_token` – Streamlabs socket API token that listens to
     Twitch, YouTube and TikTok events.
   * `arduino.port` – serial device for the Arduino Nano.
   * `tiers` – adjust thresholds, motor mapping, animation classes and audio assets.

2. Install Python dependencies (Python 3.11+ recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Start the service:

   ```bash
   python -m catfeeder.main --config config.yaml
   ```

4. In OBS/Streamlabs add a browser source pointing to `http://localhost:8080/` for the
   donation overlay and another pointing to `/sleep` to monitor the sleep schedule.

## Arduino Nano

Upload the sketch in `catfeeder/arduino/cat_feeder.ino` to the Arduino Nano. The
controller expects newline-terminated commands of the form `MOTOR:<id>` (1-5) and will
run the associated motor for one second. The `PING` command can be used as a health
check.

## Audio & Animations

Place tier specific audio files under `catfeeder/static/sounds/` (create the directory
if necessary). The front-end will automatically play the configured file when a
matching donation is displayed. If an asset is missing, a generated chime is used as a
fallback so alerts still emit audio.

Available animation classes: `pulse`, `glow`, `sparkle`. You can define additional CSS
animations in `catfeeder/static/css/donations.css` and reference them from `tiers`.

## Sleep Mode

The service automatically toggles sleep mode based on the configured time window and
timezone. During sleep mode, the Arduino controller ignores motor triggers but donation
alerts and logging continue. The `/sleep` page and WebSocket provide live status.

## Reliability Notes

* The Streamlabs socket listener retries with exponential back-off.
* Serial disconnections trigger automatic reconnection attempts.
* Queue failures re-schedule the donation with incremental back-off.
* On shutdown all background tasks are cancelled gracefully and the database connection
  is flushed.

## Requirements

See [`requirements.txt`](requirements.txt) for the full list of Python dependencies.
