let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let statusFiltro = '';
let modoFiltro = '';
let periodicidadeParaExcluir = null;
let isLoading = false;

const API_URLS = {
    listar: '/api/periodicidades/',
    criar: '/api/periodicidades/criar/',
    editar: (id) => `/api/periodicidades/${id}/editar/`,
    excluir: (id) => `/api/periodicidades/${id}/excluir/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarPeriodicidades();
    configurarEventListeners();
    configurarSwitchPorDemanda();
});

function configurarSwitchPorDemanda() {
    const porDemandaCheckbox = document.getElementById('porDemanda');
    const periodoFields = document.getElementById('periodoFields');
    const valorInput = document.getElementById('valor');
    const tipoSelect = document.getElementById('tipo');

    if (!porDemandaCheckbox || !periodoFields || !valorInput || !tipoSelect) return;

    const atualizarEstadoCampos = () => {
        if (porDemandaCheckbox.checked) {
            periodoFields.classList.add('hidden');
            valorInput.value = '';
            tipoSelect.value = '';
            valorInput.disabled = true;
            tipoSelect.disabled = true;
        } else {
            periodoFields.classList.remove('hidden');
            valorInput.disabled = false;
            tipoSelect.disabled = false;
        }
    };

    porDemandaCheckbox.addEventListener('change', atualizarEstadoCampos);
    atualizarEstadoCampos();
}

async function carregarPeriodicidades() {
    if (isLoading) return;

    isLoading = true;
    mostrarLoading(true);

    try {
        const params = new URLSearchParams({
            page: currentPage,
            rows: rowsPerPage,
            search: searchTerm,
            sort: sortDirection,
        });

        if (statusFiltro) params.set('status', statusFiltro);
        if (modoFiltro) params.set('modo', modoFiltro);

        const data = await fetchJson(`${API_URLS.listar}?${params.toString()}`);
        atualizarResumo(data);

        if (Array.isArray(data.data) && data.data.length > 0) {
            renderizarTabela(data.data);
        } else {
            mostrarSemDados();
        }

        renderizarPaginacao(data.total || 0);
    } catch (error) {
        mostrarErro(error.message || 'Não foi possível carregar as periodicidades.');
    } finally {
        isLoading = false;
        mostrarLoading(false);
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchPeriodicidade');
    const clearBtn = document.getElementById('clearSearch');
    const sortIcon = document.querySelector('.sort-icon');
    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const filtroStatus = document.getElementById('filtroStatus');
    const filtroModo = document.getElementById('filtroModo');
    const form = document.getElementById('periodicidadeForm');
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarPeriodicidades();
                if (clearBtn) clearBtn.style.display = searchTerm ? 'flex' : 'none';
            }, 280);
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            searchTerm = '';
            currentPage = 1;
            clearBtn.style.display = 'none';
            carregarPeriodicidades();
        });
    }

    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarPeriodicidades();
        });
    }

    if (filtroModo) {
        filtroModo.addEventListener('change', () => {
            modoFiltro = filtroModo.value;
            currentPage = 1;
            carregarPeriodicidades();
        });
    }

    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarPeriodicidades();
        });
    }

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10) || 10;
            currentPage = 1;
            carregarPeriodicidades();
        });
    }

    document.querySelectorAll('.close').forEach((btn) => {
        btn.addEventListener('click', () => {
            fecharModal();
            fecharModalExcluir();
        });
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target !== modal) return;
            fecharModal();
            fecharModalExcluir();
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        fecharModal();
        fecharModalExcluir();
    });

    if (form) {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            salvarPeriodicidade();
        });
    }
}

function renderizarTabela(periodicidadesList) {
    const tbody = document.getElementById('periodicidadesTableBody');
    const noResults = document.getElementById('noResults');

    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = periodicidadesList.map((period) => `
        <tr onclick="visualizarPeriodicidade(${period.id})">
            <td class="period-nome">
                <span class="period-avatar"><i class="fa-solid fa-calendar-days"></i></span>
                <div>
                    <strong>${escapeHtml(period.nome)}</strong>
                    <span>${period.por_demanda ? 'Execução sob demanda' : escapeHtml(period.tipo_display || period.tipo || 'Prazo definido')}</span>
                </div>
            </td>
            <td>
                <span class="badge ${period.por_demanda ? 'badge-info' : 'badge-success'}">
                    ${escapeHtml(period.descricao || '-')}
                </span>
            </td>
            <td>
                <span class="badge ${period.configuracoes > 0 ? 'badge-info' : 'badge-secondary'}">
                    ${period.configuracoes || 0}
                </span>
            </td>
            <td>
                <span class="badge ${period.status ? 'badge-success' : 'badge-danger'}">
                    ${period.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${formatarDataHora(period.criado_em)}</td>
            <td class="actions" onclick="event.stopPropagation()">
                <button type="button" class="btn-icon" onclick="visualizarPeriodicidade(${period.id})" title="Visualizar">
                    <i class="fa-solid fa-eye"></i>
                </button>
                ${canManage ? `
                <button type="button" class="btn-icon" onclick="editarPeriodicidade(${period.id})" title="Editar">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="btn-icon btn-icon-danger" onclick="abrirModalExcluir(${period.id})" title="Excluir">
                    <i class="fa-solid fa-trash"></i>
                </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

function atualizarResumo(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryAtivos', data.total_ativos || 0);
    setText('summaryDemanda', data.total_por_demanda || 0);
    setText('summaryConfiguracoes', data.total_configuracoes || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('periodicidadesTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhuma periodicidade encontrada</p>
            ${canManageSystem() ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="abrirModalCriar()">
                <i class="fa-solid fa-plus"></i> Criar periodicidade
            </button>
            ` : ''}
        `;
        noResults.style.display = 'block';
    }
}

function mostrarErro(mensagem) {
    const tbody = document.getElementById('periodicidadesTableBody');
    const noResults = document.getElementById('noResults');

    if (tbody) tbody.innerHTML = '';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button type="button" class="btn btn-primary btn-sm" onclick="carregarPeriodicidades()">
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
    carregarPeriodicidades();
}

function abrirModalCriar() {
    if (!canManageSystem()) return;

    setPeriodicidadeReadOnly(false);

    const modalTitle = document.getElementById('modalTitle');
    const form = document.getElementById('periodicidadeForm');
    const periodicidadeId = document.getElementById('periodicidadeId');
    const statusSelect = document.getElementById('status');
    const porDemandaCheckbox = document.getElementById('porDemanda');
    const feedback = document.getElementById('formFeedback');

    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Nova Periodicidade';
    if (form) form.reset();
    if (periodicidadeId) periodicidadeId.value = '';
    if (statusSelect) statusSelect.value = 'true';
    if (porDemandaCheckbox) porDemandaCheckbox.checked = false;
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    atualizarCamposPorDemanda();
    openModal('periodicidadeModal');
}

async function visualizarPeriodicidade(id) {
    try {
        const period = await buscarPeriodicidade(id);
        preencherPeriodicidadeForm(period);
        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-eye"></i> Periodicidade';
        atualizarCamposPorDemanda();
        setPeriodicidadeReadOnly(true, id);
        openModal('periodicidadeModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados da periodicidade.', true);
    }
}

async function editarPeriodicidade(id) {
    if (!canManageSystem()) return;

    try {
        const period = await buscarPeriodicidade(id);

        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-pen"></i> Editar Periodicidade';
        preencherPeriodicidadeForm(period);
        setPeriodicidadeReadOnly(false, id);

        atualizarCamposPorDemanda();
        openModal('periodicidadeModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados da periodicidade.', true);
    }
}

async function salvarPeriodicidade() {
    if (!canManageSystem()) return;

    const id = document.getElementById('periodicidadeId')?.value;
    const nome = document.getElementById('nome')?.value.trim();
    const porDemanda = document.getElementById('porDemanda')?.checked || false;
    const valor = document.getElementById('valor')?.value;
    const tipo = document.getElementById('tipo')?.value;
    const status = document.getElementById('status')?.value === 'true';

    if (!nome) {
        mostrarFormFeedback('O nome da periodicidade é obrigatório.');
        document.getElementById('nome')?.focus();
        return;
    }

    if (!porDemanda) {
        if (!valor || Number(valor) <= 0) {
            mostrarFormFeedback('O valor é obrigatório e deve ser maior que zero.');
            document.getElementById('valor')?.focus();
            return;
        }

        if (!tipo) {
            mostrarFormFeedback('Selecione o tipo da recorrência.');
            document.getElementById('tipo')?.focus();
            return;
        }
    }

    const submitBtn = document.querySelector('#periodicidadeForm button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const data = await fetchJson(id ? API_URLS.editar(id) : API_URLS.criar, {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                nome,
                por_demanda: porDemanda,
                valor: porDemanda ? null : parseInt(valor, 10),
                tipo: porDemanda ? null : tipo,
                status,
            }),
        });

        mostrarToast(data.message || (id ? 'Periodicidade atualizada com sucesso!' : 'Periodicidade criada com sucesso!'));
        fecharModal();
        carregarPeriodicidades();
    } catch (error) {
        mostrarFormFeedback(error.message || 'Erro ao salvar periodicidade.');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function abrirModalExcluir(id) {
    if (!canManageSystem()) return;

    periodicidadeParaExcluir = id;

    try {
        const period = await buscarPeriodicidade(id);
        setText('excluirNome', period.nome);
        openModal('excluirModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados da periodicidade.', true);
    }
}

async function confirmarExcluir() {
    if (!canManageSystem()) return;

    if (!periodicidadeParaExcluir) return;

    const confirmBtn = document.querySelector('#excluirModal .btn-danger');
    if (confirmBtn) confirmBtn.disabled = true;

    try {
        const data = await fetchJson(API_URLS.excluir(periodicidadeParaExcluir), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });

        mostrarToast(data.message || 'Periodicidade excluída com sucesso!');
        fecharModalExcluir();
        carregarPeriodicidades();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao excluir periodicidade.', true);
    } finally {
        if (confirmBtn) confirmBtn.disabled = false;
    }
}

function fecharModal() {
    closeModal('periodicidadeModal');
    setPeriodicidadeReadOnly(false);
}

function fecharModalExcluir() {
    closeModal('excluirModal');
    periodicidadeParaExcluir = null;
}

function mostrarLoading(show) {
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('periodicidadesTableBody');
    const noResults = document.getElementById('noResults');

    if (show) {
        if (loading) loading.style.display = 'block';
        if (tableBody) tableBody.style.display = 'none';
        if (noResults) noResults.style.display = 'none';
    } else {
        if (loading) loading.style.display = 'none';
        if (tableBody) tableBody.style.display = '';
    }
}

function atualizarCamposPorDemanda() {
    const porDemandaCheckbox = document.getElementById('porDemanda');
    porDemandaCheckbox?.dispatchEvent(new Event('change'));
}

async function buscarPeriodicidade(id) {
    const data = await fetchJson(`${API_URLS.listar}?id=${id}`);
    const period = (data.data || []).find((item) => item.id === id);
    if (!period) throw new Error('Periodicidade não encontrada.');
    return period;
}

function preencherPeriodicidadeForm(period) {
    setValue('periodicidadeId', period.id);
    setValue('nome', period.nome || '');
    setChecked('porDemanda', !!period.por_demanda);
    setValue('valor', period.valor || '');
    setValue('tipo', period.tipo || '');
    setValue('status', period.status ? 'true' : 'false');

    const feedback = document.getElementById('formFeedback');
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }
}

function setPeriodicidadeReadOnly(readOnly, id = null) {
    const form = document.getElementById('periodicidadeForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = document.querySelector('#periodicidadeModal .modal-footer .btn-outline');
    if (cancelBtn) cancelBtn.textContent = readOnly ? 'Fechar' : 'Cancelar';

    let editBtn = document.getElementById('periodicidadeEditBtn');
    const footer = document.querySelector('#periodicidadeModal .modal-footer');
    if (!editBtn && footer) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'periodicidadeEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        footer.insertBefore(editBtn, submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        editBtn.onclick = () => {
            if (id) editarPeriodicidade(id);
        };
    }
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: { 'X-Requested-With': 'XMLHttpRequest', ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok || data.success === false) {
        throw new Error(data.error || 'Não foi possível concluir a ação.');
    }

    return data;
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    document.body.classList.add('modal-open');
    modal.classList.add('open');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('open');

    if (!document.querySelector('.modal.open')) {
        document.body.classList.remove('modal-open');
    }
}

function mostrarFormFeedback(message) {
    const feedback = document.getElementById('formFeedback');
    if (!feedback) {
        mostrarToast(message, true);
        return;
    }

    feedback.textContent = message;
    feedback.classList.add('show');
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
        const [dataParte, horaParte = ''] = dataHora.split(' ');
        const data = dataParte.split('-');
        return `${data[2]}/${data[1]}/${data[0]} ${horaParte}`.trim();
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

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.value = value ?? '';
}

function setChecked(id, value) {
    const element = document.getElementById(id);
    if (element) element.checked = Boolean(value);
}

function getCookie(name) {
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i += 1) {
            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === `${name}=`) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }

    return cookieValue;
}
