const statusEl = document.getElementById('sleep-status');
const textEl = document.getElementById('status-text');
const nextTransitionEl = document.getElementById('next-transition');

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/sleep`);

    socket.addEventListener('message', (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'sleep') {
                update(data.payload);
            } else if (data.sleeping !== undefined) {
                update(data);
            }
        } catch (error) {
            console.error('Failed to parse sleep state', error);
        }
    });

    socket.addEventListener('close', () => {
        console.warn('Sleep socket closed, attempting reconnect');
        setTimeout(connect, 5000);
    });
}

function update(payload) {
    if (!payload) {
        return;
    }
    const sleeping = !!payload.sleeping;
    statusEl.dataset.sleeping = sleeping ? 'true' : 'false';
    textEl.textContent = sleeping ? 'Sleep mode active' : 'Feeding active';
    if (payload.next_transition) {
        nextTransitionEl.textContent = new Date(payload.next_transition).toLocaleString();
    }
}

connect();
