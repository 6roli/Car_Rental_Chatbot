// Sends messages to /chat and shows replies. Text is inserted with textContent,
// never as HTML, so a model reply cannot inject markup into the page.
const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');
const sendButton = document.getElementById('send');

function addMessage(text, kind) {
  const element = document.createElement('div');
  element.className = `message message--${kind}`;
  element.textContent = text;
  chat.append(element);
  element.scrollIntoView({ block: 'end' });
  return element;
}

async function send(message) {
  addMessage(message, 'user');
  const pending = addMessage('Thinking…', 'bot');
  pending.classList.add('message--pending');
  sendButton.disabled = true;
  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await response.json().catch(() => ({}));
    pending.textContent = data.reply ?? data.error ?? `Unexpected answer from the server (${response.status}).`;
    if (!data.reply) pending.classList.add('message--error');
  } catch {
    pending.textContent = 'Could not reach the server. Check your connection and try again.';
    pending.classList.add('message--error');
  } finally {
    pending.classList.remove('message--pending');
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  void send(message);
});

document.querySelectorAll('[data-example]').forEach((button) => {
  button.addEventListener('click', () => void send(button.dataset.example));
});
