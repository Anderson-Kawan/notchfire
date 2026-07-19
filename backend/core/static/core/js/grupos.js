let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let statusFiltro = '';
let grupoParaExcluir = null;
let isLoading = false;
const equipamentosGrupoState = {
    grupoId: null,
    grupoNome: '',
    page: 1,
    rows: 8,
    search: '',
    status: '',
};

const API_URLS = {
    listar: '/api/grupos/',
    criar: '/api/grupos/criar/',
    editar: (id) => `/api/grupos/${id}/editar/`,
    excluir: (id) => `/api/grupos/${id}/excluir/`,
    equipamentos: '/api/equipamentos/',
    detalheEquipamento: (id) => `/equipamentos/${id}/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarGrupos();
    configurarEventListeners();
});

async function carregarGrupos() {
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
        mostrarErro(error.message || 'Não foi possível carregar os grupos.');
    } finally {
        isLoading = false;
        mostrarLoading(false);
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchGrupo');
    const clearBtn = document.getElementById('clearSearch');
    const filtroStatus = document.getElementById('filtroStatus');
    const sortIcon = document.querySelector('.sort-icon');
    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const grupoForm = document.getElementById('grupoForm');
    const searchEquipamentoGrupo = document.getElementById('searchEquipamentoGrupo');
    const clearSearchEquipamentosGrupo = document.getElementById('clearSearchEquipamentosGrupo');
    const filtroStatusEquipamentosGrupo = document.getElementById('filtroStatusEquipamentosGrupo');
    const rowsPerPageEquipamentosGrupo = document.getElementById('rowsPerPageEquipamentosGrupo');
    let debounceTimer;
    let equipamentosGrupoDebounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarGrupos();
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
            carregarGrupos();
        });
    }

    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarGrupos();
        });
    }

    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarGrupos();
        });
    }

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10);
            currentPage = 1;
            carregarGrupos();
        });
    }

    document.querySelectorAll('.close').forEach((btn) => {
        btn.addEventListener('click', () => {
            fecharModal();
            fecharModalExcluir();
            fecharModalEquipamentosGrupo();
        });
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target !== modal) return;
            fecharModal();
            fecharModalExcluir();
            fecharModalEquipamentosGrupo();
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        fecharModal();
        fecharModalExcluir();
        fecharModalEquipamentosGrupo();
    });

    if (grupoForm) {
        grupoForm.addEventListener('submit', (event) => {
            event.preventDefault();
            salvarGrupo();
        });
    }

    if (searchEquipamentoGrupo) {
        searchEquipamentoGrupo.addEventListener('input', (event) => {
            clearTimeout(equipamentosGrupoDebounceTimer);
            equipamentosGrupoDebounceTimer = setTimeout(() => {
                equipamentosGrupoState.search = event.target.value.trim();
                equipamentosGrupoState.page = 1;
                if (clearSearchEquipamentosGrupo) {
                    clearSearchEquipamentosGrupo.style.display = equipamentosGrupoState.search ? 'flex' : 'none';
                }
                carregarEquipamentosGrupo();
            }, 280);
        });
    }

    if (clearSearchEquipamentosGrupo) {
        clearSearchEquipamentosGrupo.addEventListener('click', () => {
            if (searchEquipamentoGrupo) searchEquipamentoGrupo.value = '';
            equipamentosGrupoState.search = '';
            equipamentosGrupoState.page = 1;
            clearSearchEquipamentosGrupo.style.display = 'none';
            carregarEquipamentosGrupo();
        });
    }

    if (filtroStatusEquipamentosGrupo) {
        filtroStatusEquipamentosGrupo.addEventListener('change', () => {
            equipamentosGrupoState.status = filtroStatusEquipamentosGrupo.value;
            equipamentosGrupoState.page = 1;
            carregarEquipamentosGrupo();
        });
    }

    if (rowsPerPageEquipamentosGrupo) {
        rowsPerPageEquipamentosGrupo.addEventListener('change', () => {
            equipamentosGrupoState.rows = parseInt(rowsPerPageEquipamentosGrupo.value, 10);
            equipamentosGrupoState.page = 1;
            carregarEquipamentosGrupo();
        });
    }
}

function renderizarTabela(gruposList) {
    const tbody = document.getElementById('gruposTableBody');
    const noResults = document.getElementById('noResults');

    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = gruposList.map((grupo) => `
        <tr onclick="visualizarGrupo(${grupo.id})">
            <td class="grupo-nome">
                <span class="group-avatar"><i class="fa-solid fa-layer-group"></i></span>
                <div>
                    <strong>${escapeHtml(grupo.nome)}</strong>
                    <span>${grupo.equipamentos} equipamento${grupo.equipamentos === 1 ? '' : 's'} vinculado${grupo.equipamentos === 1 ? '' : 's'}</span>
                </div>
            </td>
            <td>${escapeHtml(grupo.descricao) || '-'}</td>
            <td>
                <span class="badge ${grupo.equipamentos > 0 ? 'badge-info' : 'badge-secondary'}">
                    ${grupo.equipamentos}
                </span>
            </td>
            <td>
                <span class="badge ${grupo.status ? 'badge-success' : 'badge-danger'}">
                    ${grupo.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${formatarData(grupo.criado_em)}</td>
            <td class="actions" onclick="event.stopPropagation()">
                <button type="button" class="btn-icon" onclick="visualizarGrupo(${grupo.id})" title="Visualizar">
                    <i class="fa-solid fa-eye"></i>
                </button>
                ${canManage ? `
                <button type="button" class="btn-icon" onclick="editarGrupo(${grupo.id})" title="Editar">
                    <i class="fa-solid fa-pen"></i>
                </button>
                ` : ''}
                <button type="button" class="btn-icon" onclick="verEquipamentos(${grupo.id})" title="Ver equipamentos">
                    <i class="fa-solid fa-fire-extinguisher"></i>
                </button>
                ${canManage ? `
                <button type="button" class="btn-icon btn-icon-danger" onclick="abrirModalExcluir(${grupo.id})" title="Excluir">
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
    setText('summaryEquipamentos', data.total_equipamentos || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('gruposTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum grupo encontrado</p>
            ${canManageSystem() ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="abrirModalCriarGrupo()">
                <i class="fa-solid fa-plus"></i> Criar grupo
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
    carregarGrupos();
}

function abrirModalCriarGrupo() {
    if (!canManageSystem()) return;

    setGrupoReadOnly(false);

    const modalTitle = document.getElementById('modalTitle');
    const grupoForm = document.getElementById('grupoForm');
    const grupoId = document.getElementById('grupoId');
    const statusSelect = document.getElementById('status');
    const feedback = document.getElementById('formFeedback');

    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Novo Grupo';
    if (grupoForm) grupoForm.reset();
    if (grupoId) grupoId.value = '';
    if (statusSelect) statusSelect.value = 'true';
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    openModal('grupoModal');
}

async function visualizarGrupo(id) {
    try {
        const grupo = await buscarGrupo(id);
        preencherGrupoForm(grupo);
        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-eye"></i> Grupo';
        setGrupoReadOnly(true, id);
        openModal('grupoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do grupo.', true);
    }
}

async function editarGrupo(id) {
    if (!canManageSystem()) return;

    try {
        const grupo = await buscarGrupo(id);

        document.getElementById('modalTitle').innerHTML = '<i class="fa-solid fa-pen"></i> Editar Grupo';
        preencherGrupoForm(grupo);
        setGrupoReadOnly(false, id);

        openModal('grupoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do grupo.', true);
    }
}

async function salvarGrupo() {
    if (!canManageSystem()) return;

    const id = document.getElementById('grupoId').value;
    const nome = document.getElementById('nome').value.trim();
    const descricao = document.getElementById('descricao').value.trim();
    const status = document.getElementById('status').value === 'true';

    if (!nome) {
        mostrarFormFeedback('O nome do grupo é obrigatório.');
        document.getElementById('nome').focus();
        return;
    }

    const submitBtn = document.querySelector('#grupoForm button[type="submit"]');
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

        mostrarToast(data.message || (id ? 'Grupo atualizado com sucesso!' : 'Grupo criado com sucesso!'));
        fecharModal();
        carregarGrupos();
    } catch (error) {
        mostrarFormFeedback(error.message || 'Erro ao salvar grupo.');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function abrirModalExcluir(id) {
    if (!canManageSystem()) return;

    grupoParaExcluir = id;

    try {
        const grupo = await buscarGrupo(id);
        setText('excluirNome', grupo.nome);
        openModal('excluirModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar dados do grupo.', true);
    }
}

async function confirmarExcluir() {
    if (!canManageSystem()) return;

    if (!grupoParaExcluir) return;

    const confirmBtn = document.querySelector('#excluirModal .btn-danger');
    if (confirmBtn) confirmBtn.disabled = true;

    try {
        const data = await fetchJson(API_URLS.excluir(grupoParaExcluir), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });

        mostrarToast(data.message || 'Grupo excluído com sucesso!');
        fecharModalExcluir();
        carregarGrupos();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao excluir grupo.', true);
    } finally {
        if (confirmBtn) confirmBtn.disabled = false;
    }
}

function fecharModal() {
    closeModal('grupoModal');
    setGrupoReadOnly(false);
}

function fecharModalExcluir() {
    closeModal('excluirModal');
    grupoParaExcluir = null;
}

async function verEquipamentos(id) {
    try {
        const grupo = await buscarGrupo(id);
        abrirModalEquipamentosGrupo(grupo);
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar equipamentos do grupo.', true);
    }
}

function abrirModalEquipamentosGrupo(grupo) {
    equipamentosGrupoState.grupoId = grupo.id;
    equipamentosGrupoState.grupoNome = grupo.nome || `Grupo #${grupo.id}`;
    equipamentosGrupoState.page = 1;
    equipamentosGrupoState.search = '';
    equipamentosGrupoState.status = '';

    setText('equipamentosGrupoTitle', equipamentosGrupoState.grupoNome);
    setText('equipamentosGrupoSubtitle', `${grupo.equipamentos || 0} equipamento${grupo.equipamentos === 1 ? '' : 's'} vinculado${grupo.equipamentos === 1 ? '' : 's'}`);
    setText('equipamentosGrupoTotal', grupo.equipamentos || 0);
    setText('equipamentosGrupoAtivos', 0);
    setText('equipamentosGrupoInativos', 0);
    setValue('searchEquipamentoGrupo', '');
    setValue('filtroStatusEquipamentosGrupo', '');

    const clearBtn = document.getElementById('clearSearchEquipamentosGrupo');
    if (clearBtn) clearBtn.style.display = 'none';

    openModal('equipamentosGrupoModal');
    carregarEquipamentosGrupo();
}

function fecharModalEquipamentosGrupo() {
    closeModal('equipamentosGrupoModal');
    equipamentosGrupoState.grupoId = null;
    equipamentosGrupoState.grupoNome = '';
}

async function carregarEquipamentosGrupo() {
    if (!equipamentosGrupoState.grupoId) return;

    mostrarLoadingEquipamentosGrupo(true);

    try {
        const params = new URLSearchParams({
            grupo_id: equipamentosGrupoState.grupoId,
            page: equipamentosGrupoState.page,
            rows: equipamentosGrupoState.rows,
            search: equipamentosGrupoState.search,
            sort: 'asc',
        });

        if (equipamentosGrupoState.status) params.set('status', equipamentosGrupoState.status);

        const data = await fetchJson(`${API_URLS.equipamentos}?${params.toString()}`);
        atualizarResumoEquipamentosGrupo(data);

        if (data.data && data.data.length > 0) {
            renderizarEquipamentosGrupo(data.data);
        } else {
            mostrarSemEquipamentosGrupo();
        }

        renderizarPaginacaoEquipamentosGrupo(data.total || 0);
    } catch (error) {
        mostrarErroEquipamentosGrupo(error.message || 'Não foi possível carregar os equipamentos do grupo.');
    } finally {
        mostrarLoadingEquipamentosGrupo(false);
    }
}

function atualizarResumoEquipamentosGrupo(data) {
    const total = data.total || 0;
    setText('equipamentosGrupoTotal', total);
    setText('equipamentosGrupoAtivos', data.total_ativos || 0);
    setText('equipamentosGrupoInativos', data.total_inativos || 0);
    setText('equipamentosGrupoSubtitle', `${total} equipamento${total === 1 ? '' : 's'} encontrado${total === 1 ? '' : 's'}`);
}

function renderizarEquipamentosGrupo(equipamentosList) {
    const list = document.getElementById('equipamentosGrupoList');
    const noResults = document.getElementById('equipamentosGrupoNoResults');

    if (!list) return;
    if (noResults) noResults.style.display = 'none';

    list.innerHTML = equipamentosList.map((equip) => {
        const detalheUrl = equip.detalhe_url || API_URLS.detalheEquipamento(equip.id);
        const codigo = equip.codigo || equip.numero_serie || '-';
        const localizacao = equip.localizacao || equip.predio_nome || equip.local || '-';
        const ativo = equip.status === true || equip.ativo === true;

        return `
            <a class="equipamento-item equipamento-grupo-item" href="${escapeHtml(detalheUrl)}">
                <span class="equipamento-icon"><i class="fa-solid fa-fire-extinguisher"></i></span>
                <span class="equipamento-info">
                    <strong>${escapeHtml(equip.nome)}</strong>
                    <small>${escapeHtml(codigo)} · ${escapeHtml(equip.tipo_nome || 'Sem tipo')}</small>
                    <small>${escapeHtml(localizacao)}</small>
                </span>
                <span class="badge ${ativo ? 'badge-success' : 'badge-danger'}">${ativo ? 'Ativo' : 'Inativo'}</span>
                <i class="fa-solid fa-arrow-up-right-from-square equipamento-link-icon"></i>
            </a>
        `;
    }).join('');
}

function mostrarSemEquipamentosGrupo() {
    const list = document.getElementById('equipamentosGrupoList');
    const noResults = document.getElementById('equipamentosGrupoNoResults');
    const temFiltro = equipamentosGrupoState.search || equipamentosGrupoState.status;

    if (list) list.innerHTML = '';
    if (!noResults) return;

    noResults.innerHTML = `
        <i class="fa-solid fa-folder-open"></i>
        <span>${temFiltro ? 'Nenhum equipamento encontrado com esses filtros.' : 'Nenhum equipamento vinculado a este grupo.'}</span>
        ${canManageSystem() ? `
        <a href="/equipamentos/criar/" class="btn btn-primary btn-sm">
            <i class="fa-solid fa-plus"></i> Criar equipamento
        </a>
        ` : ''}
    `;
    noResults.style.display = 'block';
}

function mostrarErroEquipamentosGrupo(mensagem) {
    const list = document.getElementById('equipamentosGrupoList');
    const noResults = document.getElementById('equipamentosGrupoNoResults');

    if (list) list.innerHTML = '';
    if (!noResults) return;

    noResults.innerHTML = `
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>${escapeHtml(mensagem)}</span>
        <button type="button" class="btn btn-primary btn-sm" onclick="carregarEquipamentosGrupo()">
            Tentar novamente
        </button>
    `;
    noResults.style.display = 'block';
}

function mostrarLoadingEquipamentosGrupo(show) {
    const loading = document.getElementById('equipamentosGrupoLoading');
    const list = document.getElementById('equipamentosGrupoList');
    const noResults = document.getElementById('equipamentosGrupoNoResults');

    if (loading) loading.style.display = show ? 'block' : 'none';
    if (list) list.style.display = show ? 'none' : '';
    if (show && noResults) noResults.style.display = 'none';
}

function renderizarPaginacaoEquipamentosGrupo(total) {
    const totalPages = Math.ceil(total / equipamentosGrupoState.rows);
    const paginationDiv = document.getElementById('equipamentosGrupoPaginationControls');

    if (!paginationDiv) return;

    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }

    const current = equipamentosGrupoState.page;
    const startPage = Math.max(1, current - 2);
    const endPage = Math.min(totalPages, current + 2);

    let html = `
        <button class="page-btn" onclick="mudarPaginaEquipamentosGrupo(1)" ${current === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-left"></i>
        </button>
        <button class="page-btn" onclick="mudarPaginaEquipamentosGrupo(${current - 1})" ${current === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-left"></i>
        </button>
    `;

    if (startPage > 1) html += '<span class="page-info">...</span>';

    for (let page = startPage; page <= endPage; page += 1) {
        html += `
            <button class="page-btn ${page === current ? 'page-active' : ''}" onclick="mudarPaginaEquipamentosGrupo(${page})">
                ${page}
            </button>
        `;
    }

    if (endPage < totalPages) html += '<span class="page-info">...</span>';

    html += `
        <button class="page-btn" onclick="mudarPaginaEquipamentosGrupo(${current + 1})" ${current === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-right"></i>
        </button>
        <button class="page-btn" onclick="mudarPaginaEquipamentosGrupo(${totalPages})" ${current === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-right"></i>
        </button>
    `;

    paginationDiv.innerHTML = html;
}

function mudarPaginaEquipamentosGrupo(page) {
    equipamentosGrupoState.page = Math.max(1, page);
    carregarEquipamentosGrupo();
}

function preencherGrupoForm(grupo) {
    setValue('grupoId', grupo.id);
    setValue('nome', grupo.nome || '');
    setValue('descricao', grupo.descricao || '');
    setValue('status', grupo.status ? 'true' : 'false');

    const feedback = document.getElementById('formFeedback');
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }
}

function setGrupoReadOnly(readOnly, id = null) {
    const form = document.getElementById('grupoForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = document.querySelector('#grupoModal .modal-footer .btn-outline');
    if (cancelBtn) cancelBtn.textContent = readOnly ? 'Fechar' : 'Cancelar';

    let editBtn = document.getElementById('grupoEditBtn');
    const footer = document.querySelector('#grupoModal .modal-footer');
    if (!editBtn && footer) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'grupoEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        footer.insertBefore(editBtn, submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly && canManageSystem() ? '' : 'none';
        editBtn.onclick = () => {
            if (id) editarGrupo(id);
        };
    }
}

function mostrarLoading(show) {
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('gruposTableBody');
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
    const tbody = document.getElementById('gruposTableBody');
    const noResults = document.getElementById('noResults');
    if (tbody) tbody.innerHTML = '';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button type="button" class="btn btn-primary btn-sm" onclick="carregarGrupos()">
                Tentar novamente
            </button>
        `;
        noResults.style.display = 'block';
    }
}

async function buscarGrupo(id) {
    const data = await fetchJson(`${API_URLS.listar}?id=${id}`);
    const grupo = (data.data || []).find((item) => item.id === id);
    if (!grupo) throw new Error('Grupo não encontrado.');
    return grupo;
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
