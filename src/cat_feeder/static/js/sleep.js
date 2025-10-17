async function fetchStatus() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) {
      throw new Error('Status request failed');
    }
    const data = await response.json();
    const status = document.getElementById('status');
    const nextWake = document.getElementById('next-wake');
    if (data.sleep_mode) {
      status.textContent = 'Sleep mode is active. No feedings right now.';
    } else {
      status.textContent = 'Awake! Donations will trigger feedings.';
    }

    if (data.seconds_until_wake != null) {
      const minutes = Math.max(0, Math.round(data.seconds_until_wake / 60));
      if (minutes === 0) {
        nextWake.textContent = 'Ready for the next donation!';
      } else {
        nextWake.textContent = `Motors resume in approximately ${minutes} minute${minutes === 1 ? '' : 's'}.`;
      }
    } else {
      nextWake.textContent = '';
    }
  } catch (err) {
    document.getElementById('status').textContent = 'Unable to contact server. Retrying...';
    console.error(err);
  }
}

const pollInterval = parseInt(document.body.dataset.poll || '15', 10) * 1000;
fetchStatus();
setInterval(fetchStatus, Math.max(5000, pollInterval));
