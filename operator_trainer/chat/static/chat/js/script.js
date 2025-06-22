// Глобальные переменные
const messagesContainer = document.getElementById('messages-container');
const dialogsPanel = document.getElementById('dialogs-panel');
const messageForm = document.getElementById('message-form');
const currentDialogId = document.getElementById('current-dialog-id');
const hintsContainer = document.getElementById('hints-container');
const hintButton = document.getElementById('hint-button');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const toggleButton = document.getElementById('toggle-button');

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    // Прокрутка вниз
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Инициализация функций
    updateChat(currentDialogId.value);
    updateDialogs();

    // Мобильная версия
    if (window.innerWidth <= 480) {
        toggleButton.style.display = 'flex';
        let isOpen = false;
        toggleButton.addEventListener('click', () => {
            isOpen = !isOpen;
            dialogsPanel.classList.toggle('open', isOpen);
            toggleButton.textContent = isOpen ? '×' : '☰';
        });
    }

    // Автоматическая прокрутка к полю ввода на мобильных устройствах
    const messageInput = document.getElementById('message-input');
    if (window.innerWidth <= 768) {
        messageInput.addEventListener('focus', function() {
            setTimeout(() => {
                this.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        });
    }
});

// Добавляем индикатор прогресса для многошаговых диалогов
function updateProgressIndicator(currentStep, maxSteps, isMultiStep) {
    let progressHtml = '';
    if (isMultiStep && maxSteps > 1) {
        progressHtml = `
            <div class="progress-indicator" style="
                background: #f8f9fa; 
                padding: 10px 20px; 
                margin: 10px 20px; 
                border-radius: 8px; 
                text-align: center;
                border: 1px solid #e9ecef;
            ">
                <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">
                    Шаг ${currentStep} из ${maxSteps}
                </div>
                <div style="
                    background: #e9ecef; 
                    height: 6px; 
                    border-radius: 3px; 
                    overflow: hidden;
                ">
                    <div style="
                        background: var(--primary-color); 
                        height: 100%; 
                        width: ${(currentStep / maxSteps) * 100}%; 
                        transition: width 0.3s ease;
                    "></div>
                </div>
            </div>
        `;
    }
    
    // Удаляем старый индикатор прогресса
    const oldProgress = document.querySelector('.progress-indicator');
    if (oldProgress) {
        oldProgress.remove();
    }
    
    // Добавляем новый индикатор прогресса
    if (progressHtml) {
        const chatContainer = document.querySelector('.chat-container');
        const messagesContainer = document.querySelector('.chat-messages');
        chatContainer.insertBefore(document.createRange().createContextualFragment(progressHtml), messagesContainer);
    }
}

// Отправка сообщения
messageForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    if (message) {
        fetch('/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `text=${encodeURIComponent(message)}&dialog_id=${currentDialogId.value}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                messageInput.value = '';

                // Добавляем сообщение оператора
                const operatorDiv = document.createElement('div');
                operatorDiv.className = 'message operator';
                operatorDiv.innerHTML = `
                    <div class="message-header">
                        <img src="{{ user.avatar|default:'https://i.pravatar.cc/150?img=15' }}" alt="Аватар" class="message-avatar">
                        <span class="message-sender">Вы</span>
                        <span class="message-time">${data.timestamp}</span>
                    </div>
                    ${data.message}
                `;
                messagesContainer.appendChild(operatorDiv);

                // Добавляем ответ клиента
                const clientDiv = document.createElement('div');
                clientDiv.className = 'message client';
                clientDiv.innerHTML = `
                    <div class="message-header">
                        <img src="{{ current_dialog.client_avatar }}" alt="Аватар" class="message-avatar">
                        <span class="message-sender">Клиент</span>
                        <span class="message-time">${data.new_timestamp}</span>
                    </div>
                    ${data.new_message}
                `;
                messagesContainer.appendChild(clientDiv);

                // Если диалог продолжается (многошаговый)
                if (data.continue_dialog) {
                    // Обновляем индикатор прогресса
                    updateProgressIndicator(data.current_step, data.max_steps, true);
                    
                    // Показываем уведомление о продолжении диалога
                    const continueDiv = document.createElement('div');
                    continueDiv.className = 'message completion';
                    continueDiv.style.backgroundColor = '#e3f2fd';
                    continueDiv.style.color = '#1976d2';
                    continueDiv.innerHTML = `
                        <div class="message-header">
                            <span class="message-sender">Система</span>
                            <span class="message-time">${data.new_timestamp}</span>
                        </div>
                        Диалог продолжается... Следующий шаг: ${data.current_step}/${data.max_steps}
                    `;
                    messagesContainer.appendChild(continueDiv);
                } else if (data.completion_message) {
                    // Добавляем сообщение о завершении диалога
                    const completionDiv = document.createElement('div');
                    completionDiv.className = 'message completion';
                    completionDiv.innerHTML = `
                        <div class="message-header">
                            <span class="message-sender">Система</span>
                            <span class="message-time">${data.completion_timestamp}</span>
                        </div>
                        ${data.completion_message}
                    `;
                    messagesContainer.appendChild(completionDiv);
                }

                messagesContainer.scrollTop = messagesContainer.scrollHeight;

                // Обновляем список диалогов
                updateDialogs(data.dialogs);

                // Если есть новый диалог, переключаемся на него
                if (data.new_dialog_id) {
                    currentDialogId.value = data.new_dialog_id;
                    updateDialogs();
                    setTimeout(() => {
                        updateChat(data.new_dialog_id);
                    }, 100);
                    document.getElementById('message-input').value = '';
                }

                // Если вопросов больше нет, показываем уведомление
                if (data.no_more_questions) {
                    const endDiv = document.createElement('div');
                    endDiv.className = 'message completion';
                    endDiv.innerHTML = `
                        <div class="message-header">
                            <span class="message-sender">Система</span>
                        </div>
                        Все вопросы завершены! Поздравляем!`;
                    messagesContainer.appendChild(endDiv);
                }
            }
        });
    }
});

// Обновление списка диалогов с переданными данными
function updateDialogs(dialogsData) {
    if (dialogsData) {
        dialogsPanel.innerHTML = '';
        dialogsData.forEach(d => {
            const div = document.createElement('div');
            div.className = `dialog-item ${d.id == currentDialogId.value ? 'active' : ''} ${d.unread_count > 0 ? 'unread' : ''}`;
            div.setAttribute('data-dialog-id', d.id);
            div.innerHTML = `
                <img src="${d.client_avatar}" alt="Аватар клиента">
                <div class="dialog-info">
                    <div class="client-name">Клиент #${d.id}</div>
                    <div class="last-message">${d.last_message}</div>
                </div>
                ${d.unread_count > 0 ? `<span class="unread-count">${d.unread_count}</span>` : ''}
                <button class="close-button" data-dialog-id="${d.id}">&times;</button>
            `;
            dialogsPanel.appendChild(div);
        });
    } else {
        // Обновление списка диалогов без данных
        fetch('/get_dialog_data/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `dialog_id=${currentDialogId.value}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                dialogsPanel.innerHTML = '';
                data.dialogs.forEach(d => {
                    const div = document.createElement('div');
                    div.className = `dialog-item ${d.id == currentDialogId.value ? 'active' : ''} ${d.unread_count > 0 ? 'unread' : ''}`;
                    div.setAttribute('data-dialog-id', d.id);
                    div.innerHTML = `
                        <img src="${d.client_avatar}" alt="Аватар клиента">
                        <div class="dialog-info">
                            <div class="client-name">Клиент #${d.id}</div>
                            <div class="last-message">${d.last_message}</div>
                        </div>
                        ${d.unread_count > 0 ? `<span class="unread-count">${d.unread_count}</span>` : ''}
                        <button class="close-button" data-dialog-id="${d.id}">&times;</button>
                    `;
                    dialogsPanel.appendChild(div);
                });
            }
        });
    }
}

// Переключение диалогов
dialogsPanel.addEventListener('click', (e) => {
    const dialogItem = e.target.closest('.dialog-item');
    if (dialogItem && !e.target.classList.contains('close-button')) {
        const dialogId = dialogItem.getAttribute('data-dialog-id');
        currentDialogId.value = dialogId;
        updateChat(dialogId);
        updateDialogs();
        // Сбрасываем непрочитанные для выбранного диалога
        fetch('/mark_read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `dialog_id=${dialogId}`
        }).then(() => updateDialogs());
    }
});

// Закрытие диалога
dialogsPanel.addEventListener('click', (e) => {
    const closeButton = e.target.closest('.close-button');
    if (closeButton) {
        const dialogId = closeButton.getAttribute('data-dialog-id');
        fetch('/close_dialog/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `dialog_id=${dialogId}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                updateDialogs();
                if (currentDialogId.value == dialogId) {
                    const firstDialog = Dialog.objects.filter(user=request.user, is_completed=False, is_closed=False).first();
                    if (firstDialog) {
                        currentDialogId.value = firstDialog.id;
                        updateChat(firstDialog.id);
                    } else {
                        messagesContainer.innerHTML = '<div class="message">Нет активных диалогов</div>';
                        hintsContainer.classList.remove('active');
                    }
                }
            }
        });
    }
});

// Обновление чата
function updateChat(dialogId) {
    fetch('/get_dialog_data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `dialog_id=${dialogId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            messagesContainer.innerHTML = '';
            data.messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `message ${msg.sender === 'operator' ? 'operator' : 'client'}`;
                div.innerHTML = `
                    <div class="message-header">
                        <img src="${msg.sender === 'operator' ? '{{ user.avatar|default:"https://i.pravatar.cc/150?img=15" }}' : data.dialogs.find(d => d.id == dialogId).client_avatar}" alt="Аватар" class="message-avatar">
                        <span class="message-sender">${msg.sender === 'operator' ? 'Вы' : 'Клиент'}</span>
                        <span class="message-time">${msg.timestamp}</span>
                        ${msg.step_number > 1 ? `<span class="step-indicator" style="font-size: 10px; color: #999;">Шаг ${msg.step_number}</span>` : ''}
                    </div>
                    ${msg.text}
                    ${msg.admin_comment ? `<div class="admin-comment" style="font-size: 12px; color: #666; margin-top: 5px;">Комментарий администратора: ${msg.admin_comment}</div>` : ''}
                `;
                messagesContainer.appendChild(div);
            });
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            hintsContainer.classList.remove('active'); // Скрываем подсказки при переключении
            
            // Обновляем индикатор прогресса
            if (data.is_multi_step) {
                updateProgressIndicator(data.current_step, data.max_steps, true);
            } else {
                // Удаляем индикатор прогресса для обычных диалогов
                const oldProgress = document.querySelector('.progress-indicator');
                if (oldProgress) {
                    oldProgress.remove();
                }
            }
        }
    });
}

// Показ/скрытие подсказок при клике на кнопку
hintButton.addEventListener('click', () => {
    hintsContainer.classList.toggle('active');
});

// Переключение темы
document.getElementById('theme-toggle').onclick = function() {
    document.body.classList.toggle('dark');
}; 