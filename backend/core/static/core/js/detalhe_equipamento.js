let servicosCache = [];
let tipoServicoSelecionado = 'todos';
let subtabAtual = 'concluido';

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    configurarTabs();
    configurarSubtabs();
    configurarModais();
    carregarServicos();
});

function configurarTabs() {
    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;

            document.querySelectorAll('.tab-btn').forEach((btn) => btn.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.remove('active'));

            button.classList.add('active');
            const panel = document.getElementById(tabId);
            if (panel) panel.classList.add('active');

            if (tabId === 'tab-servicos' && servicosCache.length === 0) {
                carregarServicos();
            }
        });
    });
}

function configurarSubtabs() {
    document.querySelectorAll('.subtab-btn').forEach((button) => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.subtab-btn').forEach((btn) => btn.classList.remove('active'));
            button.classList.add('active');
            subtabAtual = button.dataset.subtab === 'rascunhos' ? 'rascunho' : 'concluido';
            carregarServicos();
        });
    });
}

function configurarModais() {
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.show').forEach((modal) => {
                closeModal(modal.id);
            });
        }
    });

    document.querySelectorAll('.modal-overlay').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) closeModal(modal.id);
        });
    });
}

async function carregarServicos() {
    const container = document.getElementById('servicosTimeline');
    if (!container) return;

    container.innerHTML = `
        <div class="timeline-loading">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <p>Carregando vistorias...</p>
        </div>
    `;

    try {
        const params = new URLSearchParams({
            equipamento_id: EQUIPAMENTO_ID,
            status: subtabAtual,
            rows: 50,
            sort: 'desc'
        });
        const response = await fetch(`/api/servicos/?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Não foi possível carregar os serviços.');
        }

        servicosCache = data.data || [];
        renderizarServicos();
    } catch (error) {
        container.innerHTML = `
            <div class="empty-servicos">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function renderizarServicos() {
    const container = document.getElementById('servicosTimeline');
    if (!container) return;

    const servicosFiltrados = servicosCache.filter((servico) => {
        return tipoServicoSelecionado === 'todos' || servico.tipo_servico_nome === tipoServicoSelecionado;
    });

    if (servicosFiltrados.length === 0) {
        const texto = subtabAtual === 'rascunho'
            ? 'Nenhum rascunho encontrado para este equipamento'
            : 'Nenhuma vistoria/checklist realizado para este equipamento';

        container.innerHTML = `
            <div class="empty-servicos">
                <i class="fa-solid fa-clipboard-list"></i>
                <p>${texto}</p>
                ${canManageSystem() ? `
                <button class="btn btn-sm btn-primary" onclick="novoServico()">
                    <i class="fa-solid fa-plus"></i> Criar serviço
                </button>
                ` : ''}
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="timeline-list">
            ${servicosFiltrados.map((servico) => renderizarServicoTimeline(servico)).join('')}
        </div>
    `;
}

function renderizarServicoTimeline(servico) {
    return `
        <div class="timeline-item">
            <div class="timeline-card" onclick="abrirDetalheServico(${servico.id})">
                <span class="timeline-date">${escapeHtml(servico.data_realizacao || '-')}</span>
                <div class="timeline-title">${escapeHtml(servico.tipo_servico_nome || 'Serviço')}</div>
                <div class="timeline-meta">
                    <i class="fa-solid fa-user-check"></i>
                    ${escapeHtml(servico.realizado_por_nome || '-')}
                    ${servico.local ? ` · ${escapeHtml(servico.local)}` : ''}
                </div>
                <div class="checklist-counts">
                    <span class="check-pill check-ok"><i class="fa-solid fa-check"></i> ${servico.itens_atende || 0}</span>
                    <span class="check-pill check-fail"><i class="fa-solid fa-xmark"></i> ${servico.itens_nao_atende || 0}</span>
                    <span class="check-pill check-na"><i class="fa-solid fa-minus"></i> ${servico.itens_nao_aplica || 0}</span>
                    <span class="check-pill check-na">${Number(servico.pontuacao_percentual || 0).toFixed(0)}%</span>
                </div>
            </div>
            <div class="timeline-node"><span></span></div>
        </div>
    `;
}

async function abrirDetalheServico(id) {
    const body = document.getElementById('servicoDetalheBody');
    const title = document.getElementById('servicoDetalheTitle');
    const subtitle = document.getElementById('servicoDetalheSubtitle');

    if (title) title.innerHTML = '<i class="fa-solid fa-clipboard-check"></i> Serviço Realizado';
    if (subtitle) subtitle.textContent = '';
    configurarBotaoRelatorioServico(null);
    if (body) {
        body.innerHTML = `
            <div class="loading-spinner">
                <i class="fa-solid fa-spinner fa-spin"></i> Carregando...
            </div>
        `;
    }

    openModal('servicoDetalheModal');

    try {
        const response = await fetch(`/api/servicos/${id}/`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const payload = await response.json();

        if (!response.ok || !payload.success) {
            throw new Error(payload.error || 'Não foi possível carregar o detalhe do serviço.');
        }

        const servico = payload.data;
        if (title) title.innerHTML = `<i class="fa-solid fa-clipboard-check"></i> ${escapeHtml(servico.tipo_servico_nome)}`;
        if (subtitle) {
            subtitle.textContent = `${servico.data_realizacao || '-'} · ${servico.realizado_por_nome || '-'}`;
        }
        configurarBotaoRelatorioServico(servico);
        if (body) body.innerHTML = renderizarDetalheServico(servico);
    } catch (error) {
        configurarBotaoRelatorioServico(null);
        if (body) {
            body.innerHTML = `
                <div class="empty-servicos">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>${escapeHtml(error.message)}</p>
                </div>
            `;
        }
    }
}

function configurarBotaoRelatorioServico(servico) {
    const relatorioBtn = document.getElementById('servicoRelatorioBtn');
    if (!relatorioBtn) return;

    if (!servico || !servico.id || !canManageSystem()) {
        relatorioBtn.classList.add('disabled');
        relatorioBtn.setAttribute('aria-disabled', 'true');
        relatorioBtn.href = '#';
        return;
    }

    const params = new URLSearchParams({
        servico_id: servico.id,
        equipamento_id: servico.equipamento_id || EQUIPAMENTO_ID,
    });
    if (servico.tipo_servico_id) params.set('tipo_servico_id', servico.tipo_servico_id);

    relatorioBtn.href = `/relatorios/exportar/condensado/?${params.toString()}`;
    relatorioBtn.classList.remove('disabled');
    relatorioBtn.removeAttribute('aria-disabled');
}

function renderizarDetalheServico(servico) {
    const respostas = servico.respostas || [];

    return `
        <div class="servico-detail-grid">
            <div class="servico-detail-stat">
                <span>Checklist</span>
                <strong>${servico.total_itens || 0} itens</strong>
            </div>
            <div class="servico-detail-stat">
                <span>Atende</span>
                <strong>${servico.itens_atende || 0}</strong>
            </div>
            <div class="servico-detail-stat">
                <span>Não atende</span>
                <strong>${servico.itens_nao_atende || 0}</strong>
            </div>
            <div class="servico-detail-stat">
                <span>Pontuação</span>
                <strong>${Number(servico.pontuacao_percentual || 0).toFixed(0)}%</strong>
            </div>
        </div>

        ${renderizarVencimentosEquipamento(servico.equipamento_vencimentos)}

        ${servico.observacoes ? `
            <div class="resposta-obs" style="margin-bottom:14px;">
                <strong>Observações gerais:</strong> ${escapeHtml(servico.observacoes)}
            </div>
        ` : ''}

        <div class="resposta-list">
            ${respostas.length ? respostas.map(renderizarResposta).join('') : `
                <div class="empty-servicos">
                    <i class="fa-solid fa-clipboard"></i>
                    <p>Nenhuma resposta registrada para este checklist</p>
                </div>
            `}
        </div>
    `;
}

function renderizarVencimentosEquipamento(vencimentos) {
    if (!vencimentos || !vencimentos.possui_vencimento) return '';

    if (vencimentos.is_extintor) {
        return `
            <div class="vencimentos-servico-card">
                <strong><i class="fa-solid fa-calendar-check"></i> Vencimentos do extintor</strong>
                <div>
                    <span>Carga: ${escapeHtml(vencimentos.vencimento_carga_formatado || vencimentos.vencimento_carga || '-')}</span>
                    <span>Teste hidrostático: ${escapeHtml(vencimentos.vencimento_teste_hidrostatico_formatado || vencimentos.vencimento_teste_hidrostatico || '-')}</span>
                </div>
            </div>
        `;
    }

    return `
        <div class="vencimentos-servico-card">
            <strong><i class="fa-solid fa-calendar-check"></i> Vencimento do equipamento</strong>
            <div>
                <span>${escapeHtml(vencimentos.data_vencimento_formatada || vencimentos.data_vencimento || '-')}</span>
            </div>
        </div>
    `;
}

function renderizarResposta(resposta) {
    const classe = resposta.opcao === 'atende'
        ? 'check-ok'
        : resposta.opcao === 'nao_atende'
            ? 'check-fail'
            : 'check-na';

    const fotoUrl = resposta.foto_url || resposta.fotos_url || resposta.foto || '';

    return `
        <div class="resposta-item">
            <div class="resposta-top">
                <div>
                    <div class="resposta-secao">${escapeHtml(resposta.secao_nome || 'Checklist')}</div>
                    <div class="resposta-pergunta">${escapeHtml(resposta.pergunta || '-')}</div>
                </div>
                <span class="check-pill ${classe}">${escapeHtml(resposta.opcao_display || '-')}</span>
            </div>
            ${resposta.observacao ? `<div class="resposta-obs">${escapeHtml(resposta.observacao)}</div>` : ''}
            ${fotoUrl ? `
                <button type="button" class="resposta-foto" onclick="openFotoModal(${escapeJsArg(fotoUrl)})">
                    <img src="${escapeHtml(fotoUrl)}" alt="Foto anexada ao checklist" loading="lazy">
                    <span><i class="fa-solid fa-image"></i> Ver foto anexada</span>
                </button>
            ` : ''}
        </div>
    `;
}

function filtrarServicos(tipo, button) {
    tipoServicoSelecionado = tipo;
    document.querySelectorAll('.filtro-tipo-btn').forEach((btn) => btn.classList.remove('active'));
    if (button) button.classList.add('active');
    renderizarServicos();
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('show');

    if (!document.querySelector('.modal-overlay.show')) {
        document.body.style.overflow = '';
    }
}

function openFotoModal(url) {
    const img = document.getElementById('fotoModalImg');
    if (img) img.src = url;
    openModal('fotoModal');
}

async function salvarEdicao() {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para editar equipamentos.', true);
        return;
    }

    const payload = {
        tipo_equipamento_id: getValue('editTipoEquipamento'),
        predio_id: getValue('editPredio'),
        departamento_id: getValue('editDepartamento'),
        numero_serie: getValue('editNumeroSerie'),
        data_fabricacao: getValue('editDataFabricacao'),
        marca: getValue('editMarca'),
        descricao: getValue('editDescricao'),
        ponto_referencia: getValue('editPontoReferencia')
    };

    try {
        const response = await fetch(`/api/equipamentos/${EQUIPAMENTO_ID}/editar/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Não foi possível salvar o equipamento.');
        }

        mostrarToast(data.message || 'Equipamento atualizado.');
        setTimeout(() => window.location.reload(), 650);
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

async function uploadFoto(input) {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para alterar a foto do equipamento.', true);
        if (input) input.value = '';
        return;
    }

    if (!input.files || !input.files[0]) return;

    const formData = new FormData();
    formData.append('foto', input.files[0]);

    try {
        const response = await fetch(`/api/equipamentos/${EQUIPAMENTO_ID}/foto/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Não foi possível atualizar a foto.');
        }

        mostrarToast(data.message || 'Foto atualizada.');
        setTimeout(() => window.location.reload(), 650);
    } catch (error) {
        mostrarToast(error.message, true);
        input.value = '';
    }
}

async function toggleAtivo() {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para alterar o status do equipamento.', true);
        return;
    }

    try {
        const response = await fetch(`/api/equipamentos/${EQUIPAMENTO_ID}/toggle-ativo/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Não foi possível alterar o status.');
        }

        mostrarToast(data.message || 'Status atualizado.');
        setTimeout(() => window.location.reload(), 650);
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

async function excluirEquipamento() {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para excluir equipamentos.', true);
        return;
    }

    try {
        const response = await fetch(`/api/equipamentos/${EQUIPAMENTO_ID}/excluir/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Não foi possível excluir o equipamento.');
        }

        mostrarToast(data.message || 'Equipamento excluído.');
        setTimeout(() => window.location.href = '/equipamentos/', 650);
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

function imprimirQRCode(url) {
    const janela = window.open('', '_blank');
    if (!janela) {
        mostrarToast('Permita pop-ups para imprimir o QR Code.', true);
        return;
    }

    janela.document.write(`
        <html>
            <head>
                <title>Imprimir QR Code</title>
                <style>
                    body {
                        align-items: center;
                        display: flex;
                        font-family: Arial, sans-serif;
                        height: 100vh;
                        justify-content: center;
                        margin: 0;
                    }
                    .container { text-align: center; }
                    img { height: 260px; width: 260px; }
                    h3 { color: #1a3a5a; margin-top: 18px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <img src="${url}" onload="window.print(); window.onafterprint = window.close;">
                    <h3>QR Code do Equipamento</h3>
                </div>
            </body>
        </html>
    `);
    janela.document.close();
}

function novoServico(tipoServicoId = null) {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para criar serviços.', true);
        return;
    }

    const params = new URLSearchParams({
        equipamento_id: EQUIPAMENTO_ID,
        novo: '1',
    });

    if (tipoServicoId) params.set('tipo_servico_id', tipoServicoId);

    window.location.href = `/servicos/?${params.toString()}`;
}

function agendarServico(tipoServicoId = null) {
    novoServico(tipoServicoId);
}

function verChecklist() {
    const timeline = document.getElementById('servicosTimeline');
    if (timeline) timeline.scrollIntoView({ behavior: 'smooth', block: 'start' });
    mostrarToast('Abra uma vistoria realizada para ver as respostas do checklist.');
}

function gerarRelatorioServicos() {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para gerar relatórios.', true);
        return;
    }

    window.print();
}

function uploadAnexo(input) {
    if (!canManageSystem()) {
        mostrarToast('Você não tem permissão para adicionar anexos.', true);
        if (input) input.value = '';
        return;
    }

    const total = input.files ? input.files.length : 0;
    mostrarToast(total ? `${total} anexo(s) selecionado(s).` : 'Nenhum anexo selecionado.');
    input.value = '';
}

function getValue(id) {
    const element = document.getElementById(id);
    return element ? element.value : '';
}

function getCsrfToken() {
    if (typeof CSRF_TOKEN !== 'undefined' && CSRF_TOKEN) return CSRF_TOKEN;

    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
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

function escapeJsArg(text) {
    return JSON.stringify(String(text || ''));
}
