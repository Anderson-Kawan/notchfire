const DRAFT_CACHE_PREFIX = 'notchfire:checklist-draft:';
let serverDraftIds = new Set();

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarRascunhos();
});

async function carregarRascunhos() {
    await carregarRascunhosServidor();
    renderizarRascunhosLocais();
}

async function carregarRascunhosServidor() {
    const container = document.getElementById('serverDrafts');
    if (!container) return;

    container.innerHTML = '<div class="loading-card"><i class="fa-solid fa-spinner fa-spin"></i> Carregando rascunhos...</div>';

    try {
        const response = await fetch('/api/rascunhos/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const payload = await response.json();

        if (!response.ok || !payload.success) {
            throw new Error(payload.error || 'Não foi possível carregar os rascunhos.');
        }

        const drafts = payload.data || [];
        serverDraftIds = new Set(drafts.map((draft) => Number(draft.id)));
        setText('summaryServidor', drafts.length);
        renderizarDraftsServidor(drafts);
        atualizarTotalResumo();
    } catch (error) {
        serverDraftIds = new Set();
        container.innerHTML = `
            <div class="empty-card">
                <i class="fa-solid fa-triangle-exclamation"></i>
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}

function renderizarDraftsServidor(drafts) {
    const container = document.getElementById('serverDrafts');
    if (!container) return;

    if (!drafts.length) {
        container.innerHTML = `
            <div class="empty-card">
                <i class="fa-solid fa-file-circle-check"></i>
                Nenhum rascunho salvo no sistema.
            </div>
        `;
        return;
    }

    container.innerHTML = drafts.map((draft) => renderDraftCard({
        source: 'server',
        id: draft.id,
        equipamento: draft.equipamento_nome,
        serie: draft.equipamento_numero_serie,
        tipo: draft.tipo_servico_nome,
        local: draft.local,
        atualizado: draft.atualizado_em,
        progresso: draft.progresso || 0,
        respostas: draft.total_respostas || 0,
        total: draft.total_itens || 0,
        continueUrl: `/servicos/?rascunho_id=${draft.id}`,
    })).join('');
}

function renderizarRascunhosLocais() {
    const container = document.getElementById('localDrafts');
    if (!container) return;

    const drafts = lerRascunhosLocais().filter((draft) => {
        return !draft.rascunho_id || !serverDraftIds.has(Number(draft.rascunho_id));
    });
    setText('summaryLocal', drafts.length);
    atualizarTotalResumo();

    if (!drafts.length) {
        container.innerHTML = `
            <div class="empty-card">
                <i class="fa-solid fa-laptop-file"></i>
                Nenhum rascunho local neste navegador.
            </div>
        `;
        return;
    }

    container.innerHTML = drafts.map((draft) => {
        const respostas = draft.respostas || [];
        return renderDraftCard({
            source: 'local',
            id: draft.key,
            equipamento: draft.equipamento_nome,
            serie: '',
            tipo: draft.tipo_servico_nome,
            local: '',
            atualizado: formatarDataLocal(draft.atualizado_em),
            progresso: calcularProgresso(respostas.length, draft.total_itens),
            respostas: respostas.length,
            total: draft.total_itens || respostas.length,
            continueUrl: `/servicos/?equipamento_id=${draft.equipamento_id}&tipo_servico_id=${draft.tipo_servico_id}&restore_local=${encodeURIComponent(draft.key)}`,
        });
    }).join('');
}

function renderDraftCard(draft) {
    const progress = Math.max(0, Math.min(Number(draft.progresso || 0), 100));
    const isLocal = draft.source === 'local';

    return `
        <article class="draft-card">
            <div class="draft-top">
                <span class="draft-icon">
                    <i class="fa-solid ${isLocal ? 'fa-laptop' : 'fa-cloud'}"></i>
                </span>
                <div class="draft-info">
                    <h3>${escapeHtml(draft.equipamento || 'Equipamento')}</h3>
                    <p>${escapeHtml(draft.tipo || 'Checklist')}</p>
                </div>
            </div>
            <div class="draft-meta">
                ${draft.serie ? `<span><i class="fa-solid fa-barcode"></i> Série: ${escapeHtml(draft.serie)}</span>` : ''}
                ${draft.local ? `<span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(draft.local)}</span>` : ''}
                <span><i class="fa-solid fa-clock"></i> Atualizado: ${escapeHtml(draft.atualizado || '-')}</span>
                <span><i class="fa-solid fa-list-check"></i> ${draft.respostas || 0}/${draft.total || 0} respostas</span>
            </div>
            <div class="progress-row">
                <div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div>
                <strong>${progress}%</strong>
            </div>
            <div class="draft-actions">
                ${canManageSystem() ? `
                <a href="${draft.continueUrl}" class="btn btn-primary btn-sm">
                    <i class="fa-solid fa-play"></i> Continuar
                </a>
                <button type="button" class="btn btn-outline btn-sm" onclick="${isLocal ? `descartarLocal('${escapeAttribute(draft.id)}')` : `descartarServidor(${draft.id})`}">
                    <i class="fa-solid fa-trash"></i> Descartar
                </button>
                ` : ''}
            </div>
        </article>
    `;
}

function lerRascunhosLocais() {
    const drafts = [];

    for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index);
        if (!key || !key.startsWith(DRAFT_CACHE_PREFIX)) continue;

        try {
            const draft = JSON.parse(localStorage.getItem(key));
            if (draft) drafts.push({ ...draft, key });
        } catch {
            localStorage.removeItem(key);
        }
    }

    return drafts.sort((a, b) => String(b.atualizado_em || '').localeCompare(String(a.atualizado_em || '')));
}

async function descartarServidor(id) {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar rascunhos, mas não descartar registros.', true);
        return;
    }

    if (!window.confirm('Descartar este rascunho salvo no sistema?')) return;

    try {
        const response = await fetch(`/api/servicos/${id}/descartar/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) throw new Error(payload.error || 'Não foi possível descartar.');
        mostrarToast('Rascunho descartado.');
        carregarRascunhos();
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

function descartarLocal(key) {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar rascunhos, mas não descartar registros.', true);
        return;
    }

    if (!window.confirm('Descartar este rascunho local?')) return;
    localStorage.removeItem(key);
    renderizarRascunhosLocais();
    mostrarToast('Rascunho local descartado.');
}

function limparRascunhosLocais() {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar rascunhos, mas não limpar registros.', true);
        return;
    }

    const drafts = lerRascunhosLocais();
    if (!drafts.length) {
        mostrarToast('Nenhum rascunho local para limpar.');
        return;
    }

    if (!window.confirm('Limpar todos os rascunhos locais deste navegador?')) return;

    drafts.forEach((draft) => localStorage.removeItem(draft.key));
    renderizarRascunhosLocais();
    mostrarToast('Rascunhos locais limpos.');
}

function calcularProgresso(respostas, total) {
    const totalItens = Number(total || 0);
    if (!totalItens) return respostas ? 100 : 0;
    return Math.round((Number(respostas || 0) / totalItens) * 100);
}

function atualizarTotalResumo() {
    const servidor = Number(document.getElementById('summaryServidor')?.textContent || 0);
    const local = Number(document.getElementById('summaryLocal')?.textContent || 0);
    setText('summaryTotal', servidor + local);
}

function formatarDataLocal(value) {
    if (!value) return '-';
    const data = new Date(value);
    if (Number.isNaN(data.getTime())) return '-';
    return data.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

function mostrarToast(message, isError = false) {
    const oldToast = document.querySelector('.toast-notification');
    if (oldToast) oldToast.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification${isError ? ' toast-error' : ''}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 220);
    }, 3200);
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function escapeAttribute(text) {
    return escapeHtml(text).replace(/'/g, '&#39;').replace(/"/g, '&quot;');
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}
