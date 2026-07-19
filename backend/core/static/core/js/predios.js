let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let statusFiltro = '';
let predioParaExcluir = null;

const API_URLS = {
    listar: '/api/predios/',
    criar: '/api/predios/criar/',
    editar: (id) => `/api/predios/${id}/editar/`,
    excluir: (id) => `/api/predios/${id}/excluir/`,
    departamentos: (id) => `/api/predios/${id}/departamentos/`,
    equipamentosDepartamento: (id) => `/api/departamentos/${id}/equipamentos/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarPredios();
    configurarEventListeners();
});

async function carregarPredios() {
    const loading = document.getElementById('loading');
    const noResults = document.getElementById('noResults');
    if (loading) loading.style.display = 'block';
    if (noResults) noResults.style.display = 'none';

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
        mostrarErro(error.message || 'Não foi possível carregar os prédios.');
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchPredio');
    const clearBtn = document.getElementById('clearSearch');
    const filtroStatus = document.getElementById('filtroStatus');
    const sortIcon = document.querySelector('.sort-icon');
    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const form = document.getElementById('predioForm');
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarPredios();
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
            carregarPredios();
        });
    }

    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarPredios();
        });
    }

    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarPredios();
        });
    }

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10);
            currentPage = 1;
            carregarPredios();
        });
    }

    document.querySelectorAll('.close').forEach((btn) => {
        btn.addEventListener('click', () => {
            fecharModal();
            fecharModalExcluir();
        });
    });

    document.querySelectorAll('.close-view').forEach((btn) => {
        btn.addEventListener('click', fecharModalView);
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target !== modal) return;
            fecharModal();
            fecharModalExcluir();
            fecharModalView();
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        fecharModal();
        fecharModalExcluir();
        fecharModalView();
    });

    if (form) {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            salvarPredio();
        });
    }
}

function renderizarTabela(prediosList) {
    const tbody = document.getElementById('prediosTableBody');
    const noResults = document.getElementById('noResults');
    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = prediosList.map((predio) => `
        <tr onclick="verDepartamentos(${predio.id})">
            <td class="predio-nome">
                <span class="building-avatar"><i class="fa-solid fa-building"></i></span>
                <div>
                    <strong>${escapeHtml(predio.nome)}</strong>
                    <span>${escapeHtml(predio.endereco) || 'Sem endereço informado'}</span>
                </div>
            </td>
            <td>${escapeHtml(predio.endereco) || '-'}</td>
            <td>${escapeHtml(predio.descricao) || '-'}</td>
            <td>${renderDepartamentos(predio)}</td>
            <td>
                <span class="badge ${predio.status ? 'badge-success' : 'badge-danger'}">
                    ${predio.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${formatarDataHora(predio.criado_em)}</td>
            <td class="actions" onclick="event.stopPropagation()">
                <button class="btn-icon" onclick="verDepartamentos(${predio.id})" title="Ver departamentos">
                    <i class="fa-solid fa-building-user"></i>
                </button>
                ${canManage ? `
                <button class="btn-icon" onclick="editarPredio(${predio.id})" title="Editar">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button class="btn-icon btn-icon-danger" onclick="abrirModalExcluir(${predio.id})" title="Excluir">
                    <i class="fa-solid fa-trash"></i>
                </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

function renderDepartamentos(predio) {
    if (!predio.departamentos || predio.departamentos.length === 0) {
        return '<span class="text-muted">Nenhum</span>';
    }

    const displayDeptos = predio.departamentos.slice(0, 2);
    let html = displayDeptos.map((depto) => `<span class="departamentos-badge">${escapeHtml(depto.nome)}</span>`).join('');

    if (predio.departamentos.length > 2) {
        html += `<span class="departamentos-badge">+${predio.departamentos.length - 2}</span>`;
    }

    return html;
}

function atualizarResumo(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryAtivos', data.total_ativos || 0);
    setText('summaryInativos', data.total_inativos || 0);
    setText('summaryDepartamentos', data.total_departamentos || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('prediosTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum prédio encontrado</p>
            ${canManageSystem() ? `
            <button class="btn btn-primary btn-sm" onclick="abrirModalCriar()">
                <i class="fa-solid fa-plus"></i> Criar prédio
            </button>
            ` : ''}
        `;
        noResults.style.display = 'block';
    }
}

function mostrarErro(mensagem) {
    const tbody = document.getElementById('prediosTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button class="btn btn-primary btn-sm" onclick="carregarPredios()">Tentar novamente</button>
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
    carregarPredios();
}

function abrirModalCriar() {
    if (!canManageSystem()) return;

    setPredioReadOnly(false);

    const modalTitle = document.getElementById('modalTitle');
    const form = document.getElementById('predioForm');
    const predioId = document.getElementById('predioId');
    const statusSelect = document.getElementById('status');
    const feedback = document.getElementById('formFeedback');

    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Novo Prédio';
    if (form) form.reset();
    if (predioId) predioId.value = '';
    if (statusSelect) statusSelect.value = 'true';
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    openModal('predioModal');
}

async function visualizarPredio(id) {
    try {
        const predio = await buscarPredio(id);
        preencherPredioForm(predio);

        const modalTitle = document.getElementById('modalTitle');
        if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-eye"></i> Prédio';

        setPredioReadOnly(true, id);
        openModal('predioModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do prédio.', true);
    }
}

async function verDepartamentos(id) {
    try {
        const predio = await buscarPredio(id);
        const departamentos = await buscarDepartamentosPredio(id);
        const viewPredioNome = document.getElementById('viewPredioNome');
        const viewDepartamentosList = document.getElementById('viewDepartamentosList');
        const viewDepartamentoNome = document.getElementById('viewDepartamentoNome');
        const viewEquipamentosList = document.getElementById('viewEquipamentosList');
        const viewDepartamentosCount = document.getElementById('viewDepartamentosCount');
        const viewEquipamentosCount = document.getElementById('viewEquipamentosCount');

        if (viewPredioNome) viewPredioNome.textContent = predio.nome;
        if (viewDepartamentoNome) viewDepartamentoNome.textContent = 'Equipamentos';
        if (viewDepartamentosCount) viewDepartamentosCount.textContent = departamentos.length;
        if (viewEquipamentosCount) viewEquipamentosCount.textContent = '0';
        if (viewEquipamentosList) viewEquipamentosList.innerHTML = renderEmptyState('fa-fire-extinguisher', 'Nenhum equipamento selecionado.');

        if (viewDepartamentosList) {
            if (departamentos.length > 0) {
                viewDepartamentosList.innerHTML = departamentos.map((depto) => `
                    <button type="button" class="departamento-item departamento-item-action" data-departamento-id="${depto.id}" onclick="verEquipamentosDepartamento(${depto.id}, this)">
                        <span class="departamento-item-icon"><i class="fa-solid fa-building-user"></i></span>
                        <span class="departamento-item-info">
                            <strong class="departamento-item-nome">${escapeHtml(depto.nome)}</strong>
                            <small>${escapeHtml(depto.predio_nome) || '-'}</small>
                        </span>
                        <i class="fa-solid fa-chevron-right departamento-item-arrow"></i>
                    </button>
                `).join('');
            } else {
                viewDepartamentosList.innerHTML = renderEmptyState('fa-building-user', 'Nenhum departamento cadastrado neste prédio.');
            }
        }

        openModal('viewDepartamentosModal');

        const firstDepartment = viewDepartamentosList?.querySelector('.departamento-item-action');
        if (firstDepartment) {
            verEquipamentosDepartamento(firstDepartment.dataset.departamentoId, firstDepartment);
        }
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar departamentos.', true);
    }
}

async function verEquipamentosDepartamento(id, trigger = null) {
    const viewDepartamentoNome = document.getElementById('viewDepartamentoNome');
    const viewEquipamentosList = document.getElementById('viewEquipamentosList');
    const viewEquipamentosCount = document.getElementById('viewEquipamentosCount');
    const departamentoNome = trigger?.querySelector('.departamento-item-nome')?.textContent || 'Departamento';

    document.querySelectorAll('.departamento-item-action').forEach((item) => {
        item.classList.remove('selected');
    });
    if (trigger) trigger.classList.add('selected');
    if (viewDepartamentoNome) viewDepartamentoNome.textContent = departamentoNome;
    if (viewEquipamentosCount) viewEquipamentosCount.textContent = '0';
    if (viewEquipamentosList) {
        viewEquipamentosList.innerHTML = renderLoadingState();
    }

    try {
        const equipamentos = await buscarEquipamentosDepartamento(id);
        if (viewEquipamentosCount) viewEquipamentosCount.textContent = equipamentos.length;
        if (viewEquipamentosList) {
            viewEquipamentosList.innerHTML = renderEquipamentosDepartamento(equipamentos);
        }
    } catch (error) {
        if (viewEquipamentosList) {
            viewEquipamentosList.innerHTML = '<p class="text-muted">Não foi possível carregar os equipamentos.</p>';
        }
        mostrarToast(error.message || 'Erro ao carregar equipamentos.', true);
    }
}

function renderEquipamentosDepartamento(equipamentos) {
    if (!equipamentos.length) {
        return renderEmptyState('fa-fire-extinguisher', 'Nenhum equipamento cadastrado neste departamento.');
    }

    return equipamentos.map((equipamento) => {
        const ativo = equipamento.status === 'ativo' || equipamento.ativo === true;
        const statusLabel = ativo ? 'Ativo' : 'Inativo';
        const detalheUrl = equipamento.detalhe_url || `/equipamentos/${equipamento.id}/`;

        return `
            <a class="equipamento-item" href="${escapeHtml(detalheUrl)}">
                <span class="equipamento-icon"><i class="fa-solid fa-fire-extinguisher"></i></span>
                <span class="equipamento-info">
                    <strong>${escapeHtml(equipamento.nome)}</strong>
                    <small>${escapeHtml(equipamento.codigo) || 'Sem código'}</small>
                </span>
                <span class="badge ${ativo ? 'badge-success' : 'badge-danger'}">${statusLabel}</span>
                <i class="fa-solid fa-arrow-up-right-from-square equipamento-link-icon"></i>
            </a>
        `;
    }).join('');
}

function renderLoadingState() {
    return `
        <div class="drilldown-state">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <span>Carregando...</span>
        </div>
    `;
}

function renderEmptyState(icon, message) {
    return `
        <div class="drilldown-state">
            <i class="fa-solid ${icon}"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
}

function fecharModalView() {
    closeModal('viewDepartamentosModal');
}

async function editarPredio(id) {
    if (!canManageSystem()) return;

    try {
        const predio = await buscarPredio(id);
        const modalTitle = document.getElementById('modalTitle');

        if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-pen"></i> Editar Prédio';
        preencherPredioForm(predio);
        setPredioReadOnly(false, id);

        openModal('predioModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do prédio.', true);
    }
}

async function salvarPredio() {
    if (!canManageSystem()) return;

    const id = document.getElementById('predioId').value;
    const nome = document.getElementById('nome').value.trim();
    const endereco = document.getElementById('endereco').value.trim();
    const descricao = document.getElementById('descricao').value.trim();
    const status = document.getElementById('status').value === 'true';
    const feedback = document.getElementById('formFeedback');

    if (!nome) {
        mostrarFormFeedback('O nome do prédio é obrigatório.');
        document.getElementById('nome').focus();
        return;
    }

    const submitBtn = document.querySelector('#predioForm button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const data = await fetchJson(id ? API_URLS.editar(id) : API_URLS.criar, {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ nome, endereco, descricao, status }),
        });

        if (feedback) feedback.classList.remove('show');
        mostrarToast(data.message || (id ? 'Prédio atualizado com sucesso!' : 'Prédio criado com sucesso!'));
        fecharModal();
        carregarPredios();
    } catch (error) {
        mostrarFormFeedback(error.message || 'Erro ao salvar prédio.');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function abrirModalExcluir(id) {
    if (!canManageSystem()) return;

    predioParaExcluir = id;

    try {
        const predio = await buscarPredio(id);
        setText('excluirNome', predio.nome);
        openModal('excluirModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do prédio.', true);
    }
}

async function confirmarExcluir() {
    if (!canManageSystem()) return;

    if (!predioParaExcluir) return;

    const confirmBtn = document.querySelector('#excluirModal .btn-danger');
    if (confirmBtn) confirmBtn.disabled = true;

    try {
        const data = await fetchJson(API_URLS.excluir(predioParaExcluir), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });

        mostrarToast(data.message || 'Prédio excluído com sucesso!');
        fecharModalExcluir();
        carregarPredios();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao excluir prédio.', true);
    } finally {
        if (confirmBtn) confirmBtn.disabled = false;
    }
}

function fecharModal() {
    closeModal('predioModal');
    setPredioReadOnly(false);
}

function fecharModalExcluir() {
    closeModal('excluirModal');
    predioParaExcluir = null;
}

async function buscarPredio(id) {
    const data = await fetchJson(`${API_URLS.listar}?id=${id}`);
    const predio = (data.data || []).find((item) => item.id === id);
    if (!predio) throw new Error('Prédio não encontrado.');
    return predio;
}

async function buscarDepartamentosPredio(id) {
    const data = await fetchJson(API_URLS.departamentos(id));
    return Array.isArray(data) ? data : (data.data || data.departamentos || []);
}

async function buscarEquipamentosDepartamento(id) {
    const data = await fetchJson(API_URLS.equipamentosDepartamento(id));
    return Array.isArray(data) ? data : (data.data || data.equipamentos || []);
}

function preencherPredioForm(predio) {
    setValue('predioId', predio.id);
    setValue('nome', predio.nome || '');
    setValue('endereco', predio.endereco || '');
    setValue('descricao', predio.descricao || '');
    setValue('status', predio.status ? 'true' : 'false');

    const feedback = document.getElementById('formFeedback');
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }
}

function setPredioReadOnly(readOnly, id = null) {
    const form = document.getElementById('predioForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = document.querySelector('#predioModal .modal-footer .btn-outline');
    if (cancelBtn) cancelBtn.textContent = readOnly ? 'Fechar' : 'Cancelar';

    let editBtn = document.getElementById('predioEditBtn');
    const footer = document.querySelector('#predioModal .modal-footer');
    if (!editBtn && footer) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'predioEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        footer.insertBefore(editBtn, submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        editBtn.onclick = () => {
            if (id) editarPredio(id);
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
        return `${data[2]}/${data[1]}/${data[0]} ${partes[1] || ''}`;
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
