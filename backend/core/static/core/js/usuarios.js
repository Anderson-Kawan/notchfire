let usuariosPage = 1;
let usuariosRows = 10;
let usuariosSearch = '';
let usuariosSort = 'asc';
let usuariosStatus = '';
let usuariosTipo = '';
let usuariosPredio = '';
let usuariosDebounce = null;
let usuarioModalModo = 'criar';
let usuarioModalAtual = null;

const USUARIOS_API = {
    listar: '/api/usuarios/',
    criar: '/api/usuarios/criar/',
    detalhe: (id) => `/api/usuarios/${id}/`,
};

document.addEventListener('DOMContentLoaded', () => {
    carregarUsuarios();
    configurarUsuariosEventos();
});

function configurarUsuariosEventos() {
    const searchInput = document.getElementById('searchUsuarios');
    const clearBtn = document.getElementById('clearSearch');
    const rowsSelect = document.getElementById('rowsPerPage');
    const filtroTipo = document.getElementById('filtroTipo');
    const filtroPredio = document.getElementById('filtroPredio');
    const sortBtn = document.getElementById('sortUsuarios');
    const abrirBtn = document.getElementById('abrirNovoUsuario');
    const fecharBtn = document.getElementById('fecharUsuarioModal');
    const cancelarBtn = document.getElementById('cancelarUsuario');
    const modal = document.getElementById('usuarioModal');
    const form = document.getElementById('usuarioForm');
    const exportarBtn = document.getElementById('exportarUsuarios');

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            clearTimeout(usuariosDebounce);
            usuariosDebounce = setTimeout(() => {
                usuariosSearch = event.target.value.trim();
                usuariosPage = 1;
                carregarUsuarios();
                if (clearBtn) clearBtn.style.display = usuariosSearch ? 'flex' : 'none';
            }, 260);
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            usuariosSearch = '';
            usuariosPage = 1;
            clearBtn.style.display = 'none';
            carregarUsuarios();
        });
    }

    if (rowsSelect) {
        rowsSelect.addEventListener('change', () => {
            usuariosRows = parseInt(rowsSelect.value, 10);
            usuariosPage = 1;
            carregarUsuarios();
        });
    }

    if (filtroTipo) {
        filtroTipo.addEventListener('change', () => {
            usuariosTipo = filtroTipo.value;
            usuariosPage = 1;
            carregarUsuarios();
        });
    }

    if (filtroPredio) {
        filtroPredio.addEventListener('change', () => {
            usuariosPredio = filtroPredio.value;
            usuariosPage = 1;
            carregarUsuarios();
        });
    }

    if (sortBtn) {
        sortBtn.addEventListener('click', () => {
            usuariosSort = usuariosSort === 'asc' ? 'desc' : 'asc';
            sortBtn.innerHTML = `<i class="fa-solid fa-arrow-${usuariosSort === 'asc' ? 'up' : 'down'}"></i>`;
            usuariosPage = 1;
            carregarUsuarios();
        });
    }

    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach((tab) => tab.classList.remove('active'));
            button.classList.add('active');
            usuariosStatus = button.dataset.status || '';
            usuariosPage = 1;
            carregarUsuarios();
        });
    });

    if (abrirBtn) abrirBtn.addEventListener('click', abrirUsuarioModalCriacao);
    if (fecharBtn) fecharBtn.addEventListener('click', fecharUsuarioModal);
    if (cancelarBtn) cancelarBtn.addEventListener('click', fecharUsuarioModal);
    if (exportarBtn) exportarBtn.addEventListener('click', exportarUsuarios);
    if (form) form.addEventListener('submit', salvarUsuarioModal);
    configurarPreviewFoto('fotoUsuario', 'fotoUsuarioPreview');

    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) fecharUsuarioModal();
        });
    }

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;

        if (modal && modal.classList.contains('open')) {
            fecharUsuarioModal();
        }
    });
}

async function carregarUsuarios() {
    const loading = document.getElementById('loading');
    const noResults = document.getElementById('noResults');
    const tbody = document.getElementById('usuariosTableBody');

    if (loading) loading.style.display = 'block';
    if (noResults) noResults.style.display = 'none';

    try {
        const data = await fetchUsuariosJson(`${USUARIOS_API.listar}?${montarParametros().toString()}`);

        atualizarResumoUsuarios(data);

        if (data.data && data.data.length > 0) {
            renderizarUsuarios(data.data);
        } else {
            if (tbody) tbody.innerHTML = '';
            if (noResults) noResults.style.display = 'block';
        }

        renderizarUsuariosPaginacao(data.total || 0);
    } catch (error) {
        if (tbody) tbody.innerHTML = '';
        if (noResults) {
            noResults.innerHTML = `
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${escapeHtml(error.message || 'Não foi possível carregar os usuários.')}</p>
            `;
            noResults.style.display = 'block';
        }
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function montarParametros(extra = {}) {
    const params = new URLSearchParams({
        page: extra.page || usuariosPage,
        rows: extra.rows || usuariosRows,
        search: usuariosSearch,
        sort: usuariosSort,
    });

    if (usuariosStatus) params.set('status', usuariosStatus);
    if (usuariosTipo) params.set('tipo_acesso', usuariosTipo);
    if (usuariosPredio) params.set('predio_id', usuariosPredio);

    return params;
}

function renderizarUsuarios(lista) {
    const tbody = document.getElementById('usuariosTableBody');
    const noResults = document.getElementById('noResults');
    if (!tbody) return;
    if (noResults) noResults.style.display = 'none';

    tbody.innerHTML = lista.map((usuario) => `
        <tr onclick="abrirUsuarioVisualizacao(${usuario.id})">
            <td>
                <div class="user-cell">
                    ${renderAvatar(usuario)}
                    <div>
                        <span class="user-name">${escapeHtml(usuario.nome)}</span>
                        <span class="user-meta">${escapeHtml(usuario.username)}</span>
                    </div>
                </div>
            </td>
            <td>${escapeHtml(usuario.email || '-')}</td>
            <td><span class="badge">${escapeHtml(usuario.tipo_acesso_label)}</span></td>
            <td><span class="badge">${escapeHtml(usuario.predio_nome || '-')}</span></td>
            <td><span class="badge badge-status-${escapeHtml(usuario.status)}">${escapeHtml(usuario.status_label)}</span></td>
            <td>${escapeHtml(usuario.ultimo_acesso)}</td>
        </tr>
    `).join('');
}

function renderAvatar(usuario) {
    if (usuario.foto_url) {
        return `<img src="${escapeHtml(usuario.foto_url)}" class="avatar avatar-img" alt="${escapeHtml(usuario.nome)}">`;
    }

    return `<span class="avatar">${escapeHtml(usuario.iniciais)}</span>`;
}

async function abrirUsuarioEdicao(id) {
    try {
        const data = await fetchUsuariosJson(USUARIOS_API.detalhe(id));
        abrirUsuarioModalEdicao(data.data);
    } catch (error) {
        mostrarUsuariosToast(error.message || 'Não foi possível abrir o usuário.', true);
    }
}

async function abrirUsuarioVisualizacao(id) {
    try {
        const data = await fetchUsuariosJson(USUARIOS_API.detalhe(id));
        usuarioModalModo = 'visualizar';
        usuarioModalAtual = data.data;
        abrirUsuarioModal(data.data);
    } catch (error) {
        mostrarUsuariosToast(error.message || 'Não foi possível abrir o usuário.', true);
    }
}

function atualizarResumoUsuarios(data) {
    setText('summaryTotal', data.total || 0);
    setText('summaryAtivos', data.total_ativos || 0);
    setText('summaryConvites', data.total_convites || 0);
    setText('summaryAdmins', data.total_admins || 0);
}

function renderizarUsuariosPaginacao(total) {
    const totalPages = Math.ceil(total / usuariosRows);
    const pagination = document.getElementById('paginationControls');
    if (!pagination) return;

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    const startPage = Math.max(1, usuariosPage - 2);
    const endPage = Math.min(totalPages, usuariosPage + 2);

    let html = `
        <button class="page-btn" onclick="mudarUsuariosPagina(1)" ${usuariosPage === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-left"></i>
        </button>
        <button class="page-btn" onclick="mudarUsuariosPagina(${usuariosPage - 1})" ${usuariosPage === 1 ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-left"></i>
        </button>
    `;

    if (startPage > 1) html += '<span class="page-info">...</span>';

    for (let page = startPage; page <= endPage; page += 1) {
        html += `
            <button class="page-btn ${page === usuariosPage ? 'page-active' : ''}" onclick="mudarUsuariosPagina(${page})">
                ${page}
            </button>
        `;
    }

    if (endPage < totalPages) html += '<span class="page-info">...</span>';

    html += `
        <button class="page-btn" onclick="mudarUsuariosPagina(${usuariosPage + 1})" ${usuariosPage === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-chevron-right"></i>
        </button>
        <button class="page-btn" onclick="mudarUsuariosPagina(${totalPages})" ${usuariosPage === totalPages ? 'disabled' : ''}>
            <i class="fa-solid fa-angles-right"></i>
        </button>
    `;

    pagination.innerHTML = html;
}

function mudarUsuariosPagina(page) {
    usuariosPage = page;
    carregarUsuarios();
}

function abrirUsuarioModalCriacao() {
    usuarioModalModo = 'criar';
    usuarioModalAtual = null;
    abrirUsuarioModal();
}

function abrirUsuarioModalEdicao(usuario) {
    usuarioModalModo = 'editar';
    usuarioModalAtual = usuario;
    abrirUsuarioModal(usuario);
}

function abrirUsuarioModal(usuario = null) {
    const modal = document.getElementById('usuarioModal');
    const form = document.getElementById('usuarioForm');
    const feedback = document.getElementById('formFeedback');
    const title = document.getElementById('usuarioModalTitle');
    const senhaInput = document.getElementById('senhaUsuario');
    const senhaLabel = document.getElementById('senhaUsuarioLabel');
    if (!modal) return;

    if (form) form.reset();
    if (title) {
        title.innerHTML = usuarioModalModo === 'visualizar'
            ? '<i class="fa-solid fa-eye"></i> Usuário'
            : usuario
            ? '<i class="fa-solid fa-pen"></i> Editar usuário'
            : '<i class="fa-solid fa-user-plus"></i> Novo usuário';
    }

    if (senhaInput) {
        senhaInput.value = '';
        senhaInput.required = !usuario;
        senhaInput.placeholder = usuario ? 'Preencha apenas se quiser alterar' : '';
    }

    if (senhaLabel) {
        senhaLabel.textContent = usuario ? 'Nova senha (opcional)' : 'Senha';
    }

    if (usuario) {
        preencherUsuarioModal(usuario);
    } else {
        resetarPreviewFoto('fotoUsuarioPreview', 'US');
    }

    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    setUsuarioReadOnly(usuarioModalModo === 'visualizar', usuario?.id || null);

    document.body.classList.add('user-modal-open');
    modal.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => {
        modal.classList.add('open');
        document.getElementById('nomeUsuario')?.focus();
    });
}

function fecharUsuarioModal() {
    const modal = document.getElementById('usuarioModal');
    if (!modal) return;

    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('user-modal-open');
    usuarioModalModo = 'criar';
    usuarioModalAtual = null;
    setUsuarioReadOnly(false);
}

function setUsuarioReadOnly(readOnly, id = null) {
    const form = document.getElementById('usuarioForm');
    if (!form) return;

    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
        field.disabled = readOnly;
    });

    const submitBtn = document.getElementById('salvarUsuario');
    if (submitBtn) submitBtn.style.display = readOnly ? 'none' : '';

    const cancelBtn = document.getElementById('cancelarUsuario');
    if (cancelBtn) cancelBtn.textContent = readOnly ? 'Fechar' : 'Cancelar';

    let editBtn = document.getElementById('usuarioEditBtn');
    const footer = form.querySelector('.modal-footer');
    if (!editBtn && footer) {
        editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.id = 'usuarioEditBtn';
        editBtn.className = 'btn btn-primary';
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
        footer.insertBefore(editBtn, submitBtn || null);
    }

    if (editBtn) {
        editBtn.style.display = readOnly ? '' : 'none';
        editBtn.onclick = () => {
            if (id) abrirUsuarioEdicao(id);
        };
    }
}

function preencherUsuarioModal(usuario) {
    setValue('nomeUsuario', usuario.nome || '');
    setValue('usernameUsuario', usuario.username || '');
    setValue('emailUsuario', usuario.email || '');
    setValue('predioUsuario', usuario.predio_id || '');
    setFormValue('usuarioForm', 'status', usuario.status || 'ativo');
    setPreviewFoto('fotoUsuarioPreview', usuario.foto_url || '', usuario.iniciais || 'US');

    const fotoInput = document.getElementById('fotoUsuario');
    if (fotoInput) fotoInput.value = '';

    document.querySelectorAll('#usuarioForm input[name="tipo_acesso"]').forEach((input) => {
        input.checked = input.value === usuario.tipo_acesso;
    });
}

async function salvarUsuarioModal(event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = document.getElementById('salvarUsuario');
    const feedback = document.getElementById('formFeedback');

    const formData = new FormData(form);

    if (feedback) {
        feedback.textContent = '';
        feedback.classList.remove('show');
    }

    if (submitBtn) submitBtn.disabled = true;

    try {
        const url = usuarioModalModo === 'editar' && usuarioModalAtual
            ? USUARIOS_API.detalhe(usuarioModalAtual.id)
            : USUARIOS_API.criar;

        const data = await fetchUsuariosJson(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
        });

        mostrarUsuariosToast(data.message || (usuarioModalModo === 'editar' ? 'Usuário atualizado com sucesso!' : 'Usuário criado com sucesso!'));
        fecharUsuarioModal();
        resetarPreviewFoto('fotoUsuarioPreview', 'US');
        usuariosPage = 1;
        carregarUsuarios();
    } catch (error) {
        if (feedback) {
            feedback.textContent = error.message || 'Não foi possível salvar o usuário.';
            feedback.classList.add('show');
        } else {
            mostrarUsuariosToast(error.message || 'Não foi possível salvar o usuário.', true);
        }
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function exportarUsuarios() {
    try {
        const params = montarParametros({ page: 1, rows: 10000 });
        const data = await fetchUsuariosJson(`${USUARIOS_API.listar}?${params.toString()}`);
        const linhas = [
            ['Nome', 'Login', 'E-mail', 'Tipo de acesso', 'Predio', 'Status', 'Ultimo acesso', 'Criado em'],
            ...(data.data || []).map((usuario) => [
                usuario.nome,
                usuario.username,
                usuario.email,
                usuario.tipo_acesso_label,
                usuario.predio_nome,
                usuario.status_label,
                usuario.ultimo_acesso,
                usuario.criado_em,
            ]),
        ];

        const csv = linhas.map((linha) => linha.map(formatarCsv).join(';')).join('\n');
        const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'usuarios_notchfire.csv';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        mostrarUsuariosToast('Dados exportados com sucesso.');
    } catch (error) {
        mostrarUsuariosToast(error.message || 'Não foi possível exportar os usuários.', true);
    }
}

function formatarCsv(value) {
    const text = value === null || value === undefined ? '' : String(value);
    return `"${text.replace(/"/g, '""')}"`;
}

function configurarPreviewFoto(inputId, previewId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('change', () => {
        const file = input.files && input.files[0];
        if (!file) return;

        const url = URL.createObjectURL(file);
        setPreviewFoto(previewId, url, '');
    });
}

function setPreviewFoto(previewId, fotoUrl, iniciais) {
    const preview = document.getElementById(previewId);
    if (!preview) return;

    const img = preview.querySelector('img');
    const span = preview.querySelector('span');

    if (img) {
        img.src = fotoUrl || '';
        img.style.display = fotoUrl ? 'block' : 'none';
    }

    if (span) {
        span.textContent = iniciais || 'US';
        span.style.display = fotoUrl ? 'none' : 'flex';
    }
}

function resetarPreviewFoto(previewId, iniciais) {
    setPreviewFoto(previewId, '', iniciais);
}

async function fetchUsuariosJson(url, options = {}) {
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

function mostrarUsuariosToast(message, isError = false) {
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

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
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
    if (element) element.checked = !!value;
}

function setFormValue(formId, fieldName, value) {
    const element = document.querySelector(`#${formId} [name="${fieldName}"]`);
    if (element) element.value = value ?? '';
}
