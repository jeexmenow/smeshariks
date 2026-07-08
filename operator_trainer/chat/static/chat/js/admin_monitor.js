const adminMessagesContainer = document.getElementById('admin-messages-container');
const adminDialogIdInput = document.getElementById('admin-current-dialog-id');
const adminCommentForm = document.getElementById('admin-comment-form');
const adminCommentInput = document.getElementById('admin-comment-input');
const adminDialogTitle = document.getElementById('admin-dialog-title');
const adminOperatorLabel = document.getElementById('admin-operator-label');
const adminDialogScore = document.getElementById('admin-dialog-score');
const adminRatingForm = document.getElementById('admin-rating-form');
const adminScoreInput = document.getElementById('admin-score-input');
const adminScoreDescription = document.getElementById('admin-score-description');
const adminRatingSubmit = document.getElementById('admin-rating-submit');
const adminRatingStatus = document.getElementById('admin-rating-status');
const adminCsrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

document.addEventListener('DOMContentLoaded', () => {
    if (window.initialAdminDialogId) {
        loadAdminDialog(window.initialAdminDialogId);
    }
});

document.querySelectorAll('.admin-dialog-item').forEach((button) => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.admin-dialog-item').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        loadAdminDialog(button.dataset.dialogId);
    });
});

adminCommentForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const dialogId = adminDialogIdInput.value;
    const text = adminCommentInput.value.trim();
    if (!dialogId || !text) {
        return;
    }

    const response = await postAdminForm('/admin_send_comment/', { dialog_id: dialogId, text });
    const data = await response.json();
    if (data.status !== 'ok') {
        alert(data.message || 'Не удалось отправить комментарий');
        return;
    }
    adminCommentInput.value = '';
    appendAdminMessage(data.message);
});

adminRatingForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const dialogId = adminDialogIdInput.value;
    const score = adminScoreInput.value.trim();
    const description = adminScoreDescription.value.trim();
    if (!dialogId || !score) {
        showRatingStatus('Укажите оценку перед сохранением', 'error');
        return;
    }

    adminRatingSubmit.disabled = true;
    adminRatingSubmit.textContent = 'Сохраняем...';
    showRatingStatus('Сохраняем оценку...', 'pending');

    try {
        const response = await postAdminForm('/admin_rate_dialog/', {
            dialog_id: dialogId,
            score,
            description,
        });
        const data = await response.json();
        if (data.status !== 'ok') {
            showRatingStatus(data.message || 'Не удалось сохранить оценку', 'error');
            return;
        }

        adminDialogScore.textContent = `Оценка: ${data.score}%`;
        showRatingStatus(`Оценка сохранена: ${data.score}%`, 'success');
    } catch (error) {
        showRatingStatus('Не удалось сохранить оценку', 'error');
    } finally {
        adminRatingSubmit.disabled = false;
        adminRatingSubmit.textContent = 'Сохранить оценку';
    }
});

async function loadAdminDialog(dialogId) {
    const response = await postAdminForm('/get_dialog_data/', { dialog_id: dialogId });
    const data = await response.json();
    if (data.status !== 'ok') {
        return;
    }
    adminDialogIdInput.value = dialogId;
    adminOperatorLabel.textContent = `Диалог оператора ${data.operator_name || ''}`.trim();
    adminDialogTitle.textContent = data.dialog_title || data.training_panel?.title || `Диалог #${dialogId}`;
    adminDialogScore.textContent = data.dialog_score ? `Оценка: ${data.dialog_score}%` : 'Оценка еще не выставлена';
    adminScoreInput.value = data.dialog_score || '';
    adminScoreDescription.value = data.evaluation_description || '';
    showRatingStatus('', '');
    adminMessagesContainer.innerHTML = '';
    data.messages.forEach(appendAdminMessage);
}

function appendAdminMessage(message) {
    const div = document.createElement('div');
    div.className = `message ${message.sender === 'operator' ? 'operator' : message.sender === 'admin' ? 'admin' : message.sender === 'system' ? 'system' : 'client'} new-message`;
    div.innerHTML = `
        <div class="message-header">
            ${message.sender === 'system' ? '' : `<img src="${messageAvatar(message)}" alt="Аватар" class="message-avatar">`}
            <span class="message-sender">${senderLabel(message)}</span>
            <span class="message-time">${escapeHTML(message.timestamp || '')}</span>
        </div>
        <div class="message-text">${escapeHTML(message.text || '')}</div>
    `;
    adminMessagesContainer.appendChild(div);
    adminMessagesContainer.scrollTop = adminMessagesContainer.scrollHeight;
}

function senderLabel(message) {
    if (message.sender === 'operator') {
        return message.sender_name || 'Оператор';
    }
    if (message.sender === 'admin') {
        return message.sender_name || 'Администратор';
    }
    if (message.sender === 'system') {
        return 'Система';
    }
    return 'Клиент';
}

function messageAvatar(message) {
    if (message.sender === 'operator' || message.sender === 'admin') {
        return escapeAttribute(message.sender_avatar || 'https://github.com/identicons/default.png');
    }
    return escapeAttribute(message.client_avatar || 'https://api.dicebear.com/8.x/pixel-art/png?seed=client');
}

function showRatingStatus(message, type) {
    adminRatingStatus.textContent = message;
    adminRatingStatus.className = `admin-rating-status ${type ? `is-${type}` : ''}`;
}

function postAdminForm(url, payload) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': adminCsrfToken,
        },
        body: new URLSearchParams(payload).toString(),
    });
}

function escapeHTML(value) {
    return String(value).replace(/[&<>'"]/g, (tag) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;',
    }[tag]));
}

function escapeAttribute(value) {
    return escapeHTML(value).replace(/`/g, '&#96;');
}
