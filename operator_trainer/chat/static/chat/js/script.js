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
const templateSuggestions = document.getElementById('template-suggestions');
const toastContainer = document.getElementById('toast-container');
let templateSearchTimer = null;
let currentDialogTab = document.querySelector('.dialog-tab.active')?.dataset.tab || 'open';
let cachedDialogs = window.initialDialogs || [];

document.addEventListener('DOMContentLoaded', () => {
    scrollToBottom();
    updateProgressIndicatorFromDom();
    renderInitialProgressDots();
    updateComposerState(window.initialCanSend);

    if (window.innerWidth <= 720) {
        toggleButton.style.display = 'flex';
        toggleButton.addEventListener('click', () => {
            dialogsPanel.classList.toggle('open');
            toggleButton.textContent = dialogsPanel.classList.contains('open') ? '×' : '☰';
        });
    }
});

const messageInput = document.getElementById('message-input');
messageInput.addEventListener('input', () => {
    clearTimeout(templateSearchTimer);
    templateSearchTimer = setTimeout(() => loadTemplateSuggestions(messageInput.value), 220);
});

document.addEventListener('click', (event) => {
    if (!event.target.closest('.message-input-wrap')) {
        hideTemplateSuggestions();
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
            sender_avatar: data.sender_avatar || userAvatar,
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

        if (data.new_dialog_id) {
            currentDialogTab = 'open';
            updateDialogs(data.dialogs);
            setTimeout(() => switchDialog(data.new_dialog_id), 500);
        } else if (data.no_more_questions) {
            currentDialogTab = 'archive';
            updateDialogs(data.dialogs);
            appendMessage({
                sender: 'system',
                text: 'Все доступные сценарии завершены. Отличная работа!',
                timestamp: data.completion_timestamp || '',
            });
        } else {
            updateDialogs(data.dialogs);
        }
    } catch (error) {
        showToast(`Не удалось отправить сообщение: ${error.message}`, 'error');
    } finally {
        hideTypingIndicator();
        sendButton.innerHTML = originalButtonContent;
        sendButton.disabled = false;
    }
});

dialogsPanel.addEventListener('click', async (event) => {
    const tabButton = event.target.closest('.dialog-tab');
    if (tabButton) {
        currentDialogTab = tabButton.dataset.tab;
        updateDialogs(cachedDialogs);
        return;
    }

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

if (hintButton) {
    hintButton.addEventListener('click', () => {
        hintsContainer.classList.toggle('active');
        hintButton.textContent = hintsContainer.classList.contains('active') ? 'Скрыть' : 'Показать';
    });
}

async function switchDialog(dialogId) {
    showChatSkeleton();
    const response = await postForm('/get_dialog_data/', { dialog_id: dialogId });
    const data = await response.json();
    if (!response.ok || data.status !== 'ok') {
        hideChatSkeleton();
        showToast('Не удалось открыть диалог', 'error');
        return;
    }

    currentDialogId.value = dialogId;
    dialogClientAvatar = data.client_avatar || dialogClientAvatar;
    setImage('current-client-avatar', dialogClientAvatar);
    renderMessages(data.messages);
    updateDialogs(data.dialogs);
    updateProgressIndicator(data.current_step, data.max_steps, data.is_multi_step);
    updateTrainingPanel(data.training_panel);
    updateOperatorEvaluation(data);
    updateComposerState(data.can_send);
    await postForm('/mark_read/', { dialog_id: dialogId });
    hideChatSkeleton();
}

async function closeDialog(dialogId) {
    const response = await postForm('/close_dialog/', { dialog_id: dialogId });
    const data = await response.json();
    if (!response.ok || data.status !== 'ok') {
        showToast(data.message || 'Не удалось закрыть диалог', 'error');
        return;
    }

    if (currentDialogId.value === dialogId) {
        const dialogs = data.dialogs || [];
        const nextDialog = data.new_dialog_id
            ? { id: data.new_dialog_id, is_archived: false }
            : dialogs.find((dialog) => !dialog.is_archived) || dialogs.find((dialog) => dialog.is_archived);
        if (nextDialog) {
            currentDialogTab = nextDialog.is_archived ? 'archive' : 'open';
            updateDialogs(dialogs);
            await switchDialog(nextDialog.id);
        } else {
            currentDialogId.value = '';
            messagesContainer.innerHTML = '<div class="empty-state">Нет активных диалогов</div>';
            updateDialogs(dialogs);
        }
    } else {
        updateDialogs(data.dialogs || []);
    }
}

function renderMessages(messages) {
    messagesContainer.innerHTML = '';
    messages.forEach(appendMessage);
    scrollToBottom();
}

function appendMessage(message) {
    const div = document.createElement('div');
    div.className = `message ${message.sender === 'operator' ? 'operator' : message.sender === 'admin' ? 'admin' : message.sender === 'system' ? 'system' : 'client'} new-message`;
    div.innerHTML = `
        <div class="message-header">
            ${message.sender === 'system' ? '' : `<img src="${messageAvatar(message)}" alt="Аватар" class="message-avatar">`}
            <span class="message-sender">${message.sender === 'admin' && message.sender_name ? escapeHTML(message.sender_name) : senderLabel(message.sender)}</span>
            <span class="message-time">${escapeHTML(message.timestamp || '')}</span>
            ${message.score ? `<span class="score-pill">${message.score}%</span>` : ''}
        </div>
        <div class="message-text">${escapeHTML(message.text || '')}</div>
        ${message.admin_comment ? `<div class="admin-comment">Комментарий администратора: ${escapeHTML(message.admin_comment)}</div>` : ''}
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
}

function updateDialogs(dialogsData) {
    cachedDialogs = dialogsData || [];
    const visibleDialogs = cachedDialogs.filter((dialog) => (
        currentDialogTab === 'archive' ? dialog.is_archived : !dialog.is_archived
    ));
    dialogsPanel.innerHTML = `
        <div class="panel-heading">
            <span>Диалоги</span>
            <span class="counter">${visibleDialogs.length}</span>
        </div>
        <div class="dialog-tabs" id="dialog-tabs">
            <button type="button" class="dialog-tab ${currentDialogTab === 'open' ? 'active' : ''}" data-tab="open">Открытые</button>
            <button type="button" class="dialog-tab ${currentDialogTab === 'archive' ? 'active' : ''}" data-tab="archive">Архив</button>
        </div>
    `;

    if (!visibleDialogs.length) {
        dialogsPanel.insertAdjacentHTML('beforeend', `<div class="empty-state">${currentDialogTab === 'archive' ? 'Нет диалогов в архиве' : 'Нет открытых диалогов'}</div>`);
        return;
    }

    visibleDialogs.forEach((dialog) => {
        const div = document.createElement('div');
        div.className = `dialog-item status-${dialog.status || 'active'} ${dialog.needs_operator_response ? 'needs-response' : ''} ${String(dialog.id) === String(currentDialogId.value) ? 'active' : ''} ${dialog.unread_count > 0 ? 'unread' : ''}`;
        div.dataset.dialogId = dialog.id;
        div.innerHTML = `
            <img src="${escapeAttribute(dialog.client_avatar)}" alt="Аватар клиента">
            <div class="dialog-info">
                <div class="client-name">${escapeHTML(dialog.client_name || 'Клиент')}</div>
                <div class="scenario-name">${escapeHTML(dialog.title || `Диалог #${dialog.id}`)}</div>
                <div class="last-message">${escapeHTML(dialog.last_message || '')}</div>
                ${dialog.has_admin_evaluation ? `<div class="dialog-evaluation-mini">Оценка: ${escapeHTML(dialog.evaluation_score)}%</div>` : ''}
            </div>
            ${dialog.can_close ? `<button class="close-button" data-dialog-id="${dialog.id}" title="Закрыть диалог">&times;</button>` : `<span class="dialog-status-badge">${escapeHTML(dialog.status_label || 'Закрыт')}</span>`}
        `;
        dialogsPanel.appendChild(div);
    });
}

function updateOperatorEvaluation(data) {
    const card = document.getElementById('operator-evaluation-card');
    const score = document.getElementById('operator-evaluation-score');
    const description = document.getElementById('operator-evaluation-description');
    if (!card || !score || !description) {
        return;
    }

    card.hidden = !data.has_admin_evaluation;
    if (data.has_admin_evaluation) {
        score.textContent = `${data.evaluation_score}%`;
        description.textContent = data.evaluation_description || 'Без описания';
    }
}

function updateComposerState(canSend) {
    const sendButton = messageForm.querySelector('button[type="submit"]');
    const isEnabled = Boolean(canSend);
    messageInput.disabled = !isEnabled;
    sendButton.disabled = !isEnabled;
    messageInput.placeholder = isEnabled ? 'Ответ клиенту от вашего имени...' : 'Диалог закрыт или завершен, доступен только просмотр';
}

function updateTrainingPanel(panel) {
    if (!panel) {
        return;
    }

    currentClientName = panel.client_name || 'Клиент';
    setText('current-client-name', currentClientName);
    setText('current-client-status', panel.client_status || 'online');
    setText('panel-title', panel.title || 'Тренировочный кейс');
    setText('panel-situation', panel.situation || 'Описание ситуации будет здесь.');
    setText('panel-goal', panel.goal || 'Помогите клиенту и корректно завершите диалог.');

    hintsContainer.innerHTML = '<div class="hint reminder-accent">Ориентируйтесь на проблему клиента и цель кейса. Не просите лишние данные и ведите диалог как в реальной поддержке.</div>';
    const hints = panel.hints || [];
    if (!hints.length) {
        hintsContainer.insertAdjacentHTML('beforeend', '<div class="hint muted">Дополнительных напоминаний для этого шага нет.</div>');
    } else {
        hints.forEach((hint) => {
            const div = document.createElement('div');
            div.className = 'hint';
            div.textContent = hint;
            hintsContainer.appendChild(div);
        });
    }
    hintsContainer.classList.add('active');
    if (hintButton) {
        hintButton.textContent = 'Показать';
    }
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
    renderProgressDots(current, total, isActive);
}

function updateProgressIndicatorFromDom() {
    const label = document.getElementById('progress-label');
    if (!label) {
        return;
    }
}

function renderInitialProgressDots() {
    const dots = document.getElementById('progress-dots');
    if (!dots) {
        return;
    }
    renderProgressDots(Number(dots.dataset.current) || 1, Number(dots.dataset.total) || 1, true);
}

function renderProgressDots(current, total, isActive) {
    const dots = document.getElementById('progress-dots');
    if (!dots) {
        return;
    }
    dots.innerHTML = '';
    for (let index = 1; index <= total; index += 1) {
        const dot = document.createElement('span');
        dot.className = `progress-dot ${index < current || !isActive ? 'done' : ''} ${index === current && isActive ? 'current' : ''}`;
        dot.textContent = index;
        dots.appendChild(dot);
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
    if (sender === 'admin') {
        return 'Администратор';
    }
    if (sender === 'system') {
        return 'Система';
    }
    return currentClientName || 'Клиент';
}

function messageAvatar(message) {
    if (message.sender === 'operator' || message.sender === 'admin') {
        return escapeAttribute(message.sender_avatar || userAvatar);
    }
    return escapeAttribute(dialogClientAvatar);
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

function setImage(id, value) {
    const element = document.getElementById(id);
    if (element && value) {
        element.src = value;
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

async function loadTemplateSuggestions(query) {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
        hideTemplateSuggestions();
        return;
    }

    const response = await fetch(`/template_suggestions/?q=${encodeURIComponent(trimmed)}`);
    const data = await response.json();
    if (data.status !== 'ok' || !data.templates.length) {
        hideTemplateSuggestions();
        return;
    }

    templateSuggestions.innerHTML = '';
    data.templates.forEach((template, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'template-suggestion';
        button.innerHTML = `
            <span class="template-count">${index + 1}</span>
            <span class="template-body">
                <span class="template-title">${highlightMatch(template.title, trimmed)}</span>
                ${template.category ? `<span class="template-separator">|</span><span class="template-category">${escapeHTML(template.category)}</span>` : ''}
                <span class="template-preview">${highlightMatch(template.text.slice(0, 180), trimmed)}${template.text.length > 180 ? '...' : ''}</span>
            </span>
            <span class="template-close" aria-hidden="true">×</span>
        `;
        button.addEventListener('click', (event) => {
            if (event.target.closest('.template-close')) {
                button.remove();
                if (!templateSuggestions.children.length) {
                    hideTemplateSuggestions();
                }
                return;
            }
            messageInput.value = template.text;
            hideTemplateSuggestions();
            messageInput.focus();
        });
        templateSuggestions.appendChild(button);
    });
    templateSuggestions.classList.add('active');
}

function hideTemplateSuggestions() {
    templateSuggestions.classList.remove('active');
    templateSuggestions.innerHTML = '';
}

function showChatSkeleton() {
    messagesContainer.classList.add('is-loading');
    messagesContainer.innerHTML = `
        <div class="skeleton-message"></div>
        <div class="skeleton-message short"></div>
        <div class="skeleton-message right"></div>
    `;
}

function hideChatSkeleton() {
    messagesContainer.classList.remove('is-loading');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.classList.add('visible'), 20);
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 220);
    }, 3200);
}

function highlightMatch(value, query) {
    const escaped = escapeHTML(value || '');
    const cleanQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (!cleanQuery) {
        return escaped;
    }
    return escaped.replace(new RegExp(`(${cleanQuery})`, 'ig'), '<mark>$1</mark>');
}
