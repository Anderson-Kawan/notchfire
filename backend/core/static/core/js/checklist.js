// checklist.js

let itemParaExcluir = null;

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    configurarEventListeners();
});

function configurarEventListeners() {
    // Preview de imagem
    const imagemInput = document.getElementById('imagem_descritiva');
    if (imagemInput) {
        imagemInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validar tipo de arquivo
                const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
                if (!validTypes.includes(file.type)) {
                    mostrarToast('Selecione uma imagem válida (JPEG, PNG ou GIF).', true);
                    imagemInput.value = '';
                    return;
                }
                
                // Validar tamanho (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    mostrarToast('A imagem deve ter no máximo 5MB.', true);
                    imagemInput.value = '';
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(event) {
                    const preview = document.getElementById('imagemPreview');
                    if (preview) {
                        renderImagePreview(preview, event.target.result);
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Modais
    const modal = document.getElementById('itemModal');
    const excluirModal = document.getElementById('excluirItemModal');
    const closeBtns = document.querySelectorAll('.close');
    
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            fecharModalItem();
            fecharModalExcluirItem();
        });
    });
    
    window.addEventListener('click', function(e) {
        if (e.target === modal) fecharModalItem();
        if (e.target === excluirModal) fecharModalExcluirItem();
    });
    
    // Formulário
    const form = document.getElementById('itemForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            salvarItem();
        });
    }
}

// Funções globais
window.abrirModalCriarItem = function() {
    const modalTitle = document.getElementById('modalTitle');
    const form = document.getElementById('itemForm');
    const itemId = document.getElementById('itemId');
    const imagemPreview = document.getElementById('imagemPreview');
    
    if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-plus"></i> Criar Pergunta';
    if (form) form.reset();
    if (itemId) itemId.value = '';
    if (imagemPreview) {
        imagemPreview.innerHTML = '';
        imagemPreview.style.display = 'none';
    }
    
    const obrigatorioCheckbox = document.getElementById('obrigatorio');
    if (obrigatorioCheckbox) obrigatorioCheckbox.checked = true;
    
    const modal = document.getElementById('itemModal');
    if (modal) modal.style.display = 'block';
};

window.editarItem = async function(id) {
    try {
        const response = await fetch(`/api/checklist-itens/${id}/`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!response.ok) throw new Error('request_failed');
        const data = await response.json();
        
        if (data.success) {
            const modalTitle = document.getElementById('modalTitle');
            const itemId = document.getElementById('itemId');
            const secaoSelect = document.getElementById('secao');
            const perguntaTextarea = document.getElementById('pergunta');
            const tipoRespostaSelect = document.getElementById('tipo_resposta');
            const detalhamentoTextarea = document.getElementById('detalhamento');
            const ordemInput = document.getElementById('ordem');
            const obrigatorioCheckbox = document.getElementById('obrigatorio');
            const imagemPreview = document.getElementById('imagemPreview');
            
            if (modalTitle) modalTitle.innerHTML = '<i class="fa-solid fa-edit"></i> Editar Pergunta';
            if (itemId) itemId.value = data.item.id;
            if (secaoSelect) secaoSelect.value = data.item.secao_id || '';
            if (perguntaTextarea) perguntaTextarea.value = data.item.pergunta;
            if (tipoRespostaSelect) tipoRespostaSelect.value = data.item.tipo_resposta;
            if (detalhamentoTextarea) detalhamentoTextarea.value = data.item.detalhamento || '';
            if (ordemInput) ordemInput.value = data.item.ordem;
            if (obrigatorioCheckbox) obrigatorioCheckbox.checked = data.item.obrigatorio;
            
            if (data.item.imagem_url && imagemPreview) {
                renderImagePreview(imagemPreview, data.item.imagem_url);
            }
            
            const modal = document.getElementById('itemModal');
            if (modal) modal.style.display = 'block';
        } else {
            mostrarToast(data.error || 'Não foi possível carregar esta pergunta.', true);
        }
    } catch {
        mostrarToast('Não foi possível carregar esta pergunta. Tente novamente.', true);
    }
};

window.salvarItem = async function() {
    const id = document.getElementById('itemId').value;
    const tipoEquipamentoId = document.getElementById('tipoEquipamentoId').value;
    const secao = document.getElementById('secao').value;
    const pergunta = document.getElementById('pergunta').value;
    const tipoResposta = document.getElementById('tipo_resposta').value;
    const detalhamento = document.getElementById('detalhamento').value;
    const ordem = document.getElementById('ordem').value;
    const obrigatorio = document.getElementById('obrigatorio').checked;
    const imagem = document.getElementById('imagem_descritiva').files[0];
    
    if (!pergunta || pergunta.trim() === '') {
        mostrarToast('A pergunta é obrigatória.', true);
        document.getElementById('pergunta').focus();
        return;
    }
    
    const formData = new FormData();
    formData.append('tipo_equipamento_id', tipoEquipamentoId);
    formData.append('secao_id', secao);
    formData.append('pergunta', pergunta);
    formData.append('tipo_resposta', tipoResposta);
    formData.append('detalhamento', detalhamento);
    formData.append('ordem', ordem);
    formData.append('obrigatorio', obrigatorio);
    if (imagem) formData.append('imagem_descritiva', imagem);
    
    const submitBtn = document.querySelector('#itemForm button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Salvando...';
    submitBtn.disabled = true;
    
    try {
        let url, method;
        if (id) {
            url = `/api/checklist-itens/${id}/editar/`;
            method = 'POST';
        } else {
            url = '/api/checklist-itens/criar/';
            method = 'POST';
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData
        });
        if (!response.ok) throw new Error('request_failed');
        
        const data = await response.json();
        
        if (data.success) {
            mostrarToast(data.message || 'Pergunta salva com sucesso.');
            fecharModalItem();
            location.reload();
        } else {
            mostrarToast(data.error || 'Erro ao salvar pergunta.', true);
        }
    } catch {
        mostrarToast('Erro ao salvar pergunta. Tente novamente.', true);
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
};

window.abrirModalExcluirItem = function(id) {
    itemParaExcluir = id;
    const modal = document.getElementById('excluirItemModal');
    if (modal) modal.style.display = 'block';
};

window.confirmarExcluirItem = async function() {
    if (!itemParaExcluir) return;
    
    const confirmBtn = document.querySelector('#excluirItemModal .btn-danger');
    const originalText = confirmBtn.innerHTML;
    confirmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Excluindo...';
    confirmBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/checklist-itens/${itemParaExcluir}/excluir/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        if (!response.ok) throw new Error('request_failed');
        
        const data = await response.json();
        
        if (data.success) {
            mostrarToast(data.message || 'Pergunta excluída com sucesso.');
            fecharModalExcluirItem();
            location.reload();
        } else {
            mostrarToast(data.error || 'Erro ao excluir pergunta.', true);
        }
    } catch {
        mostrarToast('Erro ao excluir pergunta. Tente novamente.', true);
    } finally {
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
    }
};

window.fecharModalItem = function() {
    const modal = document.getElementById('itemModal');
    if (modal) modal.style.display = 'none';
};

window.fecharModalExcluirItem = function() {
    const modal = document.getElementById('excluirItemModal');
    if (modal) modal.style.display = 'none';
    itemParaExcluir = null;
};

function getCookie(name) {
    if (name === 'csrftoken' && typeof CSRF_TOKEN !== 'undefined' && CSRF_TOKEN) {
        return CSRF_TOKEN;
    }

    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function renderImagePreview(preview, src) {
    preview.textContent = '';
    const img = document.createElement('img');
    img.src = src;
    img.alt = 'Preview da imagem';
    img.style.maxWidth = '200px';
    img.style.borderRadius = '8px';
    preview.appendChild(img);
    preview.style.display = 'block';
}

function mostrarToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `checklist-toast ${isError ? 'toast-error' : 'toast-success'}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 180);
    }, 2600);
}
