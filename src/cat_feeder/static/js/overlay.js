const socket = new WebSocket(`ws://${window.location.host}/ws/overlay`);
const alertBox = document.getElementById('alert');
const username = document.getElementById('username');
const tier = document.getElementById('tier');
const message = document.getElementById('message');
const sound = document.getElementById('tier-sound');
let hideTimeout = null;

socket.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'donation') {
    showDonation(data.payload);
  }
});

socket.addEventListener('close', () => {
  console.warn('Overlay websocket closed, retrying in 3s');
  setTimeout(() => window.location.reload(), 3000);
});

function showDonation(payload) {
  clearTimeout(hideTimeout);
  alertBox.className = 'show ' + payload.animation;
  username.textContent = `${payload.username}`;
  tier.textContent = `${payload.tier_name} • ${payload.coins} coins`;
  message.textContent = payload.message;
  if (payload.sound) {
    if (payload.sound.startsWith('tone:')) {
      playTone(payload.sound.split(':')[1]);
    } else {
      sound.src = payload.sound;
      sound.currentTime = 0;
      sound.play().catch(() => {});
    }
  }
  hideTimeout = setTimeout(() => {
    alertBox.className = 'hidden';
  }, 7000);
}

function playTone(tierName) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  const tier = parseInt(tierName.replace(/\D/g, ''), 10) || 1;
  const baseFrequency = 440;
  oscillator.type = 'sine';
  oscillator.frequency.value = baseFrequency + tier * 80;
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  gain.gain.setValueAtTime(0.2, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
  oscillator.start();
  oscillator.stop(ctx.currentTime + 1.2);
}
