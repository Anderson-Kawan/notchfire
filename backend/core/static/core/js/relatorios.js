const API_RELATORIOS = {
    filtros: '/api/relatorios/filtros/',
    resumo: '/api/relatorios/resumo/',
    historico: '/api/relatorios/historico/',
    exportar: '/relatorios/exportar/condensado/',
};

document.addEventListener('DOMContentLoaded', () => {
    configurarDatasPadrao();
    configurarEventos();
    carregarFiltros();
    carregarHistorico();
});

function configurarEventos() {
    const predio = document.getElementById('predioSelect');
    const tipoEquipamento = document.getElementById('tipoEquipamentoSelect');
    const tipoServico = document.getElementById('tipoServicoSelect');
    const equipamento = document.getElementById('equipamentoSelect');
    const form = document.getElementById('relatorioForm');
    const limpar = document.getElementById('limparRelatorio');
    const atualizarHistorico = document.getElementById('atualizarHistorico');

    predio?.addEventListener('change', async () => {
        setValue('tipoEquipamentoSelect', '');
        setValue('tipoServicoSelect', '');
        setValue('equipamentoSelect', '');
        await carregarFiltros();
        atualizarResumo();
    });

    tipoEquipamento?.addEventListener('change', async () => {
        setValue('tipoServicoSelect', '');
        setValue('equipamentoSelect', '');
        await carregarFiltros();
        atualizarResumo();
    });

    tipoServico?.addEventListener('change', atualizarResumo);
    equipamento?.addEventListener('change', atualizarResumo);
    document.getElementById('dataInicio')?.addEventListener('change', atualizarResumo);
    document.getElementById('dataFim')?.addEventListener('change', atualizarResumo);

    document.querySelectorAll('.clear-select').forEach((button) => {
        button.addEventListener('click', async () => {
            const target = button.dataset.target;
            setValue(target, '');

            if (target === 'predioSelect') {
                setValue('tipoEquipamentoSelect', '');
                setValue('tipoServicoSelect', '');
                setValue('equipamentoSelect', '');
            }

            if (target === 'tipoEquipamentoSelect') {
                setValue('tipoServicoSelect', '');
                setValue('equipamentoSelect', '');
            }

            await carregarFiltros();
            atualizarResumo();
        });
    });

    limpar?.addEventListener('click', async () => {
        setValue('predioSelect', '');
        setValue('tipoEquipamentoSelect', '');
        setValue('tipoServicoSelect', '');
        setValue('equipamentoSelect', '');
        configurarDatasPadrao();
        await carregarFiltros();
        limparResumo();
    });

    form?.addEventListener('submit', (event) => {
        event.preventDefault();
        exportarRelatorio();
    });

    atualizarHistorico?.addEventListener('click', carregarHistorico);
}

function configurarDatasPadrao() {
    const hoje = new Date();
    const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    setValue('dataInicio', formatDateInput(inicio));
    setValue('dataFim', formatDateInput(hoje));
}

async function carregarFiltros() {
    try {
        const params = new URLSearchParams();
        const predioId = getValue('predioSelect');
        const tipoEquipamentoId = getValue('tipoEquipamentoSelect');
        const equipamentoId = getValue('equipamentoSelect');

        if (predioId) params.set('predio_id', predioId);
        if (tipoEquipamentoId) params.set('tipo_equipamento_id', tipoEquipamentoId);

        const data = await fetchJson(`${API_RELATORIOS.filtros}?${params.toString()}`);
        preencherSelect('predioSelect', data.predios || [], 'Selecione um prédio...');
        preencherSelect('tipoEquipamentoSelect', data.tipos_equipamento || [], predioId ? 'Selecione o tipo...' : 'Selecione o prédio primeiro...');
        preencherSelect('tipoServicoSelect', data.tipos_servico || [], tipoEquipamentoId ? 'Selecione o serviço...' : 'Selecione o tipo de equipamento...');
        preencherSelect('equipamentoSelect', data.equipamentos || [], tipoEquipamentoId ? 'Todos os equipamentos do filtro...' : 'Selecione o tipo de equipamento...');

        setValue('predioSelect', predioId);
        setValue('tipoEquipamentoSelect', tipoEquipamentoId);
        setValue('equipamentoSelect', equipamentoId);

        document.getElementById('tipoEquipamentoSelect').disabled = !predioId;
        document.getElementById('tipoServicoSelect').disabled = !tipoEquipamentoId;
        document.getElementById('equipamentoSelect').disabled = !tipoEquipamentoId;
    } catch (error) {
        mostrarToast(error.message || 'Erro ao carregar filtros.', true);
    }
}

function preencherSelect(id, itens, placeholder) {
    const select = document.getElementById(id);
    if (!select) return;

    const selected = select.value;
    select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>`;

    itens.forEach((item) => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = item.periodicidade ? `${item.nome} · ${item.periodicidade}` : item.nome;
        select.appendChild(option);
    });

    if ([...select.options].some((option) => option.value === selected)) {
        select.value = selected;
    }
}

async function atualizarResumo() {
    if (!filtrosObrigatoriosPreenchidos(false)) {
        limparResumo();
        return;
    }

    try {
        const data = await fetchJson(`${API_RELATORIOS.resumo}?${montarParams().toString()}`);
        setText('summaryServicos', data.total_servicos || 0);
        setText('summaryEquipamentos', data.total_equipamentos || 0);
        setText('summaryNaoConformes', data.total_nao_conformes || 0);
        setText('summaryPontuacao', `${data.media_pontuacao || 0}%`);
        renderizarRecentes(data.ultimos || []);
    } catch (error) {
        mostrarToast(error.message || 'Erro ao atualizar resumo.', true);
    }
}

function renderizarRecentes(itens) {
    const container = document.getElementById('recentResults');
    if (!container) return;

    if (!itens.length) {
        container.innerHTML = `
            <div class="recent-empty">
                <span><i class="fa-solid fa-folder-open"></i> Nenhum serviço concluído encontrado para estes filtros.</span>
            </div>
        `;
        return;
    }

    container.innerHTML = itens.map((item) => `
        <div class="recent-item">
            <div>
                <strong>${escapeHtml(item.equipamento)}</strong>
                <small>${escapeHtml(item.tipo_servico)} · ${escapeHtml(item.data)}</small>
            </div>
            <span class="recent-score">${Number(item.pontuacao || 0).toFixed(0)}%</span>
        </div>
    `).join('');
}

function exportarRelatorio() {
    if (!filtrosObrigatoriosPreenchidos(true)) return;
    window.location.href = `${API_RELATORIOS.exportar}?${montarParams().toString()}`;
    setTimeout(carregarHistorico, 1200);
}

async function carregarHistorico() {
    const container = document.getElementById('historicoRelatorios');
    if (!container) return;

    container.innerHTML = `
        <div class="recent-empty">
            <span><i class="fa-solid fa-spinner fa-spin"></i> Carregando relatórios...</span>
        </div>
    `;

    try {
        const data = await fetchJson(API_RELATORIOS.historico);
        renderizarHistorico(data.data || []);
    } catch (error) {
        container.innerHTML = `
            <div class="recent-empty">
                <span><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(error.message || 'Erro ao carregar histórico.')}</span>
            </div>
        `;
    }
}

function renderizarHistorico(relatorios) {
    const container = document.getElementById('historicoRelatorios');
    if (!container) return;

    if (!relatorios.length) {
        container.innerHTML = `
            <div class="recent-empty">
                <span><i class="fa-solid fa-folder-open"></i> Nenhum relatório gerado ainda.</span>
            </div>
        `;
        return;
    }

    container.innerHTML = relatorios.map((relatorio) => `
        <article class="history-item">
            <span class="history-icon"><i class="fa-solid fa-file-pdf"></i></span>
            <div class="history-info">
                <strong>${escapeHtml(relatorio.tipo)}</strong>
                <span>${escapeHtml(relatorio.predio)} · ${escapeHtml(relatorio.tipo_equipamento)} · ${escapeHtml(relatorio.equipamento)} · ${escapeHtml(relatorio.tipo_servico)}</span>
                <small>${escapeHtml(relatorio.periodo)} · ${escapeHtml(relatorio.criado_em)} · ${relatorio.total_servicos} serviços · ${Number(relatorio.media_pontuacao || 0).toFixed(1)}%</small>
            </div>
            <a href="/relatorios/${relatorio.id}/baixar/" class="btn btn-outline btn-sm">
                <i class="fa-solid fa-download"></i> Baixar
            </a>
        </article>
    `).join('');
}

function filtrosObrigatoriosPreenchidos(showToast) {
    const required = [
        ['predioSelect', 'Selecione o prédio.'],
        ['tipoEquipamentoSelect', 'Selecione o tipo de equipamento.'],
        ['tipoServicoSelect', 'Selecione o tipo de serviço.'],
        ['dataInicio', 'Informe a data inicial.'],
        ['dataFim', 'Informe a data final.'],
    ];

    for (const [id, message] of required) {
        if (!getValue(id)) {
            if (showToast) mostrarToast(message, true);
            return false;
        }
    }

    if (getValue('dataInicio') > getValue('dataFim')) {
        if (showToast) mostrarToast('A data inicial não pode ser maior que a data final.', true);
        return false;
    }

    return true;
}

function montarParams() {
    return new URLSearchParams({
        predio_id: getValue('predioSelect'),
        tipo_equipamento_id: getValue('tipoEquipamentoSelect'),
        tipo_servico_id: getValue('tipoServicoSelect'),
        equipamento_id: getValue('equipamentoSelect'),
        data_inicio: getValue('dataInicio'),
        data_fim: getValue('dataFim'),
    });
}

function limparResumo() {
    setText('summaryServicos', '0');
    setText('summaryEquipamentos', '0');
    setText('summaryNaoConformes', '0');
    setText('summaryPontuacao', '0%');
    const container = document.getElementById('recentResults');
    if (container) container.innerHTML = '';
}

async function fetchJson(url) {
    const response = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok || data.success === false) {
        throw new Error(data.error || 'Não foi possível concluir a ação.');
    }

    return data;
}

function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
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

function getValue(id) {
    return document.getElementById(id)?.value || '';
}

function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.value = value || '';
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}
