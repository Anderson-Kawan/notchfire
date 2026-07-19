const API_CALENDARIO = {
    filtros: '/api/calendario/filtros/',
    eventos: '/api/calendario/eventos/',
    exportar: '/calendario/exportar/',
};

const MONTHS = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];

let currentDate = new Date();
let currentEvents = [];
let currentSummary = {};
let filtersLoaded = false;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    configurarEventosCalendario();
    carregarFiltros();
    carregarEventos();
});

function configurarEventosCalendario() {
    document.getElementById('prevMonth')?.addEventListener('click', () => mudarMes(-1));
    document.getElementById('nextMonth')?.addEventListener('click', () => mudarMes(1));
    document.getElementById('todayMonth')?.addEventListener('click', () => {
        currentDate = new Date();
        carregarEventos();
    });

    document.getElementById('toggleFilters')?.addEventListener('click', () => {
        document.getElementById('filtersPanel')?.classList.toggle('open');
    });
    document.getElementById('closeFilters')?.addEventListener('click', () => {
        document.getElementById('filtersPanel')?.classList.remove('open');
    });

    document.getElementById('applyFilters')?.addEventListener('click', () => {
        carregarEventos();
        document.getElementById('filtersPanel')?.classList.remove('open');
    });

    document.getElementById('clearFilters')?.addEventListener('click', async () => {
        limparFiltros();
        await carregarFiltros();
        carregarEventos();
    });

    document.getElementById('exportCalendar')?.addEventListener('click', exportarCalendario);
    document.getElementById('closeDrawer')?.addEventListener('click', fecharDrawer);
    document.getElementById('eventDrawer')?.addEventListener('click', (event) => {
        if (event.target.id === 'eventDrawer') fecharDrawer();
    });

    [
        'filterPredio',
        'filterDepartamento',
        'filterGrupo',
        'filterTipoEquipamento',
        'filterTipoServico',
        'filterPeriodicidade',
        'filterResponsavel',
        'filterStatus',
        'filterAcoes',
    ].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', async () => {
            if (['filterPredio', 'filterGrupo', 'filterTipoEquipamento'].includes(id)) {
                await carregarFiltros();
            }
            atualizarChips();
        });
    });

    document.getElementById('filterBusca')?.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(atualizarChips, 180);
    });
}

function mudarMes(delta) {
    currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + delta, 1);
    carregarEventos();
}

async function carregarFiltros() {
    try {
        const params = montarParamsFiltros(false);
        const data = await fetchJson(`${API_CALENDARIO.filtros}?${params.toString()}`);

        preencherSelect('filterPredio', data.predios || [], 'Todos os sites');
        preencherSelect('filterDepartamento', data.departamentos || [], 'Todos os departamentos');
        preencherSelect('filterGrupo', data.grupos || [], 'Todos os grupos');
        preencherSelect('filterTipoEquipamento', data.tipos_equipamento || [], 'Todos os tipos');
        preencherSelect('filterTipoServico', data.tipos_servico || [], 'Todos os serviços');
        preencherSelect('filterPeriodicidade', data.periodicidades || [], 'Todas as periodicidades');
        preencherSelect('filterResponsavel', data.responsaveis || [], 'Todos os responsáveis');

        filtersLoaded = true;
        atualizarChips();
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível carregar os filtros.', true);
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
        option.textContent = item.nome;
        select.appendChild(option);
    });

    if ([...select.options].some((option) => option.value === selected)) {
        select.value = selected;
    }
}

async function carregarEventos() {
    renderizarLoading();
    atualizarTituloMes();

    try {
        if (!filtersLoaded) await carregarFiltros();

        const params = montarParamsFiltros(true);
        const data = await fetchJson(`${API_CALENDARIO.eventos}?${params.toString()}`);

        currentEvents = data.eventos || [];
        currentSummary = data.resumo || {};
        renderizarResumo();
        renderizarCalendario();
        renderizarDetalhesMes();
        atualizarChips();
    } catch (error) {
        mostrarErroCalendario(error.message || 'Não foi possível carregar o calendário.');
    }
}

function montarParamsFiltros(includeMonth) {
    const params = new URLSearchParams();
    const fields = {
        predio_id: 'filterPredio',
        departamento_id: 'filterDepartamento',
        grupo_id: 'filterGrupo',
        tipo_equipamento_id: 'filterTipoEquipamento',
        tipo_servico_id: 'filterTipoServico',
        periodicidade_id: 'filterPeriodicidade',
        responsavel_id: 'filterResponsavel',
        status: 'filterStatus',
        acoes: 'filterAcoes',
        busca: 'filterBusca',
    };

    Object.entries(fields).forEach(([param, id]) => {
        const value = getValue(id);
        if (value) params.set(param, value);
    });

    if (includeMonth) {
        params.set('ano', currentDate.getFullYear());
        params.set('mes', currentDate.getMonth() + 1);
    }

    return params;
}

function atualizarTituloMes() {
    setText('monthName', MONTHS[currentDate.getMonth()]);
    setText('monthYear', currentDate.getFullYear());
}

function renderizarLoading() {
    const grid = document.getElementById('calendarGrid');
    if (!grid) return;

    grid.innerHTML = `
        <div class="loading-cell">
            <i class="fa-solid fa-spinner fa-spin"></i>
            Carregando calendário...
        </div>
    `;
}

function renderizarResumo() {
    setText('summaryTotal', currentSummary.total || 0);
    setText('summaryPendentes', currentSummary.pendentes || 0);
    setText('summaryVencidas', currentSummary.vencidas || 0);
    setText('summaryRealizadas', currentSummary.realizadas || 0);
}

function renderizarCalendario() {
    const grid = document.getElementById('calendarGrid');
    if (!grid) return;

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const start = new Date(year, month, 1);
    const end = new Date(year, month + 1, 0);
    const startOffset = (start.getDay() + 6) % 7;
    const totalCells = Math.ceil((startOffset + end.getDate()) / 7) * 7;
    const firstCell = new Date(year, month, 1 - startOffset);
    const todayKey = formatDateInput(new Date());
    const eventsByDate = agruparEventosPorData(currentEvents);

    const cells = [];
    for (let index = 0; index < totalCells; index += 1) {
        const day = new Date(firstCell.getFullYear(), firstCell.getMonth(), firstCell.getDate() + index);
        const dateKey = formatDateInput(day);
        const events = eventsByDate[dateKey] || [];
        const visibleEvents = events.slice(0, 3);
        const classes = [
            'calendar-day',
            day.getMonth() !== month ? 'other-month' : '',
            dateKey === todayKey ? 'today' : '',
        ].filter(Boolean).join(' ');

        cells.push(`
            <div class="${classes}" data-date="${dateKey}">
                <div class="day-head">
                    <span class="day-number">${String(day.getDate()).padStart(2, '0')}</span>
                    ${events.length ? `<span class="day-count">${events.length}</span>` : ''}
                </div>
                <div class="day-events">
                    ${visibleEvents.map((event) => renderizarEvento(event)).join('')}
                    ${events.length > visibleEvents.length ? `
                        <button type="button" class="more-events" data-date="${dateKey}">
                            +${events.length - visibleEvents.length} revisões
                        </button>
                    ` : ''}
                </div>
            </div>
        `);
    }

    grid.innerHTML = cells.join('');

    grid.querySelectorAll('.calendar-event').forEach((button) => {
        button.addEventListener('click', () => abrirDrawer(button.dataset.date));
    });

    grid.querySelectorAll('.more-events').forEach((button) => {
        button.addEventListener('click', () => abrirDrawer(button.dataset.date));
    });
}

function renderizarEvento(evento) {
    return `
        <button type="button" class="calendar-event event-${escapeHtml(evento.status)}" data-date="${escapeHtml(evento.data_calendario)}">
            <span class="event-title">${escapeHtml(evento.equipamento_nome)}</span>
            <span class="event-meta">${escapeHtml(evento.tipo_servico_nome)} · ${escapeHtml(evento.status_label)}</span>
        </button>
    `;
}

function renderizarDetalhesMes() {
    const attention = currentEvents
        .filter((evento) => ['vencida', 'pendente'].includes(evento.status))
        .sort((a, b) => a.data_original.localeCompare(b.data_original))
        .slice(0, 8);

    const attentionList = document.getElementById('attentionList');
    if (attentionList) {
        if (!attention.length) {
            attentionList.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-circle-check"></i>
                    Nenhuma revisão pendente para os filtros selecionados.
                </div>
            `;
        } else {
            attentionList.innerHTML = attention.map((evento) => `
                <article class="attention-item">
                    <span class="attention-status ${escapeHtml(evento.status)}">
                        <i class="fa-solid ${evento.status === 'vencida' ? 'fa-triangle-exclamation' : 'fa-clock'}"></i>
                    </span>
                    <div class="attention-info">
                        <strong>${escapeHtml(evento.equipamento_nome)}</strong>
                        <span>${escapeHtml(evento.tipo_servico_nome)} · ${escapeHtml(evento.local || '-')} · ${escapeHtml(evento.periodicidade || '-')}</span>
                    </div>
                    <span class="attention-date">${formatDateDisplay(evento.data_original)}</span>
                </article>
            `).join('');
        }
    }

    const responsaveis = contarResponsaveis(currentEvents);
    const responsaveisList = document.getElementById('responsaveisList');
    if (!responsaveisList) return;

    if (!responsaveis.length) {
        responsaveisList.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-user-check"></i>
                Nenhuma revisão realizada neste mês.
            </div>
        `;
        return;
    }

    responsaveisList.innerHTML = responsaveis.map((item) => `
        <article class="person-item">
            <div class="person-info">
                <strong>${escapeHtml(item.nome)}</strong>
                <span>${item.servicos.map((servico) => escapeHtml(servico)).join(' · ')}</span>
            </div>
            <span class="person-count">${item.total}</span>
        </article>
    `).join('');
}

function abrirDrawer(dateKey) {
    const eventos = currentEvents
        .filter((evento) => evento.data_calendario === dateKey)
        .sort((a, b) => a.status.localeCompare(b.status));

    const drawer = document.getElementById('eventDrawer');
    const list = document.getElementById('drawerEvents');
    if (!drawer || !list) return;

    setText('drawerDate', formatDateDisplay(dateKey));
    setText('drawerTitle', `${eventos.length} ${eventos.length === 1 ? 'revisão' : 'revisões'}`);

    if (!eventos.length) {
        list.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-calendar-xmark"></i>
                Nenhuma revisão neste dia.
            </div>
        `;
    } else {
        list.innerHTML = eventos.map((evento) => `
            <article class="drawer-event event-${escapeHtml(evento.status)}">
                <div class="drawer-info">
                    <strong>${escapeHtml(evento.equipamento_nome)}</strong>
                    <span>${escapeHtml(evento.tipo_servico_nome)} · ${escapeHtml(evento.status_label)}</span>
                    <span>${escapeHtml(evento.local || '-')} · ${escapeHtml(evento.tipo_equipamento_nome || '-')}</span>
                    <span>${evento.realizado_por_nome ? `Inspecionado por ${escapeHtml(evento.realizado_por_nome)}` : `Vencimento ${formatDateDisplay(evento.data_original)}`}</span>
                </div>
                <div class="drawer-actions">
                    <a href="/equipamentos/${evento.equipamento_id}/">
                        <i class="fa-solid fa-fire-extinguisher"></i>
                        Ver equipamento
                    </a>
                    ${evento.servico_id ? `
                        <a href="/servicos/?equipamento_id=${evento.equipamento_id}">
                            <i class="fa-solid fa-list-check"></i>
                            Ver serviços
                        </a>
                    ` : ''}
                </div>
            </article>
        `).join('');
    }

    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
}

function fecharDrawer() {
    const drawer = document.getElementById('eventDrawer');
    if (!drawer) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
}

function agruparEventosPorData(eventos) {
    return eventos.reduce((acc, evento) => {
        if (!acc[evento.data_calendario]) acc[evento.data_calendario] = [];
        acc[evento.data_calendario].push(evento);
        return acc;
    }, {});
}

function contarResponsaveis(eventos) {
    const mapa = new Map();
    eventos
        .filter((evento) => evento.status === 'realizada' && evento.realizado_por_nome)
        .forEach((evento) => {
            const nome = evento.realizado_por_nome;
            if (!mapa.has(nome)) {
                mapa.set(nome, { nome, total: 0, servicos: new Set() });
            }
            const item = mapa.get(nome);
            item.total += 1;
            item.servicos.add(evento.tipo_servico_nome);
        });

    return [...mapa.values()]
        .map((item) => ({ ...item, servicos: [...item.servicos].slice(0, 3) }))
        .sort((a, b) => b.total - a.total);
}

function atualizarChips() {
    const chips = document.getElementById('activeChips');
    const counter = document.getElementById('activeFiltersCount');
    if (!chips) return;

    const fields = [
        ['filterPredio', 'Site'],
        ['filterDepartamento', 'Departamento'],
        ['filterGrupo', 'Grupo'],
        ['filterTipoEquipamento', 'Tipo'],
        ['filterTipoServico', 'Serviço'],
        ['filterPeriodicidade', 'Periodicidade'],
        ['filterResponsavel', 'Responsável'],
        ['filterStatus', 'Status'],
        ['filterAcoes', 'Ações'],
        ['filterBusca', 'Busca'],
    ];

    const active = fields
        .map(([id, label]) => {
            const value = getValue(id);
            if (!value) return null;
            const element = document.getElementById(id);
            const text = element?.tagName === 'SELECT'
                ? element.options[element.selectedIndex]?.textContent
                : value;
            return { id, label, text };
        })
        .filter(Boolean);

    chips.innerHTML = active.length ? active.map((item) => `
        <span class="filter-chip">
            ${escapeHtml(item.label)}: ${escapeHtml(item.text)}
            <button type="button" data-clear="${escapeHtml(item.id)}" title="Remover filtro">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </span>
    `).join('') : '<span class="filter-empty">Nenhum filtro aplicado.</span>';

    chips.querySelectorAll('[data-clear]').forEach((button) => {
        button.addEventListener('click', async () => {
            setValue(button.dataset.clear, '');
            await carregarFiltros();
            carregarEventos();
        });
    });

    if (counter) counter.textContent = active.length;
}

function limparFiltros() {
    [
        'filterPredio',
        'filterDepartamento',
        'filterGrupo',
        'filterTipoEquipamento',
        'filterTipoServico',
        'filterPeriodicidade',
        'filterResponsavel',
        'filterStatus',
        'filterAcoes',
        'filterBusca',
    ].forEach((id) => setValue(id, ''));
    atualizarChips();
}

function exportarCalendario() {
    if (window.NOTCHFIRE_CAN_MANAGE !== true) {
        mostrarToast('Seu perfil permite visualizar o calendário, mas não exportar dados.', true);
        return;
    }

    const params = montarParamsFiltros(true);
    window.location.href = `${API_CALENDARIO.exportar}?${params.toString()}`;
}

function mostrarErroCalendario(message) {
    const grid = document.getElementById('calendarGrid');
    if (!grid) return;
    grid.innerHTML = `
        <div class="loading-cell">
            <i class="fa-solid fa-triangle-exclamation"></i>
            ${escapeHtml(message)}
        </div>
    `;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok || data.success === false) {
        throw new Error(data.error || 'Erro na comunicação com o servidor.');
    }
    return data;
}

function getValue(id) {
    return document.getElementById(id)?.value?.trim() || '';
}

function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.value = value;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatDateDisplay(value) {
    if (!value) return '-';
    const [year, month, day] = value.split('-');
    return `${day}/${month}/${year}`;
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
}

function mostrarToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        right: 22px;
        bottom: 22px;
        background: ${isError ? '#c24135' : '#1a3a5a'};
        color: #fff;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 14px 28px rgba(15, 23, 42, .2);
        font-weight: 800;
        z-index: 60;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
}
