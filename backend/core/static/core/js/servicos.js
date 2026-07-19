let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'desc';
let dataInicio = '';
let dataFim = '';
let siteFiltro = '';
let statusFiltro = '';
let isLoading = false;
let equipamentoFiltroUrl = '';

let equipamentosPage = 1;
let equipamentosRows = 5;
let equipamentosSearch = '';
let equipamentosGrupoFiltro = '';
let equipamentosTotal = 0;

let equipamentoSelecionado = null;
let tipoServicoSelecionado = null;
let servicoAtual = null;
let rascunhoId = null;
let acaoItemId = null;
let autosaveTimer = null;
let ultimoRascunhoAssinado = '';

const DRAFT_CACHE_PREFIX = 'notchfire:checklist-draft:';

const API_URLS = {
    listar: '/api/servicos/',
    listarEquipamentos: '/api/equipamentos-para-servico/',
    listarTiposServico: '/api/tipos-servico-para-equipamento/',
    criar: '/api/servicos/criar/',
    atualizar: (id) => `/api/servicos/${id}/atualizar/`,
    detalhes: (id) => `/api/servicos/${id}/`,
    acaoCriar: '/api/acoes-corretivas/criar/',
    grupos: '/api/grupos-para-select/',
    rascunho: '/api/servicos/rascunho/',
    descartar: (id) => `/api/servicos/${id}/descartar/`,
    exportarRelatorio: (equipamentoId) => `/relatorios/exportar/condensado/?equipamento_id=${equipamentoId}`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    equipamentoFiltroUrl = params.get('equipamento_id') || '';

    carregarServicos();
    configurarEventListeners();
    processarAtalhoServicoUrl();
});

window.addEventListener('beforeunload', () => {
    if (canManageSystem() && document.getElementById('checklistModal')?.classList.contains('open')) {
        salvarCacheLocalChecklist();
        enviarRascunhoBeacon();
    }
});

async function carregarServicos() {
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

        if (siteFiltro) params.set('site', siteFiltro);
        if (statusFiltro) params.set('status', statusFiltro);
        if (dataInicio) params.set('data_inicio', dataInicio);
        if (dataFim) params.set('data_fim', dataFim);
        if (equipamentoFiltroUrl) params.set('equipamento_id', equipamentoFiltroUrl);

        const data = await fetchJson(`${API_URLS.listar}?${params.toString()}`);
        atualizarResumo(data);

        if (data.data && data.data.length > 0) {
            renderizarTabela(data.data);
        } else {
            mostrarSemDados();
        }

        renderizarPaginacao(data.total || 0);
    } catch (error) {
        mostrarErro(error.message || 'Não foi possível carregar os serviços.');
    } finally {
        isLoading = false;
        mostrarLoading(false);
    }
}

async function processarAtalhoServicoUrl() {
    const params = new URLSearchParams(window.location.search);
    const rascunhoParametro = parseInt(params.get('rascunho_id'), 10);
    const equipamentoId = parseInt(params.get('equipamento_id'), 10);
    const tipoServicoId = parseInt(params.get('tipo_servico_id'), 10);
    const restoreLocalKey = params.get('restore_local') || '';

    if (!canManageSystem() && (!Number.isNaN(rascunhoParametro) || restoreLocalKey || tipoServicoId)) {
        mostrarToast('Seu perfil permite visualizar serviços, mas não iniciar ou retomar checklists.', true);
        return;
    }

    if (!Number.isNaN(rascunhoParametro)) {
        await carregarRascunho(rascunhoParametro);
        return;
    }

    if (!equipamentoId) return;

    try {
        await iniciarServicoDoEquipamento(equipamentoId, Number.isNaN(tipoServicoId) ? null : tipoServicoId, restoreLocalKey);
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível iniciar o serviço deste equipamento.', true);
    }
}

async function iniciarServicoDoEquipamento(equipamentoId, tipoServicoId = null, restoreLocalKey = '') {
    await selecionarEquipamento(equipamentoId, {
        autoAbrirChecklist: true,
        tipoServicoId,
        restoreLocalKey,
    });
}

function renderizarTabela(servicosList) {
    const tbody = document.getElementById('servicosTableBody');
    const noResults = document.getElementById('noResults');

    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    const canManage = canManageSystem();
    tbody.innerHTML = servicosList.map((servico) => {
        const pontuacao = Number(servico.pontuacao_percentual || 0);
        const pontuacaoClass = getPontuacaoClass(pontuacao);

        return `
            <tr onclick="verDetalhes(${servico.id})">
                <td class="data-cell">${escapeHtml(servico.data_realizacao)}</td>
                <td class="servico-equipamento">
                    <span class="service-avatar"><i class="fa-solid fa-fire-extinguisher"></i></span>
                    <div>
                        <strong>${escapeHtml(servico.equipamento_nome)}</strong>
                        <span>${escapeHtml(servico.equipamento_numero_serie || 'Sem número de série')}</span>
                    </div>
                </td>
                <td>${escapeHtml(servico.tipo_servico_nome || '-')}</td>
                <td>
                    <div class="checklist-progress">
                        <strong>${servico.total_itens ? `${servico.itens_realizados}/${servico.total_itens}` : '-'}</strong>
                        <div class="pontuacao-bar"><div class="pontuacao-fill ${pontuacaoClass}" style="width: ${pontuacao}%"></div></div>
                    </div>
                </td>
                <td>${escapeHtml(servico.local || '-')}</td>
                <td>${escapeHtml(servico.realizado_por_nome || '-')}</td>
                <td>
                    <span class="badge ${getStatusClass(servico.status)}">
                        ${escapeHtml(servico.status_display || servico.status || '-')}
                    </span>
                </td>
                <td><span class="badge ${pontuacaoClass}">${pontuacao}%</span></td>
                <td class="actions" onclick="event.stopPropagation()">
                    <button type="button" class="btn-icon" onclick="verDetalhes(${servico.id})" title="Ver detalhes">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                    ${canManage ? `
                    <button type="button" class="btn-icon btn-report" onclick="exportarRelatorioEquipamento(${servico.equipamento_id})" title="Relatório deste equipamento">
                        <i class="fa-solid fa-file-pdf"></i>
                    </button>
                    ` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

function exportarRelatorioEquipamento(equipamentoId) {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar serviços, mas não exportar relatórios.', true);
        return;
    }

    if (!equipamentoId) {
        mostrarToast('Equipamento não encontrado para gerar o relatório.', true);
        return;
    }

    window.location.href = API_URLS.exportarRelatorio(equipamentoId);
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchServico');
    const clearBtn = document.getElementById('clearSearch');
    const filtroSite = document.getElementById('filtroSite');
    const filtroStatus = document.getElementById('filtroStatus');
    const dataInicioInput = document.getElementById('filtroDataInicio');
    const dataFimInput = document.getElementById('filtroDataFim');
    const limparBtn = document.getElementById('limparFiltros');
    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const checklistForm = document.getElementById('checklistForm');
    const acaoForm = document.getElementById('acaoForm');
    const searchEquipamento = document.getElementById('searchEquipamentoSelect');
    const filtroGrupo = document.getElementById('filtroGrupoEquipamento');
    let debounceTimer;
    let debounceEquipamento;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarServicos();
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
            carregarServicos();
        });
    }

    if (filtroSite) {
        filtroSite.addEventListener('change', () => {
            siteFiltro = filtroSite.value;
            currentPage = 1;
            carregarServicos();
        });
    }

    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarServicos();
        });
    }

    if (dataInicioInput) {
        dataInicioInput.addEventListener('change', () => {
            dataInicio = dataInicioInput.value;
            currentPage = 1;
            carregarServicos();
        });
    }

    if (dataFimInput) {
        dataFimInput.addEventListener('change', () => {
            dataFim = dataFimInput.value;
            currentPage = 1;
            carregarServicos();
        });
    }

    if (limparBtn) {
        limparBtn.addEventListener('click', () => {
            setValue('filtroSite', '');
            setValue('filtroStatus', '');
            setValue('filtroDataInicio', '');
            setValue('filtroDataFim', '');
            siteFiltro = '';
            statusFiltro = '';
            dataInicio = '';
            dataFim = '';
            currentPage = 1;
            carregarServicos();
        });
    }

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10);
            currentPage = 1;
            carregarServicos();
        });
    }

    document.querySelectorAll('.close').forEach((btn) => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            if (!modal) return;
            if (modal.id === 'checklistModal') cancelarChecklist();
            else closeModal(modal.id);
        });
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target !== modal) return;
            if (modal.id === 'checklistModal') cancelarChecklist();
            else closeModal(modal.id);
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modaisAbertos = [...document.querySelectorAll('.modal.open')];
            const modal = modaisAbertos[modaisAbertos.length - 1];
            if (!modal) return;
            if (modal.id === 'checklistModal') cancelarChecklist();
            else closeModal(modal.id);
        }
    });

    if (checklistForm) {
        checklistForm.addEventListener('submit', (event) => {
            event.preventDefault();
            concluirServico();
        });
    }

    if (acaoForm) {
        acaoForm.addEventListener('submit', (event) => {
            event.preventDefault();
            salvarAcao();
        });
    }

    if (searchEquipamento) {
        searchEquipamento.addEventListener('input', (event) => {
            clearTimeout(debounceEquipamento);
            debounceEquipamento = setTimeout(() => {
                equipamentosSearch = event.target.value.trim();
                equipamentosPage = 1;
                carregarEquipamentosParaSelect();
            }, 280);
        });
    }

    if (filtroGrupo) {
        filtroGrupo.addEventListener('change', () => {
            equipamentosGrupoFiltro = filtroGrupo.value;
            equipamentosPage = 1;
            carregarEquipamentosParaSelect();
        });
    }
}

async function abrirModalSelecionarEquipamento() {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar serviços, mas não criar novos registros.', true);
        return;
    }

    try {
        rascunhoId = null;
        servicoAtual = null;
        await carregarGruposParaFiltro();
        equipamentosPage = 1;
        equipamentosSearch = '';
        equipamentosGrupoFiltro = '';
        setValue('searchEquipamentoSelect', '');
        setValue('filtroGrupoEquipamento', '');
        await carregarEquipamentosParaSelect();
        openModal('selecionarEquipamentoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao abrir seleção de equipamentos.', true);
    }
}

async function carregarGruposParaFiltro() {
    const data = await fetchJson(API_URLS.grupos);
    const select = document.getElementById('filtroGrupoEquipamento');
    if (!select) return;

    select.innerHTML = '<option value="">Todos os grupos</option>';
    (data.data || []).forEach((grupo) => {
        const option = document.createElement('option');
        option.value = grupo.id;
        option.textContent = grupo.nome;
        select.appendChild(option);
    });
}

async function carregarEquipamentosParaSelect() {
    const container = document.getElementById('equipamentosList');
    if (!container) return;

    container.innerHTML = '<div class="loading compact"><i class="fa-solid fa-spinner fa-spin"></i><p>Carregando equipamentos...</p></div>';

    try {
        const params = new URLSearchParams({
            page: equipamentosPage,
            rows: equipamentosRows,
        });

        if (equipamentosSearch) params.set('search', equipamentosSearch);
        if (equipamentosGrupoFiltro) params.set('grupo_id', equipamentosGrupoFiltro);

        const data = await fetchJson(`${API_URLS.listarEquipamentos}?${params.toString()}`);
        equipamentosTotal = data.total || 0;
        renderizarListaEquipamentos(data.data || []);
        renderizarPaginacaoEquipamentos();
    } catch (error) {
        container.innerHTML = `<div class="no-results compact"><i class="fa-solid fa-triangle-exclamation"></i><p>${escapeHtml(error.message || 'Erro ao carregar equipamentos')}</p></div>`;
    }
}

function renderizarListaEquipamentos(equipamentos) {
    const container = document.getElementById('equipamentosList');
    if (!container) return;

    if (!equipamentos.length) {
        container.innerHTML = '<div class="no-results compact"><i class="fa-solid fa-folder-open"></i><p>Nenhum equipamento encontrado</p></div>';
        return;
    }

    container.innerHTML = equipamentos.map((equip) => `
        <div class="equipamento-card" onclick="selecionarEquipamento(${equip.id})">
            <span class="service-avatar"><i class="fa-solid fa-fire-extinguisher"></i></span>
            <div class="equipamento-info">
                <div class="equipamento-nome">${escapeHtml(equip.nome)}</div>
                <div class="equipamento-detalhes">
                    ${equip.grupo_nome ? `<span><i class="fa-solid fa-layer-group"></i> ${escapeHtml(equip.grupo_nome)}</span>` : ''}
                    ${equip.local ? `<span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(equip.local)}</span>` : ''}
                </div>
                ${renderizarVencimentosEquipamento(equip)}
            </div>
            <button type="button" class="btn-select" onclick="event.stopPropagation(); selecionarEquipamento(${equip.id})">
                Selecionar <i class="fa-solid fa-arrow-right"></i>
            </button>
        </div>
    `).join('');
}

function renderizarPaginacaoEquipamentos() {
    const totalPages = Math.ceil(equipamentosTotal / equipamentosRows);
    const paginationDiv = document.getElementById('paginationEquipamentos');

    if (!paginationDiv) return;
    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }

    paginationDiv.innerHTML = `
        <button class="page-btn" onclick="mudarPaginaEquipamentos(1)" ${equipamentosPage === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-left"></i>
        </button>
        <button class="page-btn" onclick="mudarPaginaEquipamentos(${equipamentosPage - 1})" ${equipamentosPage === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-left"></i>
        </button>
        <span class="page-info">Página ${equipamentosPage} de ${totalPages}</span>
        <button class="page-btn" onclick="mudarPaginaEquipamentos(${equipamentosPage + 1})" ${equipamentosPage === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-right"></i>
        </button>
        <button class="page-btn" onclick="mudarPaginaEquipamentos(${totalPages})" ${equipamentosPage === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-right"></i>
        </button>
    `;
}

function mudarPaginaEquipamentos(page) {
    equipamentosPage = page;
    carregarEquipamentosParaSelect();
}

async function selecionarEquipamento(id, options = {}) {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar serviços, mas não criar novos registros.', true);
        return;
    }

    try {
        const data = await fetchJson(`/api/equipamentos/${id}/`);
        equipamentoSelecionado = data.data;

        const rascunhoParams = new URLSearchParams({ equipamento_id: id });
        if (options.tipoServicoId) rascunhoParams.set('tipo_servico_id', options.tipoServicoId);

        const rascunhoData = await fetchJson(`${API_URLS.rascunho}?${rascunhoParams.toString()}`);

        if (rascunhoData.has_rascunho) {
            rascunhoId = rascunhoData.rascunho_id;
            const progresso = Math.max(0, Math.min(Number(rascunhoData.progresso || 0), 100));
            setHtml('rascunhoInfo', `
                <div class="rascunho-card-head">
                    <span class="service-avatar"><i class="fa-solid fa-file-pen"></i></span>
                    <div>
                        <strong>${escapeHtml(equipamentoSelecionado.nome)}</strong>
                        <small>${escapeHtml(rascunhoData.tipo_servico_nome || 'Serviço em andamento')}</small>
                    </div>
                </div>
                <div class="rascunho-card-meta">
                    <span><i class="fa-solid fa-clock"></i> Iniciado em ${escapeHtml(rascunhoData.data_inicio)}</span>
                    <span><i class="fa-solid fa-list-check"></i> ${rascunhoData.total_respostas || 0}/${rascunhoData.total_itens || 0} respostas</span>
                </div>
                <div class="rascunho-progress">
                    <div><span style="width:${progresso}%"></span></div>
                    <strong>${progresso}%</strong>
                </div>
            `);
            closeModal('selecionarEquipamentoModal');
            if (options.autoAbrirChecklist || options.tipoServicoId) {
                await carregarRascunho(rascunhoId);
                return;
            }
            openModal('rascunhoModal');
            return;
        }

        closeModal('selecionarEquipamentoModal');
        rascunhoId = null;
        await carregarTiposServico(options);
    } catch (error) {
        mostrarToast(error.message || 'Erro ao selecionar equipamento.', true);
    }
}

function continuarRascunho() {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar rascunhos, mas não retomar checklists.', true);
        return;
    }

    fecharModalRascunho();
    carregarRascunho(rascunhoId);
}

async function descartarRascunho() {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar rascunhos, mas não descartar registros.', true);
        return;
    }

    if (!rascunhoId) return;

    try {
        await fetchJson(API_URLS.descartar(rascunhoId), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        mostrarToast('Rascunho descartado com sucesso!');
        fecharModalRascunho();
        limparCacheLocalAtual();
        carregarTiposServico();
    } catch (error) {
        mostrarToast(error.message || 'Erro ao descartar rascunho.', true);
    }
}

async function carregarTiposServico(options = {}) {
    try {
        const data = await fetchJson(`${API_URLS.listarTiposServico}?equipamento_id=${equipamentoSelecionado.id}`);
        const tipos = data.data || [];

        setHtml('equipamentoInfo', `
            <h3><i class="fa-solid fa-fire-extinguisher"></i> ${escapeHtml(equipamentoSelecionado.nome)}</h3>
            <p><i class="fa-solid fa-barcode"></i> S/N: ${escapeHtml(equipamentoSelecionado.numero_serie || 'N/A')}</p>
            <p><i class="fa-solid fa-location-dot"></i> Local: ${escapeHtml(equipamentoSelecionado.local || 'N/A')}</p>
            ${renderizarVencimentosEquipamentoSelecionado()}
        `);

        const container = document.getElementById('tiposServicoList');
        if (!container) return;

        if (!tipos.length) {
            container.innerHTML = '<div class="no-results compact"><i class="fa-solid fa-folder-open"></i><p>Nenhum tipo de serviço configurado para este equipamento.</p></div>';
        } else {
            const tipoServicoId = parseInt(options.tipoServicoId, 10);
            const tipoPreferido = tipos.find((tipo) => tipo.id === tipoServicoId);

            if (tipoPreferido || (options.autoAbrirChecklist && tipos.length === 1)) {
                const tipo = tipoPreferido || tipos[0];
                tipoServicoSelecionado = { id: tipo.id };
                await carregarChecklist({ restoreLocalKey: options.restoreLocalKey || '' });
                return;
            }

            container.innerHTML = tipos.map((tipo) => `
                <div class="tipo-servico-card" onclick="selecionarTipoServico(${tipo.id})">
                    <div class="tipo-servico-nome">${escapeHtml(tipo.nome)}</div>
                    <div class="tipo-servico-descricao">${escapeHtml(tipo.descricao || 'Serviço configurado')}</div>
                    <div class="tipo-servico-meta">
                        <span><i class="fa-solid fa-clock"></i> ${escapeHtml(tipo.periodicidade_nome || '-')}</span>
                        ${tipo.obrigatorio ? '<span><i class="fa-solid fa-lock"></i> Obrigatório</span>' : ''}
                    </div>
                </div>
            `).join('');

            if (tipoServicoId && !tipoPreferido) {
                mostrarToast('O tipo de serviço solicitado não está configurado para este equipamento.', true);
            }
        }

        openModal('selecionarTipoServicoModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar tipos de serviço.', true);
    }
}

async function selecionarTipoServico(id) {
    tipoServicoSelecionado = { id };
    rascunhoId = null;
    closeModal('selecionarTipoServicoModal');
    await carregarChecklist();
}

async function carregarRascunho(id) {
    try {
        const data = await fetchJson(API_URLS.detalhes(id));
        servicoAtual = data.data;
        rascunhoId = servicoAtual.id;

        const equipamentoData = await fetchJson(`/api/equipamentos/${servicoAtual.equipamento_id}/`);
        equipamentoSelecionado = equipamentoData.data;

        if (!servicoAtual.tipo_servico_id) {
            tipoServicoSelecionado = null;
            await carregarTiposServico();
            mostrarToast('Selecione o tipo de serviço para continuar este rascunho.', true);
            return;
        }

        

        tipoServicoSelecionado = { id: servicoAtual.tipo_servico_id };

        await carregarChecklist({ draft: servicoAtual, origem: 'server' });
        mostrarToast('Rascunho recuperado.');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar rascunho.', true);
    }
}

async function carregarChecklist(options = {}) {
    try {
        const data = await fetchJson(`/api/checklist-itens-por-tipo/?tipo_equipamento_id=${equipamentoSelecionado.tipo_equipamento_id}&tipo_servico_id=${tipoServicoSelecionado.id}`);

        setHtml('checklistInfo', `
            <div class="equipamento-info-card">
                <h3>${escapeHtml(equipamentoSelecionado.nome)}</h3>
                <p>Serviço: ${escapeHtml(data.tipo_servico_nome || 'Checklist')}</p>
                <p>Total de itens: ${(data.itens || data.data || []).length}</p>
                ${renderizarVencimentosEquipamentoSelecionado()}
            </div>
        `);

        renderizarChecklistItens(data.itens || data.data || []);
        setValue('equipamentoId', equipamentoSelecionado.id);
        setValue('tipoServicoId', tipoServicoSelecionado.id);
        setValue('observacoesServico', '');
        aplicarRascunhoNoChecklist(options.draft || carregarCacheLocal(options.restoreLocalKey || ''));
        configurarAutosaveChecklist();
        await garantirRascunhoInicial();
        openModal('checklistModal');

        if (options.draft?.origem === 'local' || options.origem === 'local') {
            mostrarToast('Rascunho local recuperado.');
        }
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar checklist.', true);
    }
}

function renderizarVencimentosEquipamentoSelecionado() {
    return renderizarVencimentosEquipamento(equipamentoSelecionado);
}

function renderizarVencimentosEquipamento(equipamento) {
    if (!equipamento || !equipamento.possui_vencimento) {
        return '';
    }

    if (equipamento.is_extintor) {
        return `
            <div class="equipamento-vencimentos-mini">
                <span><i class="fa-solid fa-calendar-check"></i> Carga: ${escapeHtml(equipamento.vencimento_carga_formatado || equipamento.vencimento_carga || '-')}</span>
                <span><i class="fa-solid fa-gauge-high"></i> Teste hidrostático: ${escapeHtml(equipamento.vencimento_teste_hidrostatico_formatado || equipamento.vencimento_teste_hidrostatico || '-')}</span>
            </div>
        `;
    }

    return `
        <div class="equipamento-vencimentos-mini">
            <span><i class="fa-solid fa-calendar-check"></i> Vencimento: ${escapeHtml(equipamento.data_vencimento_formatada || equipamento.data_vencimento || '-')}</span>
        </div>
    `;
}

function renderizarChecklistItens(itens) {
    const container = document.getElementById('checklistItems');
    if (!container) return;

    if (!itens.length) {
        container.innerHTML = '<div class="no-results compact"><i class="fa-solid fa-list-check"></i><p>Nenhum item de checklist configurado.</p></div>';
        return;
    }

    container.innerHTML = itens.map((item, index) => `
        <div class="checklist-item" data-item-id="${item.id}">
            <div class="checklist-question">
                <span>${index + 1}</span>
                <strong>${escapeHtml(item.pergunta)}</strong>
            </div>
            <div class="checklist-options">
                <label><input type="radio" name="item_${item.id}" value="atende" data-item-id="${item.id}"> Atende</label>
                <label><input type="radio" name="item_${item.id}" value="nao_atende" data-item-id="${item.id}"> Não atende</label>
                <label><input type="radio" name="item_${item.id}" value="nao_aplica" data-item-id="${item.id}"> Não se aplica</label>
            </div>
            <div class="checklist-observacao" style="display: none;">
                <textarea class="form-control" rows="2" placeholder="Observações sobre este item..." data-obs-id="${item.id}"></textarea>
            </div>
            <button type="button" class="btn-acao" onclick="abrirModalAcao(${item.id}, '${escapeAttribute(item.pergunta)}')">
                <i class="fa-solid fa-tools"></i> Adicionar ação
            </button>
        </div>
    `).join('');

    document.querySelectorAll('.checklist-options input[type="radio"]').forEach((radio) => {
        radio.addEventListener('change', function () {
            const itemDiv = this.closest('.checklist-item');
            const obsDiv = itemDiv.querySelector('.checklist-observacao');
            if (obsDiv) obsDiv.style.display = this.value === 'nao_atende' ? 'block' : 'none';
            registrarAlteracaoChecklist();
        });
    });

    document.querySelectorAll('#checklistItems textarea').forEach((textarea) => {
        textarea.addEventListener('input', registrarAlteracaoChecklist);
    });
}

async function cancelarChecklist() {
    if (!canManageSystem()) return;

    await enviarServico('rascunho', { force: true, silent: true });
    fecharModalChecklist();
    carregarServicos();
}

async function concluirServico() {
    if (!canManageSystem()) return;

    await enviarServico('concluido');
}

async function enviarServico(status, options = {}) {
    if (!canManageSystem()) {
        if (!options.silent) {
            mostrarToast('Seu perfil permite visualizar serviços, mas não salvar alterações.', true);
        }
        return;
    }

    if (!equipamentoSelecionado || !tipoServicoSelecionado) {
        mostrarToast('Selecione o equipamento e o tipo de serviço.', true);
        return;
    }

    const data = {
        equipamento_id: equipamentoSelecionado.id,
        tipo_servico_id: tipoServicoSelecionado.id,
        rascunho_id: rascunhoId,
        respostas: coletarRespostas(),
        observacoes: document.getElementById('observacoesServico')?.value || '',
        status,
    };

    if (status === 'rascunho' && !options.force && !temConteudoRascunho(data)) {
        return;
    }

    try {
        const result = await fetchJson(API_URLS.criar, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(data),
        });

        if (result.servico_id) rascunhoId = result.servico_id;

        if (status === 'rascunho') {
            ultimoRascunhoAssinado = assinaturaRascunhoAtual();
            limparCacheLocalAtual();
            atualizarStatusAutosave('Rascunho salvo automaticamente.');
            if (!options.silent) mostrarToast(result.message || 'Rascunho salvo com sucesso!');
            if (options.closeOnSuccess) {
                fecharModalChecklist();
                carregarServicos();
            }
            return;
        }

        limparCacheLocalAtual();
        mostrarToast(result.message || 'Serviço concluído com sucesso!');
        fecharModalChecklist();
        carregarServicos();
    } catch (error) {
        if (status === 'rascunho' && options.silent) {
            atualizarStatusAutosave('Sem conexão. Mantido no cache local.');
            return;
        }
        mostrarToast(error.message || 'Erro ao salvar serviço.', true);
    }
}

function configurarAutosaveChecklist() {
    if (!canManageSystem()) return;

    const form = document.getElementById('checklistForm');
    const observacoes = document.getElementById('observacoesServico');
    if (!form) return;

    form.querySelectorAll('input, textarea').forEach((field) => {
        field.removeEventListener('input', registrarAlteracaoChecklist);
        field.removeEventListener('change', registrarAlteracaoChecklist);
        field.addEventListener('input', registrarAlteracaoChecklist);
        field.addEventListener('change', registrarAlteracaoChecklist);
    });

    if (observacoes) observacoes.addEventListener('input', registrarAlteracaoChecklist);

    ultimoRascunhoAssinado = assinaturaRascunhoAtual();
    atualizarStatusAutosave('Rascunho automático ativo.');
    salvarCacheLocalChecklist();
}

async function garantirRascunhoInicial() {
    if (!canManageSystem()) return;

    if (rascunhoId || !equipamentoSelecionado || !tipoServicoSelecionado) return;

    atualizarStatusAutosave('Criando rascunho automático...');
    await enviarServico('rascunho', { force: true, silent: true });
}

function registrarAlteracaoChecklist() {
    if (!canManageSystem()) return;

    salvarCacheLocalChecklist();
    atualizarStatusAutosave('Alterações no cache local. Salvando...');

    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
        const assinaturaAtual = assinaturaRascunhoAtual();
        if (assinaturaAtual && assinaturaAtual !== ultimoRascunhoAssinado) {
            enviarServico('rascunho', { silent: true });
        }
    }, 1600);
}

function temConteudoRascunho(data) {
    return (data.respostas || []).length > 0 || Boolean((data.observacoes || '').trim());
}

function assinaturaRascunhoAtual() {
    if (!equipamentoSelecionado || !tipoServicoSelecionado) return '';
    return JSON.stringify({
        equipamento_id: equipamentoSelecionado.id,
        tipo_servico_id: tipoServicoSelecionado.id,
        respostas: coletarRespostas(),
        observacoes: document.getElementById('observacoesServico')?.value || '',
    });
}

function montarCacheChecklist() {
    return {
        origem: 'local',
        rascunho_id: rascunhoId,
        equipamento_id: equipamentoSelecionado?.id,
        equipamento_nome: equipamentoSelecionado?.nome,
        tipo_servico_id: tipoServicoSelecionado?.id,
        tipo_servico_nome: document.querySelector('#checklistInfo .equipamento-info-card p')?.textContent?.replace('Serviço:', '').trim() || 'Checklist',
        observacoes: document.getElementById('observacoesServico')?.value || '',
        respostas: coletarRespostas(),
        total_itens: document.querySelectorAll('#checklistItems .checklist-item').length,
        atualizado_em: new Date().toISOString(),
    };
}

function montarPayloadRascunhoAtual() {
    if (!equipamentoSelecionado || !tipoServicoSelecionado) return null;

    return {
        equipamento_id: equipamentoSelecionado.id,
        tipo_servico_id: tipoServicoSelecionado.id,
        rascunho_id: rascunhoId,
        respostas: coletarRespostas(),
        observacoes: document.getElementById('observacoesServico')?.value || '',
        status: 'rascunho',
    };
}

function enviarRascunhoBeacon() {
    const payload = montarPayloadRascunhoAtual();
    if (!payload) return;

    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
        navigator.sendBeacon(API_URLS.criar, new Blob([body], { type: 'application/json' }));
        return;
    }

    fetch(API_URLS.criar, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
    }).catch(() => {});
}

function chaveCacheChecklist() {
    if (!equipamentoSelecionado || !tipoServicoSelecionado) return '';
    return `${DRAFT_CACHE_PREFIX}${equipamentoSelecionado.id}:${tipoServicoSelecionado.id}`;
}

function salvarCacheLocalChecklist() {
    const chave = chaveCacheChecklist();
    if (!chave) return;
    const cache = montarCacheChecklist();
    if (!temConteudoRascunho(cache)) return;
    localStorage.setItem(chave, JSON.stringify(cache));
}

function carregarCacheLocal(restoreLocalKey = '') {
    const chave = restoreLocalKey || chaveCacheChecklist();
    if (!chave) return null;

    try {
        return JSON.parse(localStorage.getItem(chave) || 'null');
    } catch {
        return null;
    }
}

function limparCacheLocalAtual() {
    const chave = chaveCacheChecklist();
    if (chave) localStorage.removeItem(chave);
}

function aplicarRascunhoNoChecklist(draft) {
    if (!draft) return;

    rascunhoId = draft.id || draft.rascunho_id || rascunhoId;
    setValue('observacoesServico', draft.observacoes || '');

    (draft.respostas || []).forEach((resposta) => {
        const itemId = resposta.item_id || resposta.item_checklist_id;
        const radio = document.querySelector(`input[name="item_${itemId}"][value="${resposta.opcao}"]`);
        if (radio) {
            radio.checked = true;
            const itemDiv = radio.closest('.checklist-item');
            const obsDiv = itemDiv?.querySelector('.checklist-observacao');
            const obsTextarea = itemDiv?.querySelector(`textarea[data-obs-id="${itemId}"]`);
            if (obsTextarea) obsTextarea.value = resposta.observacao || '';
            if (obsDiv) obsDiv.style.display = resposta.opcao === 'nao_atende' ? 'block' : 'none';
        }
    });
}

function atualizarStatusAutosave(message) {
    const status = document.getElementById('autosaveStatus');
    if (!status) return;
    status.textContent = message;
}

function coletarRespostas() {
    const respostas = [];

    document.querySelectorAll('.checklist-item').forEach((item) => {
        const itemId = item.getAttribute('data-item-id');
        const selectedRadio = item.querySelector('input[type="radio"]:checked');
        const observacao = item.querySelector('textarea')?.value || '';

        if (selectedRadio) {
            respostas.push({
                item_id: parseInt(itemId, 10),
                opcao: selectedRadio.value,
                observacao,
            });
        }
    });

    return respostas;
}

function abrirModalAcao(itemId, pergunta) {
    if (!canManageSystem()) {
        mostrarToast('Seu perfil permite visualizar serviços, mas não criar ações corretivas.', true);
        return;
    }

    acaoItemId = itemId;
    setHtml('acaoPergunta', `<strong>${escapeHtml(pergunta)}</strong>`);
    document.getElementById('acaoForm')?.reset();
    const feedback = document.getElementById('acaoFeedback');
    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }
    openModal('acaoModal');
}

async function salvarAcao() {
    if (!canManageSystem()) return;

    const problema = document.getElementById('problema')?.value.trim();
    const acao = document.getElementById('acao')?.value.trim();
    const responsaveis = document.getElementById('responsaveis')?.value.trim();
    const prazo = document.getElementById('prazo')?.value;
    const anexos = document.getElementById('anexos')?.files[0];

    if (!problema || !acao || !responsaveis || !prazo) {
        mostrarFeedbackAcao('Preencha todos os campos obrigatórios.');
        return;
    }

    const formData = new FormData();
    formData.append('servico_id', servicoAtual?.id || '');
    formData.append('item_checklist_id', acaoItemId);
    formData.append('problema', problema);
    formData.append('acao', acao);
    formData.append('responsaveis', responsaveis);
    formData.append('prazo', prazo);
    if (anexos) formData.append('anexos', anexos);

    try {
        const result = await fetchJson(API_URLS.acaoCriar, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
        });

        mostrarToast(result.message || 'Ação cadastrada com sucesso!');
        fecharModalAcao();
    } catch (error) {
        mostrarFeedbackAcao(error.message || 'Erro ao salvar ação.');
    }
}

async function verDetalhes(id) {
    try {
        const data = await fetchJson(API_URLS.detalhes(id));
        const servico = data.data;
        const pontuacao = Number(servico.pontuacao_percentual || 0);
        const respostasHtml = renderRespostasDetalhes(servico.respostas || []);

        setHtml('detalhesServico', `
            <div class="equipamento-info-card">
                <h3>${escapeHtml(servico.equipamento_nome)}</h3>
                <p><i class="fa-solid fa-barcode"></i> S/N: ${escapeHtml(servico.equipamento_numero_serie || 'N/A')}</p>
                <p><i class="fa-solid fa-tag"></i> Serviço: ${escapeHtml(servico.tipo_servico_nome || '-')}</p>
                <p><i class="fa-solid fa-calendar"></i> Data: ${escapeHtml(servico.data_realizacao)}</p>
                <p><i class="fa-solid fa-user"></i> Realizado por: ${escapeHtml(servico.realizado_por_nome || '-')}</p>
                <p><i class="fa-solid fa-chart-line"></i> Pontuação: <span class="badge ${getPontuacaoClass(pontuacao)}">${pontuacao}%</span></p>
                ${servico.observacoes ? `<p><i class="fa-solid fa-comment"></i> Observações: ${escapeHtml(servico.observacoes)}</p>` : ''}
            </div>
            ${respostasHtml}
        `);

        openModal('detalhesModal');
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar detalhes.', true);
    }
}

function renderRespostasDetalhes(respostas) {
    if (!respostas.length) return '<div class="no-results compact"><p>Sem respostas registradas.</p></div>';

    return `
        <div class="respostas-list">
            <h4>Respostas do Checklist</h4>
            ${respostas.map((resposta) => `
                <div class="resposta-item">
                    <strong>${escapeHtml(resposta.pergunta)}</strong>
                    <span class="badge ${getOpcaoClass(resposta.opcao)}">${escapeHtml(resposta.opcao_display || resposta.opcao)}</span>
                    ${resposta.observacao ? `<small>Obs: ${escapeHtml(resposta.observacao)}</small>` : ''}
                </div>
            `).join('')}
        </div>
    `;
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
        html += `<button class="page-btn ${page === currentPage ? 'page-active' : ''}" onclick="mudarPagina(${page})">${page}</button>`;
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
    carregarServicos();
}

function mostrarSemDados() {
    const tbody = document.getElementById('servicosTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum serviço encontrado</p>
            ${canManageSystem() ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="abrirModalSelecionarEquipamento()">
                <i class="fa-solid fa-plus"></i> Realizar serviço
            </button>
            ` : ''}
        `;
        noResults.style.display = 'block';
    }
}

function mostrarErro(mensagem) {
    const tbody = document.getElementById('servicosTableBody');
    const noResults = document.getElementById('noResults');

    if (tbody) tbody.innerHTML = '';
    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button type="button" class="btn btn-primary btn-sm" onclick="carregarServicos()">
                Tentar novamente
            </button>
        `;
        noResults.style.display = 'block';
    }
}

function mostrarLoading(show) {
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('servicosTableBody');
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

function atualizarResumo(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryConcluidos', data.total_concluidos || 0);
    setText('summaryRascunhos', data.total_rascunhos || 0);
    setText('summaryNaoConformes', data.total_nao_conformes || 0);
}

function fecharModalSelecionarEquipamento() {
    closeModal('selecionarEquipamentoModal');
}

function fecharModalChecklist() {
    clearTimeout(autosaveTimer);
    closeModal('checklistModal');
}

function fecharModalAcao() {
    closeModal('acaoModal');
    acaoItemId = null;
}

function fecharModalRascunho() {
    closeModal('rascunhoModal');
    rascunhoId = null;
}

function fecharModalDetalhes() {
    closeModal('detalhesModal');
}

function fecharTodosModais() {
    document.querySelectorAll('.modal.open').forEach((modal) => closeModal(modal.id));
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

function mostrarFeedbackAcao(message) {
    const feedback = document.getElementById('acaoFeedback');
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

function getPontuacaoClass(pontuacao) {
    if (pontuacao >= 80) return 'badge-success';
    if (pontuacao >= 50) return 'badge-warning';
    return 'badge-danger';
}

function getStatusClass(status) {
    if (status === 'concluido') return 'badge-success';
    if (status === 'rascunho') return 'badge-warning';
    if (status === 'cancelado') return 'badge-danger';
    return 'badge-info';
}

function getOpcaoClass(opcao) {
    if (opcao === 'atende') return 'badge-success';
    if (opcao === 'nao_atende') return 'badge-danger';
    return 'badge-info';
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

function setHtml(id, value) {
    const element = document.getElementById(id);
    if (element) element.innerHTML = value;
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
