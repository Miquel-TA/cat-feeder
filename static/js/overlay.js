const alertElement = document.getElementById('alert');
const messageElement = document.getElementById('alert-message');
const metaElement = document.getElementById('alert-meta');
const animationElement = document.getElementById('animation');
const soundElement = document.getElementById('alert-sound');

const DISPLAY_TIME = 7000;
let hideTimeout = null;
let dynamicStylesheet = null;

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socketUrl = `${protocol}://${location.host}/ws/alerts`;
  const ws = new WebSocket(socketUrl);

  ws.addEventListener('message', (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'donation') {
        showAlert(payload.data);
      }
    } catch (error) {
      console.error('Failed to process websocket message', error);
    }
  });

  ws.addEventListener('close', () => {
    console.warn('Websocket closed. Reconnecting soon…');
    setTimeout(connect, 3000);
  });

  ws.addEventListener('error', (error) => {
    console.error('Websocket error', error);
    ws.close();
  });
}

function showAlert(data) {
  const { display_message, platform, username, raw_amount, tier, sound, animation } = data;
  messageElement.textContent = display_message || 'Thank you for supporting the cats!';
  metaElement.textContent = `${username} — ${platform} — ${raw_amount}`;

  applyAnimation(tier, animation);
  playSound(sound);

  alertElement.classList.remove('hidden');
  alertElement.classList.add('visible');

  if (hideTimeout) {
    clearTimeout(hideTimeout);
  }
  hideTimeout = setTimeout(() => {
    alertElement.classList.remove('visible');
    alertElement.classList.add('hidden');
  }, DISPLAY_TIME);
}

function applyAnimation(tier, animation) {
  animationElement.className = 'animation';
  if (tier) {
    animationElement.classList.add(tier);
  }

  if (dynamicStylesheet) {
    dynamicStylesheet.remove();
    dynamicStylesheet = null;
  }

  if (animation && animation.endsWith('.css')) {
    dynamicStylesheet = document.createElement('link');
    dynamicStylesheet.rel = 'stylesheet';
    if (animation.startsWith('http')) {
      dynamicStylesheet.href = animation;
    } else if (animation.startsWith('/')) {
      dynamicStylesheet.href = animation;
    } else {
      dynamicStylesheet.href = `/static/${animation}`;
    }
    document.head.appendChild(dynamicStylesheet);
  } else if (animation) {
    animationElement.classList.add(animation);
  }
}

function playSound(soundPath) {
  if (!soundPath) {
    return;
  }
  let src = soundPath;
  if (!soundPath.startsWith('http')) {
    src = soundPath.startsWith('/') ? soundPath : `/static/${soundPath}`;
  }
  if (soundElement.getAttribute('src') !== src) {
    soundElement.setAttribute('src', src);
  }
  soundElement.currentTime = 0;
  soundElement.play().catch((error) => {
    console.warn('Unable to play alert sound', error);
  });
}

connect();
