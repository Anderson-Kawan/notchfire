let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let statusFiltro = '';
let predioFiltro = '';
let departamentoParaExcluir = null;
let isLoading = false;

const API_URLS = {
    listar: '/api/departamentos/',
    listarPredios: '/api/predios-para-select/',
    criar: '/api/departamentos/criar/',
    editar: (id) => `/api/departamentos/${id}/editar/`,
    excluir: (id) => `/api/departamentos/${id}/excluir/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarPrediosParaSelect();
    carregarDepartamentos();
    configurarEventListeners();
});

async function carregarPrediosParaSelect() {
    try {
        const data = await fetchJson(API_URLS.listarPredios);
        preencherSelectPredios('predio', data.data || [], 'Selecione um prédio...');
        preencherSelectPredios('filtroPredio', data.data || [], 'Todos os prédios');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar prédios.', true);
    }
}

function preencherSelectPredios(id, predios, placeholder) {
    const select = document.getElementById(id);
    if (!select) return;

    select.innerHTML = `<option value="">${placeholder}</option>`;
    predios.forEach((predio) => {
        const option = document.createElement('option');
        option.value = predio.id;
        option.textContent = predio.nome;
        select.appendChild(option);
    });
}

async function carregarDepartamentos() {
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
        if (predioFiltro) params.set('predio_id', predioFiltro);

        const data = await fetchJson(`${API_URLS.listar}?${params.toString()}`);
        atualizarResumo(data);

        if (data.data && data.data.length > 0) {
            renderizarTabela(data.data);
        } else {
            mostrarSemDados();
        }

        renderizarPaginacao(data.total || 0);
    } catch (error) {
        mostrarErro(error.message || 'Não foi possível carregar os departamentos.');
    } finally {
        isLoading = false;
        mostrarLoading(false);
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchDepartamento');
    const clearBtn = document.getElementById('clearSearch');
    const sortIcon = document.querySelector('.sort-icon');
    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const filtroStatus = document.getElementById('filtroStatus');
    const filtroPredio = document.getElementById('filtroPredio');
    const departamentoForm = document.getElementById('departamentoForm');
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarDepartamentos();
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
            carregarDepartamentos();
        });
    }

    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarDepartamentos();
        });
    }

    if (filtroPredio) {
        filtroPredio.addEventListener('change', () => {
            predioFiltro = filtroPredio.value;
            currentPage = 1;
            carregarDepartamentos();
        });
    }

    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarDepartamentos();
        });
    }

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10);
            currentPage = 1;
            carregarDepartamentos();
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

    if (departamentoForm) {
        departamentoForm.addEventListener('submit', (event) => {
            event.preventDefault();
            salvarDepartamento();
        });
    }
}

function renderizarTabela(departamentosList) {
    const tbody = document.getElementById('departamentosTableBody');
    const noResults = document.getElementById('noResults');

    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = departamentosList.map((depto) => `
        <tr onclick="visualizarDepartamento(${depto.id})">
            <td class="departamento-nome">
                <span class="dept-avatar"><i class="fa-solid fa-building-user"></i></span>
                <div>
                    <strong>${escapeHtml(depto.nome)}</strong>
                    <span>${escapeHtml(depto.email || depto.telefone || 'Sem contato informado')}</span>
                </div>
            </td>
            <td>${escapeHtml(depto.descricao) || '-'}</td>
            <td>${escapeHtml(depto.localizacao) || '-'}</td>
            <td>${escapeHtml(depto.responsavel) || '-'}</td>
            <td>
                ${depto.predio_nome ? `<span class="badge badge-info">${escapeHtml(depto.predio_nome)}</span>` : '<span class="text-muted">Sem prédio</span>'}
            </td>
            <td>
                <span class="badge ${depto.status ? 'badge-success' : 'badge-danger'}">
                    ${depto.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${formatarData(depto.criado_em)}</td>
            <td class="actions" onclick="event.stopPropagation()">
                <button type="button" class="btn-icon" onclick="visualizarDepartamento(${depto.id})" title="Visualizar">
                    <i class="fa-solid fa-eye"></i>
                </button>
                ${canManage ? `
                <button type="button" class="btn-icon" onclick="editarDepartamento(${depto.id})" title="Editar">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="btn-icon btn-icon-danger" onclick="abrirModalExcluir(${depto.id})" title="Excluir">
                    <i class="fa-solid fa-trash"></i>
                </button>
                ` : ''}
                <button type="button" class="btn-icon" onclick="verFuncionarios(${depto.id})" title="Ver funcionários">
                    <i class="fa-solid fa-users"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function atualizarResumo(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryAtivos', data.total_ativos || 0);
    setText('summaryInativos', data.total_inativos || 0);
    setText('summaryPredios', data.total_com_predio || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('departamentosTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum departamento encontrado</p>
            ${canManageSystem() ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="abrirModalCriarDepartamento()">
                <i class="fa-solid fa-plus"></i> Criar departamento
            </button>
            ` : ''}
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
    carregarDepartamentos();
}

function abrirModalCriarDepartamento() {
    if (!canManageSystem()) return;

    setDepartamentoReadOnly(false);

    const modalTitle = document.getElementById('modalTitle');
    const departamentoForm = document.getElementById('departamentoForm');
    const departamentoId = document.getElementById('departamentoId');
    const statusSelect = document.getElementById('status');
    const predioSelect = document.getElementById('predio');
    const feedback = document.getElementById('formFeedback');

    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Novo Departamento';
    if (departamentoForm) departamentoForm.reset();
    if (departamentoId) departamentoId.value = '';
    if (statusSelect) statusSelect.value = 'true';
    if (predioSelect) predioSelect.value = '';
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    openModal('departamentoModal');
}

async function visualizarDepartamento(id) {
    try {
        const depto = await buscarDepartamento(id);
        preencherDepartamentoForm(depto);
        setText('modalTitle', '');
        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-eye"></i> Departamento';
        setDepartamentoReadOnly(true, id);
        openModal('departamentoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do departamento.', true);
    }
}

async function editarDepartamento(id) {
    if (!canManageSystem()) return;

    try {
        const depto = await buscarDepartamento(id);
        setText('modalTitle', '');
        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-pen"></i> Editar Departamento';
        preencherDepartamentoForm(depto);
        setDepartamentoReadOnly(false, id);

        const feedback = document.getElementById('formFeedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.classList.remove('show');
        }

        openModal('departamentoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do departamento.', true);
    }
}

async function salvarDepartamento() {
    if (!canManageSystem()) return;

    const id = document.getElementById('departamentoId').value;
    const nome = document.getElementById('nome').value.trim();
    const descricao = document.getElementById('descricao').value.trim();
    const localizacao = document.getElementById('localizacao').value.trim();
    const responsavel = document.getElementById('responsavel').value.trim();
    const email = document.getElementById('email').value.trim();
    const telefone = document.getElementById('telefone').value.trim();
    const predioId = document.getElementById('predio').value;
    const status = document.getElementById('status').value === 'true';

    if (!nome) {
        mostrarFormFeedback('O nome do departamento é obrigatório.');
        document.getElementById('nome').focus();
        return;
    }

    const submitBtn = document.querySelector('#departamentoForm button[type="submit"]');
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
                localizacao,
                responsavel,
                email,
                telefone,
                predio_id: predioId ? parseInt(predioId, 10) : null,
                status,
            }),
        });

        mostrarToast(data.message || (id ? 'Departamento atualizado com sucesso!' : 'Departamento criado com sucesso!'));
        fecharModal();
        carregarDepartamentos();
    } catch (error) {
        mostrarFormFeedback(error.message || 'Erro ao salvar departamento.');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function abrirModalExcluir(id) {
    if (!canManageSystem()) return;

    departamentoParaExcluir = id;

    try {
        const depto = await buscarDepartamento(id);
        setText('excluirNome', depto.nome);
        openModal('excluirModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do departamento.', true);
    }
}

async function confirmarExcluir() {
    if (!canManageSystem()) return;

    if (!departamentoParaExcluir) return;

    const confirmBtn = document.querySelector('#excluirModal .btn-danger');
    if (confirmBtn) confirmBtn.disabled = true;

    try {
        const data = await fetchJson(API_URLS.excluir(departamentoParaExcluir), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });

        mostrarToast(data.message || 'Departamento excluído com sucesso!');
        fecharModalExcluir();
        carregarDepartamentos();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao excluir departamento.', true);
    } finally {
        if (confirmBtn) confirmBtn.disabled = false;
    }
}

function fecharModal() {
    closeModal('departamentoModal');
    setDepartamentoReadOnly(false);
}

function fecharModalExcluir() {
    closeModal('excluirModal');
    departamentoParaExcluir = null;
}

function verFuncionarios(id) {
    mostrarToast(`Funcionários do departamento #${id} ainda serão conectados.`);
}

function preencherDepartamentoForm(depto) {
    setValue('departamentoId', depto.id);
    setValue('nome', depto.nome || '');
    setValue('descricao', depto.descricao || '');
    setValue('localizacao', depto.localizacao || '');
    setValue('responsavel', depto.responsavel || '');
    setValue('email', depto.email || '');
    setValue('telefone', depto.telefone || '');
    setValue('status', depto.status ? 'true' : 'false');
    setValue('predio', depto.predio_id || '');

    const feedback = document.getElementById('formFeedback');
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }
}

function setDepartamentoReadOnly(readOnly, id = null) {
    const form = document.getElementById('departamentoForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = document.querySelector('#departamentoModal .modal-footer .btn-outline');
    if (cancelBtn) cancelBtn.textContent = readOnly ? 'Fechar' : 'Cancelar';

    let editBtn = document.getElementById('departamentoEditBtn');
    const footer = document.querySelector('#departamentoModal .modal-footer');
    if (!editBtn && footer) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'departamentoEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        footer.insertBefore(editBtn, submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        editBtn.onclick = () => {
            if (id) editarDepartamento(id);
        };
    }
}

function mostrarLoading(show) {
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('departamentosTableBody');
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

function mostrarErro(mensagem) {
    const tbody = document.getElementById('departamentosTableBody');
    const noResults = document.getElementById('noResults');
    if (tbody) tbody.innerHTML = '';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button type="button" class="btn btn-primary btn-sm" onclick="carregarDepartamentos()">
                Tentar novamente
            </button>
        `;
        noResults.style.display = 'block';
    }
}

async function buscarDepartamento(id) {
    const data = await fetchJson(`${API_URLS.listar}?id=${id}`);
    const depto = (data.data || []).find((item) => item.id === id);
    if (!depto) throw new Error('Departamento não encontrado.');
    return depto;
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

function formatarData(data) {
    if (!data) return '-';
    try {
        const partes = data.split('-');
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    } catch (error) {
        return data;
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
