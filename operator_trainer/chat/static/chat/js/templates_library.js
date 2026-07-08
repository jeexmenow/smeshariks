const searchInput = document.getElementById('template-library-search');
const categorySelect = document.getElementById('template-library-category');
const langSelect = document.getElementById('template-library-lang');
const attachSelect = document.getElementById('template-library-attach');
const chipsContainer = document.getElementById('template-library-chips');
const grid = document.getElementById('template-library-grid');
const countElement = document.getElementById('template-library-count');
const totalElement = document.getElementById('template-library-total');
const pageElement = document.getElementById('template-library-page');
const emptyElement = document.getElementById('template-library-empty');
const prevButton = document.getElementById('template-library-prev');
const nextButton = document.getElementById('template-library-next');
const modalBackdrop = document.getElementById('template-modal-backdrop');
const modalTitle = document.getElementById('template-modal-title');
const modalMeta = document.getElementById('template-modal-meta');
const modalCategories = document.getElementById('template-modal-categories');
const modalText = document.getElementById('template-modal-text');
const modalAttachments = document.getElementById('template-modal-attachments');
const modalClose = document.getElementById('template-modal-close');
const modalCopy = document.getElementById('template-modal-copy');
const toastContainer = document.getElementById('toast-container');

const perPage = 25;
let templates = [];
let filtered = [];
let activeTemplate = null;
let state = {
    query: '',
    category: 'all',
    lang: 'all',
    attach: 'all',
    page: 1,
};

document.addEventListener('DOMContentLoaded', loadTemplates);
searchInput.addEventListener('input', () => {
    state.query = searchInput.value;
    state.page = 1;
    render();
});
categorySelect.addEventListener('change', () => {
    state.category = categorySelect.value;
    state.page = 1;
    render();
});
langSelect.addEventListener('change', () => {
    state.lang = langSelect.value;
    state.page = 1;
    render();
});
attachSelect.addEventListener('change', () => {
    state.attach = attachSelect.value;
    state.page = 1;
    render();
});
prevButton.addEventListener('click', () => {
    if (state.page > 1) {
        state.page -= 1;
        render();
    }
});
nextButton.addEventListener('click', () => {
    const maxPage = getMaxPage();
    if (state.page < maxPage) {
        state.page += 1;
        render();
    }
});
modalClose.addEventListener('click', closeModal);
modalBackdrop.addEventListener('click', (event) => {
    if (event.target === modalBackdrop) {
        closeModal();
    }
});
modalCopy.addEventListener('click', () => {
    if (activeTemplate) {
        copyText(stripTalkmeMarkup(activeTemplate.text));
    }
});
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeModal();
    }
});

async function loadTemplates() {
    grid.innerHTML = '<div class="empty-state">Загружаем шаблоны Talk-Me...</div>';
    try {
        const response = await fetch(window.talkmeTemplatesSource);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        templates = window.talkmeTemplatesSource.endsWith('.json')
            ? await response.json()
            : extractData(await response.text());
        populateFilters();
        render();
    } catch (error) {
        grid.innerHTML = '<div class="empty-state">Не удалось загрузить шаблоны. Проверьте доступ к GitHub.</div>';
        showToast('Не удалось загрузить шаблоны', 'error');
    }
}

function extractData(html) {
    const dataMatch = html.match(/const DATA = (\[[\s\S]*?\]);\s*const CATEGORIES =/);
    if (!dataMatch) {
        throw new Error('DATA not found');
    }
    return JSON.parse(dataMatch[1]);
}

function populateFilters() {
    const categories = [...new Set(templates.flatMap((item) => item.categories || [item.category]).filter(Boolean))].sort();
    const languages = [...new Set(templates.map((item) => item.lang).filter(Boolean))].sort();

    categorySelect.innerHTML = '<option value="all">Все категории</option>';
    categories.forEach((category) => {
        categorySelect.insertAdjacentHTML('beforeend', `<option value="${escapeAttribute(category)}">${escapeHTML(category)}</option>`);
    });

    langSelect.innerHTML = '<option value="all">Все языки</option>';
    languages.forEach((lang) => {
        langSelect.insertAdjacentHTML('beforeend', `<option value="${escapeAttribute(lang)}">${escapeHTML(lang)}</option>`);
    });

    chipsContainer.innerHTML = '<button class="template-chip active" type="button" data-category="all">Все</button>';
    categories.slice(0, 8).forEach((category) => {
        chipsContainer.insertAdjacentHTML('beforeend', `<button class="template-chip" type="button" data-category="${escapeAttribute(category)}">${escapeHTML(category)}</button>`);
    });

    chipsContainer.querySelectorAll('.template-chip').forEach((chip) => {
        chip.addEventListener('click', () => {
            state.category = chip.dataset.category;
            categorySelect.value = state.category;
            state.page = 1;
            render();
        });
    });
}

function render() {
    applyFilters();

    const start = (state.page - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);
    grid.innerHTML = pageItems.map(renderCard).join('');

    grid.querySelectorAll('[data-open-template]').forEach((button) => {
        button.addEventListener('click', () => openModal(Number(button.dataset.openTemplate)));
    });
    grid.querySelectorAll('[data-copy-template]').forEach((button) => {
        button.addEventListener('click', () => {
            const item = templates.find((template) => template.id === Number(button.dataset.copyTemplate));
            copyText(stripTalkmeMarkup(item?.text || ''));
        });
    });

    const maxPage = getMaxPage();
    countElement.textContent = filtered.length;
    totalElement.textContent = templates.length;
    pageElement.textContent = `Страница ${state.page} / ${maxPage}`;
    emptyElement.style.display = pageItems.length ? 'none' : 'block';
    prevButton.disabled = state.page <= 1;
    nextButton.disabled = state.page >= maxPage;
    syncActiveChip();
}

function renderCard(item) {
    const categories = (item.categories || [item.category]).filter(Boolean);
    return `
        <article class="template-link-card">
            <div class="template-link-top">
                <h3>${highlight(item.title)}</h3>
                <span>${escapeHTML(item.lang || 'RU')}</span>
            </div>
            <div class="template-card-meta">Оператор: ${escapeHTML(item.operator || 'Общий')} · ID ${escapeHTML(item.id)}</div>
            <div>${categories.map((category) => `<span class="template-category-tag">${escapeHTML(category)}</span>`).join('')}</div>
            <p class="template-card-preview">${highlight(stripTalkmeMarkup(item.text || ''))}</p>
            <div class="template-link-url">${item.hasAttachments ? `Вложения: ${item.attachments.length}` : 'Без вложений'}</div>
            <div class="template-link-actions">
                <button type="button" class="template-open-link" data-open-template="${escapeAttribute(item.id)}">Открыть</button>
                <button type="button" class="template-copy-link" data-copy-template="${escapeAttribute(item.id)}">Копировать</button>
            </div>
        </article>
    `;
}

function applyFilters() {
    const query = normalize(state.query);
    const words = query.split(/\s+/).filter(Boolean);
    filtered = templates.filter((item) => {
        const categories = item.categories || [item.category];
        const haystack = normalize([item.title, item.operator, item.category, item.text, categories.join(' ')].join(' '));
        const matchesQuery = !words.length || words.every((word) => haystack.includes(word));
        const matchesCategory = state.category === 'all' || categories.includes(state.category);
        const matchesLang = state.lang === 'all' || item.lang === state.lang;
        const matchesAttach = state.attach === 'all' || (state.attach === 'yes' ? item.hasAttachments : !item.hasAttachments);
        return matchesQuery && matchesCategory && matchesLang && matchesAttach;
    });

    const maxPage = getMaxPage();
    if (state.page > maxPage) {
        state.page = maxPage;
    }
}

function openModal(id) {
    const item = templates.find((template) => template.id === id);
    if (!item) {
        return;
    }

    activeTemplate = item;
    modalTitle.textContent = item.title;
    modalMeta.textContent = `Оператор: ${item.operator || 'Общий'} · ${item.lang || 'RU'} · ID ${item.id}`;
    modalCategories.innerHTML = (item.categories || [item.category]).filter(Boolean).map((category) => `<span class="template-category-tag">${escapeHTML(category)}</span>`).join('');
    modalText.textContent = stripTalkmeMarkup(item.text || '');
    modalAttachments.innerHTML = item.attachments?.length
        ? item.attachments.map((attachment) => attachment.url ? `<a href="${escapeAttribute(attachment.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(attachment.name)}</a>` : `<span>${escapeHTML(attachment.name)}</span>`).join('')
        : '<span class="muted">Вложений нет</span>';
    modalBackdrop.classList.add('active');
}

function closeModal() {
    modalBackdrop.classList.remove('active');
    activeTemplate = null;
}

function getMaxPage() {
    return Math.max(1, Math.ceil(filtered.length / perPage));
}

function syncActiveChip() {
    chipsContainer.querySelectorAll('.template-chip').forEach((chip) => {
        chip.classList.toggle('active', chip.dataset.category === state.category);
    });
}

function highlight(value) {
    const escaped = escapeHTML(value || '');
    const words = state.query.trim().split(/\s+/).filter((word) => word.length > 1).slice(0, 5);
    if (!words.length) {
        return escaped;
    }
    const pattern = words.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
    return escaped.replace(new RegExp(`(${pattern})`, 'ig'), '<mark>$1</mark>');
}

function stripTalkmeMarkup(value) {
    return String(value || '')
        .replace(/\[\{\/?b\}\]/g, '')
        .replace(/\[\{url=([^\]]+)\}\]([^\[]*)\[\{\/url\}\]/g, '$2 ($1)')
        .replace(/\[\{[^\]]+\}\]/g, '');
}

function normalize(value) {
    return String(value || '').toLowerCase().replaceAll('ё', 'е');
}

async function copyText(value) {
    if (navigator.clipboard) {
        await navigator.clipboard.writeText(value);
    } else {
        const textarea = document.createElement('textarea');
        textarea.value = value;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
    }
    showToast('Скопировано');
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
    }, 1700);
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
