// tipos_equipamento.js - NotchFire

let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let grupoFiltro = '';
let statusFiltro = '';
let tipoParaExcluir = null;
let tiposAtuais = [];

const API_URLS = {
    listar: '/api/tipos-equipamento/',
    listarGrupos: '/api/grupos-para-select/',
    listarPeriodicidades: '/api/periodicidades-para-select/',
    criar: '/api/tipos-equipamento/criar/',
    editar: (id) => `/api/tipos-equipamento/${id}/editar/`,
    excluir: (id) => `/api/tipos-equipamento/${id}/excluir/`,
    detalhe: (id) => `/tipos-equipamento/${id}/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarGruposParaSelect();
    carregarPeriodicidadesParaSelect();
    carregarTiposEquipamento();
    configurarEventListeners();
});

async function carregarPeriodicidadesParaSelect() {
    try {
        const data = await fetchJson(API_URLS.listarPeriodicidades);
        const select = document.getElementById('periodicidade');
        if (!select || !data.success) return;

        select.innerHTML = '<option value="">Selecione uma periodicidade...</option>';
        data.data.forEach((periodicidade) => {
            const descricao = periodicidade.descricao ? ` - ${periodicidade.descricao}` : '';
            select.insertAdjacentHTML('beforeend', `
                <option value="${periodicidade.id}">
                    ${escapeHtml(periodicidade.nome)}${escapeHtml(descricao)}
                </option>
            `);
        });
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível carregar periodicidades.', true);
    }
}

async function carregarGruposParaSelect() {
    try {
        const data = await fetchJson(API_URLS.listarGrupos);
        if (!data.success) return;

        preencherSelect('grupo', data.data, 'Selecione um grupo...');
        preencherSelect('filtroGrupo', data.data, 'Todos os Grupos');
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível carregar grupos.', true);
    }
}

async function carregarTiposEquipamento() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'block';

    try {
        const params = new URLSearchParams({
            page: currentPage,
            rows: rowsPerPage,
            search: searchTerm,
            sort: sortDirection
        });

        if (grupoFiltro) params.set('grupo_id', grupoFiltro);
        if (statusFiltro) params.set('status', statusFiltro);

        const data = await fetchJson(`${API_URLS.listar}?${params.toString()}`);

        if (data.success) {
            tiposAtuais = data.data || [];
            atualizarResumo(data);

            if (tiposAtuais.length > 0) {
                renderizarTabela(tiposAtuais);
            } else {
                mostrarSemDados();
            }

            renderizarPaginacao(data.total || 0);
        } else {
            mostrarErro(data.error || 'Erro ao carregar tipos de equipamento.');
        }
    } catch (error) {
        mostrarErro(error.message || 'Não foi possível carregar os tipos de equipamento.');
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchTipoEquipamento');
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarTiposEquipamento();

                const clearBtn = document.getElementById('clearSearch');
                if (clearBtn) clearBtn.style.display = searchTerm ? 'flex' : 'none';
            }, 350);
        });
    }

    const clearBtn = document.getElementById('clearSearch');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            searchTerm = '';
            currentPage = 1;
            clearBtn.style.display = 'none';
            carregarTiposEquipamento();
        });
    }

    const filtroGrupoEl = document.getElementById('filtroGrupo');
    if (filtroGrupoEl) {
        filtroGrupoEl.addEventListener('change', () => {
            grupoFiltro = filtroGrupoEl.value;
            currentPage = 1;
            carregarTiposEquipamento();
        });
    }

    const filtroStatusEl = document.getElementById('filtroStatus');
    if (filtroStatusEl) {
        filtroStatusEl.addEventListener('change', () => {
            statusFiltro = filtroStatusEl.value;
            currentPage = 1;
            carregarTiposEquipamento();
        });
    }

    const sortIcon = document.querySelector('.sort-icon');
    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarTiposEquipamento();
        });
    }

    const rowsSelect = document.getElementById('rowsPerPage');
    if (rowsSelect) {
        rowsSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsSelect.value, 10);
            currentPage = 1;
            carregarTiposEquipamento();
        });
    }

    document.querySelectorAll('.close').forEach((button) => {
        button.addEventListener('click', () => {
            fecharModal();
            fecharModalExcluir();
        });
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                fecharModal();
                fecharModalExcluir();
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            fecharModal();
            fecharModalExcluir();
        }
    });

    const form = document.getElementById('tipoEquipamentoForm');
    if (form) {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            salvarTipoEquipamento();
        });
    }
}

function renderizarTabela(tiposList) {
    const tbody = document.getElementById('tiposEquipamentoTableBody');
    const noResults = document.getElementById('noResults');
    if (!tbody) return;

    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = tiposList.map((tipo) => `
        <tr class="table-row-clickable" onclick="visualizarTipoEquipamento(${tipo.id})">
            <td class="actions" onclick="event.stopPropagation()">
                <button type="button" class="btn-icon" onclick="visualizarTipoEquipamento(${tipo.id})" title="Visualizar">
                    <i class="fa-solid fa-eye"></i>
                </button>
                ${canManage ? `
                <button type="button" class="btn-icon btn-checklist" onclick="abrirDetalheTipoEquipamento(${tipo.id})" title="Checklists">
                    <i class="fa-solid fa-list-check"></i>
                </button>
                <button type="button" class="btn-icon" onclick="editarTipoEquipamento(${tipo.id})" title="Editar">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="btn-icon" onclick="abrirModalExcluir(${tipo.id})" title="Excluir">
                    <i class="fa-solid fa-trash"></i>
                </button>
                ` : ''}
            </td>
            <td class="tipo-nome">
                <button type="button" class="tipo-link-btn" onclick="event.stopPropagation(); visualizarTipoEquipamento(${tipo.id})">
                    <strong>${escapeHtml(tipo.nome)}</strong>
                </button>
            </td>
            <td><span class="badge badge-info">${escapeHtml(tipo.grupo_nome || '-')}</span></td>
            <td>${tipo.periodicidade_nome ? `<span class="badge badge-info">${escapeHtml(tipo.periodicidade_nome)}</span>` : '-'}</td>
            <td><span class="tipo-description">${escapeHtml(tipo.descricao || '-')}</span></td>
            <td>
                <span class="badge ${tipo.status ? 'badge-success' : 'badge-danger'}">
                    ${tipo.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${formatarDataHora(tipo.criado_em)}</td>
        </tr>
    `).join('');
}

function atualizarResumo(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryAtivos', data.total_ativos || 0);
    setText('summaryInativos', data.total_inativos || 0);
    setText('summaryGrupos', data.total_grupos || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('tiposEquipamentoTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum tipo de equipamento encontrado</p>
            ${canManageSystem() ? `
            <button class="btn btn-primary btn-sm" onclick="abrirModalCriar()">
                <i class="fa-solid fa-plus"></i> Criar tipo de equipamento
            </button>
            ` : ''}
        `;
        noResults.style.display = 'block';
    }
}

function mostrarErro(mensagem) {
    const tbody = document.getElementById('tiposEquipamentoTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button class="btn btn-primary btn-sm" onclick="carregarTiposEquipamento()">
                Tentar novamente
            </button>
        `;
        noResults.style.display = 'block';
    }
}

function renderizarPaginacao(total) {
    const totalPages = Math.ceil(total / rowsPerPage);
    const paginationDiv = document.getElementById('paginationControls');
    if (!paginationDiv) return;

    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }

    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    let html = `
        <button class="page-btn" onclick="mudarPagina(1)" ${currentPage === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-left"></i>
        </button>
        <button class="page-btn" onclick="mudarPagina(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-left"></i>
        </button>
    `;

    if (startPage > 1) html += '<span class="page-info">...</span>';

    for (let page = startPage; page <= endPage; page += 1) {
        html += `
            <button class="page-btn ${page === currentPage ? 'page-active' : ''}" onclick="mudarPagina(${page})">
                ${page}
            </button>
        `;
    }

    if (endPage < totalPages) html += '<span class="page-info">...</span>';

    html += `
        <button class="page-btn" onclick="mudarPagina(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-right"></i>
        </button>
        <button class="page-btn" onclick="mudarPagina(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-right"></i>
        </button>
    `;

    paginationDiv.innerHTML = html;
}

function mudarPagina(page) {
    currentPage = page;
    carregarTiposEquipamento();
}

function abrirModalCriar() {
    if (!canManageSystem()) return;

    setTipoEquipamentoReadOnly(false);

    setText('modalTitle', '');
    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Novo Tipo de Equipamento';

    const form = document.getElementById('tipoEquipamentoForm');
    if (form) form.reset();

    setValue('tipoEquipamentoId', '');
    setValue('status', 'true');
    setValue('grupo', '');
    setValue('periodicidade', '');

    abrirModal('tipoEquipamentoModal');
}

function visualizarTipoEquipamento(id) {
    const tipo = tiposAtuais.find((item) => item.id === id);
    if (!tipo) {
        mostrarToast('Não foi possível carregar os dados deste tipo.', true);
        return;
    }

    preencherTipoEquipamentoForm(tipo);

    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-eye"></i> Tipo de Equipamento';

    setTipoEquipamentoReadOnly(true, id);
    abrirModal('tipoEquipamentoModal');
}

function editarTipoEquipamento(id) {
    if (!canManageSystem()) return;

    const tipo = tiposAtuais.find((item) => item.id === id);
    if (!tipo) {
        mostrarToast('Não foi possível carregar os dados deste tipo.', true);
        return;
    }

    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-pen"></i> Editar Tipo de Equipamento';

    preencherTipoEquipamentoForm(tipo);
    setTipoEquipamentoReadOnly(false, id);

    abrirModal('tipoEquipamentoModal');
}

function preencherTipoEquipamentoForm(tipo) {
    setValue('tipoEquipamentoId', tipo.id);
    setValue('nome', tipo.nome || '');
    setValue('grupo', tipo.grupo_id || '');
    setValue('periodicidade', tipo.periodicidade_id || '');
    setValue('descricao', tipo.descricao || '');
    setValue('status', tipo.status ? 'true' : 'false');
}

async function salvarTipoEquipamento() {
    if (!canManageSystem()) return;

    const id = getValue('tipoEquipamentoId');
    const nome = getValue('nome').trim();
    const grupoId = getValue('grupo');
    const periodicidadeId = getValue('periodicidade');
    const descricao = getValue('descricao');
    const status = getValue('status') === 'true';

    if (!nome) {
        mostrarToast('O nome do tipo de equipamento é obrigatório.', true);
        document.getElementById('nome')?.focus();
        return;
    }

    if (!grupoId) {
        mostrarToast('Selecione um grupo.', true);
        document.getElementById('grupo')?.focus();
        return;
    }

    if (!periodicidadeId) {
        mostrarToast('Selecione uma periodicidade.', true);
        document.getElementById('periodicidade')?.focus();
        return;
    }

    const submitBtn = document.querySelector('#tipoEquipamentoForm button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : '';
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Salvando...';
        submitBtn.disabled = true;
    }

    try {
        const data = await fetchJson(id ? API_URLS.editar(id) : API_URLS.criar, {
            method: id ? 'PUT' : 'POST',
            body: {
                nome,
                grupo_id: parseInt(grupoId, 10),
                periodicidade_id: parseInt(periodicidadeId, 10),
                descricao,
                status
            }
        });

        mostrarToast(data.message || (id ? 'Tipo atualizado com sucesso.' : 'Tipo criado com sucesso.'));

        if (!id && data.data?.id) {
            window.location.href = API_URLS.detalhe(data.data.id);
            return;
        }

        fecharModal();
        await carregarTiposEquipamento();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao salvar tipo de equipamento.', true);
    } finally {
        if (submitBtn) {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    }
}

function abrirModalExcluir(id) {
    if (!canManageSystem()) return;

    tipoParaExcluir = id;
    const tipo = tiposAtuais.find((item) => item.id === id);
    setText('excluirNome', tipo ? tipo.nome : 'selecionado');
    abrirModal('excluirModal');
}

async function confirmarExcluir() {
    if (!canManageSystem()) return;

    if (!tipoParaExcluir) return;

    const confirmBtn = document.querySelector('#excluirModal .btn-danger');
    const originalText = confirmBtn ? confirmBtn.innerHTML : '';
    if (confirmBtn) {
        confirmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Excluindo...';
        confirmBtn.disabled = true;
    }

    try {
        const data = await fetchJson(API_URLS.excluir(tipoParaExcluir), { method: 'DELETE' });
        mostrarToast(data.message || 'Tipo excluído com sucesso.');
        fecharModalExcluir();
        await carregarTiposEquipamento();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao excluir tipo de equipamento.', true);
    } finally {
        if (confirmBtn) {
            confirmBtn.innerHTML = originalText;
            confirmBtn.disabled = false;
        }
    }
}

function abrirDetalheTipoEquipamento(id) {
    window.location.href = API_URLS.detalhe(id);
}

function setTipoEquipamentoReadOnly(readOnly, id = null) {
    const form = document.getElementById('tipoEquipamentoForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = form.querySelector('.form-actions .btn-secondary');
    if (cancelBtn) {
        cancelBtn.innerHTML = readOnly
            ? '<i class="fa-solid fa-times"></i> Fechar'
            : '<i class="fa-solid fa-times"></i> Cancelar';
    }

    const actions = form.querySelector('.form-actions');
    let editBtn = document.getElementById('tipoEquipamentoEditBtn');
    if (!editBtn && actions) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'tipoEquipamentoEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        actions.insertBefore(editBtn, submitBtn || null);
    }

    let checklistBtn = document.getElementById('tipoEquipamentoChecklistBtn');
    if (!checklistBtn && actions) {
        checklistBtn = document.createElement('button');
        checklistBtn.type = 'button';
        checklistBtn.id = 'tipoEquipamentoChecklistBtn';
        checklistBtn.className = 'btn btn-secondary';
        checklistBtn.innerHTML = '<i class="fa-solid fa-list-check"></i> Checklists';
        actions.insertBefore(checklistBtn, editBtn || submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        editBtn.onclick = () => {
            if (id) editarTipoEquipamento(id);
        };
    }

    if (checklistBtn) {
        checklistBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        checklistBtn.onclick = () => {
            if (id) abrirDetalheTipoEquipamento(id);
        };
    }
}

function abrirModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function fecharModal() {
    const modal = document.getElementById('tipoEquipamentoModal');
    if (modal) modal.classList.remove('open');
    setTipoEquipamentoReadOnly(false);
    restaurarScrollSeSemModal();
}

function fecharModalExcluir() {
    const modal = document.getElementById('excluirModal');
    if (modal) modal.classList.remove('open');
    tipoParaExcluir = null;
    restaurarScrollSeSemModal();
}

function restaurarScrollSeSemModal() {
    if (!document.querySelector('.modal.open')) {
        document.body.style.overflow = '';
    }
}

async function fetchJson(url, options = {}) {
    const fetchOptions = {
        method: options.method || 'GET',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
            ...(options.headers || {})
        }
    };

    if (options.body !== undefined) {
        fetchOptions.headers['Content-Type'] = 'application/json';
        fetchOptions.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, fetchOptions);
    const data = await response.json().catch(() => ({}));

    if (!response.ok || data.success === false) {
        throw new Error(data.error || 'Não foi possível concluir a ação.');
    }

    return data;
}

function preencherSelect(id, itens, placeholder) {
    const select = document.getElementById(id);
    if (!select) return;

    select.innerHTML = `<option value="">${placeholder}</option>`;
    itens.forEach((item) => {
        select.insertAdjacentHTML('beforeend', `<option value="${item.id}">${escapeHtml(item.nome)}</option>`);
    });
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

function formatarDataHora(dataHora) {
    if (!dataHora) return '-';

    try {
        const [data, hora = ''] = dataHora.split(' ');
        const [ano, mes, dia] = data.split('-');
        return `${dia}/${mes}/${ano}${hora ? ` ${hora}` : ''}`;
    } catch (error) {
        return dataHora;
    }
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

function getValue(id) {
    const element = document.getElementById(id);
    return element ? element.value : '';
}

function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.value = value;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}
