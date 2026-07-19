let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let statusFiltro = '';
let tipoParaExcluir = null;
let isLoading = false;

const API_URLS = {
    listar: '/api/tipos-servico/',
    criar: '/api/tipos-servico/criar/',
    editar: (id) => `/api/tipos-servico/${id}/editar/`,
    excluir: (id) => `/api/tipos-servico/${id}/excluir/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarTipos();
    configurarEventListeners();
});

async function carregarTipos() {
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

        const data = await fetchJson(`${API_URLS.listar}?${params.toString()}`);
        atualizarResumo(data);

        if (data.data && data.data.length > 0) {
            renderizarTabela(data.data);
        } else {
            mostrarSemDados();
        }

        renderizarPaginacao(data.total || 0);
    } catch (error) {
        mostrarErro(error.message || 'Não foi possível carregar os tipos de serviço.');
    } finally {
        isLoading = false;
        mostrarLoading(false);
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchTipoServico');
    const clearBtn = document.getElementById('clearSearch');
    const filtroStatus = document.getElementById('filtroStatus');
    const sortIcon = document.querySelector('.sort-icon');
    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const form = document.getElementById('tipoServicoForm');
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarTipos();
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
            carregarTipos();
        });
    }

    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarTipos();
        });
    }

    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarTipos();
        });
    }

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10);
            currentPage = 1;
            carregarTipos();
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
            salvarTipo();
        });
    }
}

function renderizarTabela(tiposList) {
    const tbody = document.getElementById('tiposServicoTableBody');
    const noResults = document.getElementById('noResults');

    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = tiposList.map((tipo) => `
        <tr onclick="visualizarTipo(${tipo.id})">
            <td class="tipo-nome">
                <span class="service-avatar"><i class="fa-solid fa-screwdriver-wrench"></i></span>
                <div>
                    <strong>${escapeHtml(tipo.nome)}</strong>
                    <span>${tipo.servicos || 0} serviço${tipo.servicos === 1 ? '' : 's'} realizado${tipo.servicos === 1 ? '' : 's'}</span>
                </div>
            </td>
            <td>${escapeHtml(tipo.descricao) || '-'}</td>
            <td>
                <span class="badge ${tipo.configuracoes > 0 ? 'badge-info' : 'badge-secondary'}">
                    ${tipo.configuracoes || 0}
                </span>
            </td>
            <td>
                <span class="badge ${tipo.status ? 'badge-success' : 'badge-danger'}">
                    ${tipo.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${formatarDataHora(tipo.criado_em)}</td>
            <td class="actions" onclick="event.stopPropagation()">
                <button type="button" class="btn-icon" onclick="visualizarTipo(${tipo.id})" title="Visualizar">
                    <i class="fa-solid fa-eye"></i>
                </button>
                ${canManage ? `
                <button type="button" class="btn-icon" onclick="editarTipo(${tipo.id})" title="Editar">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="btn-icon btn-icon-danger" onclick="abrirModalExcluir(${tipo.id})" title="Excluir">
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
    setText('summaryInativos', data.total_inativos || 0);
    setText('summaryConfiguracoes', data.total_configuracoes || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('tiposServicoTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum tipo de serviço encontrado</p>
            ${canManageSystem() ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="abrirModalCriar()">
                <i class="fa-solid fa-plus"></i> Criar tipo de serviço
            </button>
            ` : ''}
        `;
        noResults.style.display = 'block';
    }
}

function mostrarErro(mensagem) {
    const tbody = document.getElementById('tiposServicoTableBody');
    const noResults = document.getElementById('noResults');

    if (tbody) tbody.innerHTML = '';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button type="button" class="btn btn-primary btn-sm" onclick="carregarTipos()">
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
    carregarTipos();
}

function abrirModalCriar() {
    if (!canManageSystem()) return;

    setTipoReadOnly(false);

    const modalTitle = document.getElementById('modalTitle');
    const form = document.getElementById('tipoServicoForm');
    const tipoId = document.getElementById('tipoServicoId');
    const statusSelect = document.getElementById('status');
    const feedback = document.getElementById('formFeedback');

    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Novo Tipo de Serviço';
    if (form) form.reset();
    if (tipoId) tipoId.value = '';
    if (statusSelect) statusSelect.value = 'true';
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    openModal('tipoServicoModal');
}

async function visualizarTipo(id) {
    try {
        const tipo = await buscarTipo(id);
        preencherTipoForm(tipo);
        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-eye"></i> Tipo de Serviço';
        setTipoReadOnly(true, id);
        openModal('tipoServicoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do tipo de serviço.', true);
    }
}

async function editarTipo(id) {
    if (!canManageSystem()) return;

    try {
        const tipo = await buscarTipo(id);

        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-pen"></i> Editar Tipo de Serviço';
        preencherTipoForm(tipo);
        setTipoReadOnly(false, id);

        openModal('tipoServicoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do tipo de serviço.', true);
    }
}

async function salvarTipo() {
    if (!canManageSystem()) return;

    const id = document.getElementById('tipoServicoId').value;
    const nome = document.getElementById('nome').value.trim();
    const descricao = document.getElementById('descricao').value.trim();
    const status = document.getElementById('status').value === 'true';

    if (!nome) {
        mostrarFormFeedback('O nome do tipo de serviço é obrigatório.');
        document.getElementById('nome').focus();
        return;
    }

    const submitBtn = document.querySelector('#tipoServicoForm button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const data = await fetchJson(id ? API_URLS.editar(id) : API_URLS.criar, {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                nome: nome.toUpperCase(),
                descricao,
                status,
            }),
        });

        mostrarToast(data.message || (id ? 'Tipo de serviço atualizado com sucesso!' : 'Tipo de serviço criado com sucesso!'));
        fecharModal();
        carregarTipos();
    } catch (error) {
        mostrarFormFeedback(error.message || 'Erro ao salvar tipo de serviço.');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function abrirModalExcluir(id) {
    if (!canManageSystem()) return;

    tipoParaExcluir = id;

    try {
        const tipo = await buscarTipo(id);
        setText('excluirNome', tipo.nome);
        openModal('excluirModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do tipo de serviço.', true);
    }
}

async function confirmarExcluir() {
    if (!canManageSystem()) return;

    if (!tipoParaExcluir) return;

    const confirmBtn = document.querySelector('#excluirModal .btn-danger');
    if (confirmBtn) confirmBtn.disabled = true;

    try {
        const data = await fetchJson(API_URLS.excluir(tipoParaExcluir), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });

        mostrarToast(data.message || 'Tipo de serviço excluído com sucesso!');
        fecharModalExcluir();
        carregarTipos();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao excluir tipo de serviço.', true);
    } finally {
        if (confirmBtn) confirmBtn.disabled = false;
    }
}

function fecharModal() {
    closeModal('tipoServicoModal');
    setTipoReadOnly(false);
}

function fecharModalExcluir() {
    closeModal('excluirModal');
    tipoParaExcluir = null;
}

function mostrarLoading(show) {
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('tiposServicoTableBody');
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

async function buscarTipo(id) {
    const data = await fetchJson(`${API_URLS.listar}?id=${id}`);
    const tipo = (data.data || []).find((item) => item.id === id);
    if (!tipo) throw new Error('Tipo de serviço não encontrado.');
    return tipo;
}

function preencherTipoForm(tipo) {
    setValue('tipoServicoId', tipo.id);
    setValue('nome', tipo.nome || '');
    setValue('descricao', tipo.descricao || '');
    setValue('status', tipo.status ? 'true' : 'false');

    const feedback = document.getElementById('formFeedback');
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }
}

function setTipoReadOnly(readOnly, id = null) {
    const form = document.getElementById('tipoServicoForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = document.querySelector('#tipoServicoModal .modal-footer .btn-outline');
    if (cancelBtn) cancelBtn.textContent = readOnly ? 'Fechar' : 'Cancelar';

    let editBtn = document.getElementById('tipoServicoEditBtn');
    const footer = document.querySelector('#tipoServicoModal .modal-footer');
    if (!editBtn && footer) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'tipoServicoEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        footer.insertBefore(editBtn, submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        editBtn.onclick = () => {
            if (id) editarTipo(id);
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
        const partes = dataHora.split(' ');
        const data = partes[0].split('-');
        return `${data[2]}/${data[1]}/${data[0]} ${partes[1] || ''}`.trim();
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
