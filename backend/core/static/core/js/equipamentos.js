// equipamentos.js - NotchFire

let currentPage = 1;
let rowsPerPage = 10;
let searchTerm = '';
let sortDirection = 'asc';
let statusFiltro = '';

const API_URLS = {
    listar: '/api/equipamentos/',
    detalhe: (id) => `/equipamentos/${id}/`,
};

function canManageSystem() {
    return window.NOTCHFIRE_CAN_MANAGE === true;
}

document.addEventListener('DOMContentLoaded', () => {
    carregarEquipamentos();
    configurarEventListeners();
});

async function carregarEquipamentos() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'block';

    try {
        const params = new URLSearchParams({
            page: currentPage,
            rows: rowsPerPage,
            search: searchTerm,
            sort: sortDirection
        });

        if (statusFiltro) params.set('status', statusFiltro);

        const data = await fetchJson(`${API_URLS.listar}?${params.toString()}`);

        if (data.success) {
            atualizarResumo(data);

            if (data.data && data.data.length > 0) {
                renderizarTabela(data.data);
            } else {
                mostrarSemDados();
            }

            renderizarPaginacao(data.total || 0);
        } else {
            mostrarErro(data.error || 'Erro ao carregar equipamentos.');
        }
    } catch (error) {
        mostrarErro(error.message || 'Não foi possível carregar os equipamentos.');
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function configurarEventListeners() {
    const searchInput = document.getElementById('searchEquipamento');
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchTerm = event.target.value.trim();
                currentPage = 1;
                carregarEquipamentos();

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
            carregarEquipamentos();
        });
    }

    const filtroStatus = document.getElementById('filtroStatus');
    if (filtroStatus) {
        filtroStatus.addEventListener('change', () => {
            statusFiltro = filtroStatus.value;
            currentPage = 1;
            carregarEquipamentos();
        });
    }

    const sortIcon = document.querySelector('.sort-icon');
    if (sortIcon) {
        sortIcon.addEventListener('click', () => {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            sortIcon.className = `fa-solid fa-arrow-${sortDirection === 'asc' ? 'up' : 'down'} sort-icon`;
            currentPage = 1;
            carregarEquipamentos();
        });
    }

    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', () => {
            rowsPerPage = parseInt(rowsPerPageSelect.value, 10);
            currentPage = 1;
            carregarEquipamentos();
        });
    }
}

function renderizarTabela(equipamentosList) {
    const tbody = document.getElementById('equipamentosTableBody');
    const noResults = document.getElementById('noResults');
    if (!tbody) return;

    if (noResults) noResults.style.display = 'none';

    tbody.innerHTML = equipamentosList.map((equip) => `
        <tr onclick="abrirDetalheEquipamento(${equip.id})">
            <td class="foto">
                <img src="${equip.foto_url || '/static/core/img/logo.png'}" class="equip-img" alt="Foto" onerror="this.src='/static/core/img/logo.png'">
            </td>
            <td>
                <span class="equip-name">${escapeHtml(equip.nome)}</span>
                <span class="equip-meta">Série: ${escapeHtml(equip.numero_serie || '-')}</span>
                ${equip.marca ? `<span class="equip-meta">Marca: ${escapeHtml(equip.marca)}</span>` : ''}
                <span class="badge ${equip.status ? 'badge-status-active' : 'badge-status-inactive'}">
                    ${equip.status ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${escapeHtml(equip.tipo_nome || '-')}</td>
            <td><span class="badge">${escapeHtml(equip.grupo_nome || '-')}</span></td>
            <td>${escapeHtml(equip.local || '-')}</td>
            <td class="text-center" onclick="event.stopPropagation()">
                ${equip.qr_code_url ? `<img src="${equip.qr_code_url}" class="qr-code-img" onclick="imprimirQRCode('${equip.qr_code_url}')" title="Imprimir QR Code">` : '-'}
            </td>
            <td class="actions" onclick="event.stopPropagation()">
                <a href="${API_URLS.detalhe(equip.id)}" class="btn-icon" title="Ver detalhes">
                    <i class="fa-solid fa-eye"></i>
                </a>
            </td>
        </tr>
    `).join('');
}

function atualizarResumo(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryAtivos', data.total_ativos || 0);
    setText('summaryInativos', data.total_inativos || 0);
    setText('summaryTipos', data.total_tipos || 0);
}

function mostrarSemDados() {
    const tbody = document.getElementById('equipamentosTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-folder-open"></i>
            <p>Nenhum equipamento encontrado</p>
            ${canManageSystem() ? `
            <a href="/equipamentos/criar/" class="btn btn-primary btn-sm">
                <i class="fa-solid fa-plus"></i> Criar equipamento
            </a>
            ` : ''}
        `;
        noResults.style.display = 'block';
    }
}

function mostrarErro(mensagem) {
    const tbody = document.getElementById('equipamentosTableBody');
    const noResults = document.getElementById('noResults');
    const loading = document.getElementById('loading');

    if (tbody) tbody.innerHTML = '';
    if (loading) loading.style.display = 'none';

    if (noResults) {
        noResults.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>${escapeHtml(mensagem)}</p>
            <button class="btn btn-primary btn-sm" onclick="carregarEquipamentos()">
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
    carregarEquipamentos();
}

function abrirDetalheEquipamento(id) {
    window.location.href = API_URLS.detalhe(id);
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

async function fetchJson(url) {
    const response = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok || data.success === false) {
        throw new Error(data.error || 'Não foi possível concluir a ação.');
    }

    return data;
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

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}
