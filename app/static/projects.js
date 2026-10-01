(() => {
  const board = document.querySelector('.kanban');
  const message = document.getElementById('board-message');
  if (!board || !message) return;
  let moving = false;
  let dragged = null;
  board.addEventListener('dragstart', event => {
    const card = event.target.closest('.kanban-card[draggable="true"]');
    if (!card || moving) { event.preventDefault(); return; }
    dragged = card;
    event.dataTransfer.setData('text/plain', card.dataset.card);
    event.dataTransfer.effectAllowed = 'move';
    card.classList.add('dragging');
  });
  board.addEventListener('dragend', () => {
    if (dragged) dragged.classList.remove('dragging');
    dragged = null;
    board.querySelectorAll('.drop-target').forEach(column => column.classList.remove('drop-target'));
  });
  board.querySelectorAll('.kanban-column').forEach(column => {
    column.addEventListener('dragover', event => {
      if (!dragged || moving) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      column.classList.add('drop-target');
    });
    column.addEventListener('dragleave', event => {
      if (!column.contains(event.relatedTarget)) column.classList.remove('drop-target');
    });
    column.addEventListener('drop', async event => {
      event.preventDefault();
      column.classList.remove('drop-target');
      if (!dragged || moving) return;
      const card = dragged;
      if (card.closest('.kanban-column') === column) return;
      moving = true;
      message.className = 'muted';
      message.textContent = 'Karte wird verschoben …';
      try {
        const data = new URLSearchParams({status: column.dataset.status, revision: card.dataset.revision});
        const response = await fetch(`/projects/${board.dataset.project}/cards/${card.dataset.card}/move`, {method: 'POST', credentials: 'same-origin', headers: {'Accept': 'application/json'}, body: data});
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(typeof result.detail === 'string' ? result.detail : 'Verschieben nicht möglich. Bitte Seite neu laden.');
        }
        window.location.reload();
      } catch (error) {
        message.className = 'error';
        message.textContent = error.message || 'Verbindung fehlgeschlagen. Bitte neu laden und den Kartenstatus prüfen.';
      } finally {
        moving = false;
      }
    });
  });
})();
