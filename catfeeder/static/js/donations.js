const donationContainer = document.getElementById('donation-container');
const placeholder = donationContainer.querySelector('.placeholder');
const audioPlayer = document.getElementById('audio-player');

const queue = [];
let processing = false;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/donations`);

    socket.addEventListener('open', () => console.log('Donation socket connected'));
    socket.addEventListener('close', () => {
        console.warn('Donation socket disconnected, retrying in 3s');
        setTimeout(connectWebSocket, 3000);
    });
    socket.addEventListener('message', (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'donation') {
                enqueueDonation(data.payload);
            }
        } catch (error) {
            console.error('Failed to parse donation message', error);
        }
    });

    return socket;
}

function enqueueDonation(donation) {
    queue.push(donation);
    if (!processing) {
        processNext();
    }
}

async function processNext() {
    if (queue.length === 0) {
        processing = false;
        if (placeholder) {
            placeholder.style.display = 'block';
        }
        return;
    }

    processing = true;
    if (placeholder) {
        placeholder.style.display = 'none';
    }

    const donation = queue.shift();
    await displayDonation(donation);
    processNext();
}

async function displayDonation(donation) {
    const card = document.createElement('div');
    card.classList.add('donation-card');
    if (donation.name) {
        card.classList.add(`tier-${donation.name.toLowerCase().replace(/\s+/g, '-')}`);
    }
    if (donation.animation) {
        card.classList.add(donation.animation);
    }

    const donorNote = donation.donor_note ? `<div class="note">${donation.donor_note}</div>` : '';
    card.innerHTML = `
        <div class="platform">${donation.platform}</div>
        <div class="amount">${donation.amount} ${donation.currency}</div>
        <div class="message">${donation.message}</div>
        ${donorNote}
        <div class="user">${donation.username}</div>
    `;

    donationContainer.innerHTML = '';
    donationContainer.appendChild(card);

    playSound(donation.sound);

    const duration = donation.duration ? donation.duration * 1000 : 6000;
    await new Promise((resolve) => setTimeout(resolve, duration));
}

function playSound(sound) {
    if (!sound) {
        playFallbackTone();
        return;
    }
    if (sound.startsWith('http') || sound.startsWith('/')) {
        audioPlayer.src = sound;
        audioPlayer.currentTime = 0;
        audioPlayer.play().catch(() => playFallbackTone());
    } else {
        // treat as relative static path
        audioPlayer.src = `/static/sounds/${sound}`;
        audioPlayer.currentTime = 0;
        audioPlayer.play().catch(() => playFallbackTone());
    }
}

function playFallbackTone() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.frequency.value = 880;
        oscillator.type = 'sine';
        oscillator.connect(gain);
        gain.connect(ctx.destination);
        gain.gain.setValueAtTime(0.0001, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.05);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.2);
        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + 1.2);
    } catch (error) {
        console.error('Unable to play fallback tone', error);
    }
}

connectWebSocket();
