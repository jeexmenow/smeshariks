const userAvatar = window.userAvatar || 'https://github.com/identicons/default.png';
let dialogClientAvatar = window.dialogClientAvatar || 'https://api.dicebear.com/8.x/pixel-art/png?seed=client';
let currentClientName = window.currentClientName || 'Клиент';

const messagesContainer = document.getElementById('messages-container');
const dialogsPanel = document.getElementById('dialogs-panel');
const messageForm = document.getElementById('message-form');
const currentDialogId = document.getElementById('current-dialog-id');
const hintsContainer = document.getElementById('hints-container');
const hintButton = document.getElementById('hint-button');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const toggleButton = document.getElementById('toggle-button');
const typingIndicator = document.getElementById('typing-indicator');

document.addEventListener('DOMContentLoaded', () => {
    scrollToBottom();
    updateProgressIndicatorFromDom();

    if (window.innerWidth <= 720) {
        toggleButton.style.display = 'flex';
        toggleButton.addEventListener('click', () => {
            dialogsPanel.classList.toggle('open');
            toggleButton.textContent = dialogsPanel.classList.contains('open') ? '×' : '☰';
        });
    }
});

messageForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const messageInput = document.getElementById('message-input');
    const sendButton = messageForm.querySelector('button[type="submit"]');
    const message = messageInput.value.trim();
    if (!message || sendButton.disabled) {
        return;
    }

    const originalButtonContent = sendButton.innerHTML;
    sendButton.innerHTML = '<div class="spinner"></div>';
    sendButton.disabled = true;

    try {
        const response = await postForm('/send/', {
            text: message,
            dialog_id: currentDialogId.value,
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'ok') {
            throw new Error(data.message || `Ошибка сети: ${response.statusText}`);
        }

        messageInput.value = '';
        appendMessage({
            sender: 'operator',
            text: data.message,
            timestamp: data.timestamp,
            score: data.score,
            feedback: data.feedback,
        });

        if (data.new_message) {
            showTypingIndicator();
            await delay(Math.min(1200, Math.max(350, data.new_message.length * 20)));
            hideTypingIndicator();
            appendMessage({
                sender: 'client',
                text: data.new_message,
                timestamp: data.new_timestamp,
            });
        }

        if (data.completion_message) {
            appendMessage({
                sender: 'system',
                text: data.completion_message,
                timestamp: data.completion_timestamp,
            });
        }

        updateProgressIndicator(data.current_step, data.max_steps, data.continue_dialog);
        updateDialogs(data.dialogs);

        if (data.new_dialog_id) {
            setTimeout(() => switchDialog(data.new_dialog_id), 500);
        } else if (data.no_more_questions) {
            appendMessage({
                sender: 'system',
                text: 'Все доступные сценарии завершены. Отличная работа!',
                timestamp: data.completion_timestamp || '',
            });
        }
    } catch (error) {
        alert(`Не удалось отправить сообщение: ${error.message}`);
    } finally {
        hideTypingIndicator();
        sendButton.innerHTML = originalButtonContent;
        sendButton.disabled = false;
    }
});

dialogsPanel.addEventListener('click', async (event) => {
    const closeButton = event.target.closest('.close-button');
    if (closeButton) {
        event.stopPropagation();
        await closeDialog(closeButton.dataset.dialogId);
        return;
    }

    const dialogItem = event.target.closest('.dialog-item');
    if (!dialogItem || !dialogItem.dataset.dialogId) {
        return;
    }
    await switchDialog(dialogItem.dataset.dialogId);
});

hintButton.addEventListener('click', () => {
    hintsContainer.classList.toggle('active');
    hintButton.textContent = hintsContainer.classList.contains('active') ? 'Скрыть' : 'Показать';
});

async function switchDialog(dialogId) {
    const response = await postForm('/get_dialog_data/', { dialog_id: dialogId });
    const data = await response.json();
    if (!response.ok || data.status !== 'ok') {
        return;
    }

    currentDialogId.value = dialogId;
    dialogClientAvatar = data.client_avatar || dialogClientAvatar;
    renderMessages(data.messages);
    updateDialogs(data.dialogs);
    updateProgressIndicator(data.current_step, data.max_steps, data.is_multi_step);
    updateTrainingPanel(data.training_panel);
    await postForm('/mark_read/', { dialog_id: dialogId });
}

async function closeDialog(dialogId) {
    const response = await postForm('/close_dialog/', { dialog_id: dialogId });
    const data = await response.json();
    if (!response.ok || data.status !== 'ok') {
        return;
    }

    updateDialogs(data.dialogs || []);
    if (currentDialogId.value === dialogId) {
        const nextDialog = (data.dialogs || [])[0];
        if (nextDialog) {
            await switchDialog(nextDialog.id);
        } else {
            currentDialogId.value = '';
            messagesContainer.innerHTML = '<div class="empty-state">Нет активных диалогов</div>';
        }
    }
}

function renderMessages(messages) {
    messagesContainer.innerHTML = '';
    messages.forEach(appendMessage);
    scrollToBottom();
}

function appendMessage(message) {
    const div = document.createElement('div');
    div.className = `message ${message.sender === 'operator' ? 'operator' : message.sender === 'system' ? 'system' : 'client'} new-message`;
    div.innerHTML = `
        <div class="message-header">
            ${message.sender === 'system' ? '' : `<img src="${message.sender === 'operator' ? userAvatar : dialogClientAvatar}" alt="Аватар" class="message-avatar">`}
            <span class="message-sender">${senderLabel(message.sender)}</span>
            <span class="message-time">${escapeHTML(message.timestamp || '')}</span>
            ${message.score ? `<span class="score-pill">${message.score}%</span>` : ''}
        </div>
        <div class="message-text">${escapeHTML(message.text || '')}</div>
        ${message.feedback ? `<div class="message-feedback">${escapeHTML(message.feedback)}</div>` : ''}
        ${message.admin_comment ? `<div class="admin-comment">Комментарий администратора: ${escapeHTML(message.admin_comment)}</div>` : ''}
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
}

function updateDialogs(dialogsData) {
    dialogsPanel.innerHTML = `
        <div class="panel-heading">
            <span>Диалоги</span>
            <span class="counter">${dialogsData.length}</span>
        </div>
    `;

    if (!dialogsData.length) {
        dialogsPanel.insertAdjacentHTML('beforeend', '<div class="empty-state">Нет активных диалогов</div>');
        return;
    }

    dialogsData.forEach((dialog) => {
        const div = document.createElement('div');
        div.className = `dialog-item ${String(dialog.id) === String(currentDialogId.value) ? 'active' : ''} ${dialog.unread_count > 0 ? 'unread' : ''}`;
        div.dataset.dialogId = dialog.id;
        div.innerHTML = `
            <img src="${escapeAttribute(dialog.client_avatar)}" alt="Аватар клиента">
            <div class="dialog-info">
                <div class="client-name">${escapeHTML(dialog.client_name || 'Клиент')}</div>
                <div class="scenario-name">${escapeHTML(dialog.title || `Диалог #${dialog.id}`)}</div>
                <div class="last-message">${escapeHTML(dialog.last_message || '')}</div>
            </div>
            <button class="close-button" data-dialog-id="${dialog.id}" title="Закрыть диалог">&times;</button>
        `;
        dialogsPanel.appendChild(div);
    });
}

function updateTrainingPanel(panel) {
    if (!panel) {
        return;
    }

    currentClientName = panel.client_name || 'Клиент';
    setText('current-client-name', currentClientName);
    setText('current-client-status', panel.client_status || 'online');
    setText('scenario-title', panel.title || 'Тренировочный кейс');
    setText('scenario-difficulty', panel.difficulty || 'medium');
    setText('panel-title', panel.title || 'Тренировочный кейс');
    setText('panel-situation', panel.situation || 'Описание ситуации будет здесь.');
    setText('panel-goal', panel.goal || 'Помогите клиенту и корректно завершите диалог.');

    hintsContainer.innerHTML = '';
    const hints = panel.hints || [];
    if (!hints.length) {
        hintsContainer.innerHTML = '<div class="hint muted">Подсказок для этого шага нет.</div>';
    } else {
        hints.forEach((hint) => {
            const div = document.createElement('div');
            div.className = 'hint';
            div.textContent = hint;
            hintsContainer.appendChild(div);
        });
    }
    hintsContainer.classList.remove('active');
    hintButton.textContent = 'Показать';
}

function updateProgressIndicator(currentStep, maxSteps, isActive) {
    const progress = document.getElementById('progress-indicator');
    const label = document.getElementById('progress-label');
    const fill = document.getElementById('progress-fill');
    const total = Math.max(Number(maxSteps) || 1, 1);
    const current = Math.min(Math.max(Number(currentStep) || 1, 1), total);
    progress.classList.toggle('completed', !isActive);
    label.textContent = isActive ? `Шаг ${current} из ${total}` : 'Сценарий завершен';
    fill.style.width = `${Math.round((current / total) * 100)}%`;
}

function updateProgressIndicatorFromDom() {
    const label = document.getElementById('progress-label');
    if (!label) {
        return;
    }
}

function postForm(url, payload) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
        },
        body: new URLSearchParams(payload).toString(),
    });
}

function senderLabel(sender) {
    if (sender === 'operator') {
        return 'Вы';
    }
    if (sender === 'system') {
        return 'Система';
    }
    return currentClientName || 'Клиент';
}

function showTypingIndicator() {
    typingIndicator.classList.add('active');
}

function hideTypingIndicator() {
    typingIndicator.classList.remove('active');
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
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

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
