document.addEventListener('DOMContentLoaded', function () {
    const fotoInput = document.getElementById('id_foto');
    const photoPreview = document.getElementById('photoPreview');
    const grupoSelect = document.getElementById('id_grupo');
    const tipoEquipamento = document.getElementById('id_tipo_equipamento');
    const predioSelect = document.getElementById('id_predio');
    const departamentoSelect = document.getElementById('id_departamento');
    const inspectionBox = document.getElementById('inspectionBox');
    const inspectionTitle = document.getElementById('inspectionTitle');
    const inspectionSummary = document.getElementById('inspectionSummary');
    const inspectionServices = document.getElementById('inspectionServices');
    const genericExpirationFields = document.getElementById('genericExpirationFields');
    const extinguisherExpirationFields = document.getElementById('extinguisherExpirationFields');
    const dataVencimento = document.getElementById('id_data_vencimento');
    const vencimentoCarga = document.getElementById('id_vencimento_carga');
    const vencimentoTesteHidrostatico = document.getElementById('id_vencimento_teste_hidrostatico');
    const vencimentoRadios = document.querySelectorAll('input[name="possui_vencimento"]');

    const PREVIEW_PADRAO = `
        <i class="fa-solid fa-camera"></i>
        <p>Clique ou arraste a foto do item aqui</p>
        <small>(.jpeg, .jpg, .png, .gif)</small>
    `;

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    }

    function resetarPreviewFoto() {
        if (!photoPreview) return;
        photoPreview.innerHTML = PREVIEW_PADRAO;
    }

    function mostrarPreviewFoto(file) {
        if (!photoPreview || !file) return;

        const reader = new FileReader();
        reader.onload = function (event) {
            photoPreview.innerHTML = `
                <img src="${event.target.result}" class="preview-image" alt="Preview da foto">
                <p class="preview-text">Clique para trocar a foto</p>
            `;
        };
        reader.readAsDataURL(file);
    }

    function validarImagem(file) {
        if (!file) return false;

        const tiposValidos = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        const tamanhoMaximo = 5 * 1024 * 1024;

        if (!tiposValidos.includes(file.type)) {
            alert('Por favor, selecione uma imagem válida (JPEG, PNG ou GIF).');
            return false;
        }

        if (file.size > tamanhoMaximo) {
            alert('A imagem deve ter no máximo 5MB.');
            return false;
        }

        return true;
    }

    function resetarInspecao() {
        if (inspectionBox) {
            inspectionBox.style.display = 'none';
        }

        if (inspectionTitle) {
            inspectionTitle.textContent = 'INSPEÇÃO';
        }

        if (inspectionSummary) {
            inspectionSummary.innerHTML = '';
        }

        if (inspectionServices) {
            inspectionServices.innerHTML = '';
        }
    }

    function preencherSelectDepartamentos(departamentos, departamentoSelecionado = '') {
        if (!departamentoSelect) return;

        departamentoSelect.innerHTML = '<option value="">Selecione um departamento</option>';

        if (!Array.isArray(departamentos) || departamentos.length === 0) {
            return;
        }

        departamentos.forEach((depto) => {
            const option = document.createElement('option');
            option.value = depto.id;
            option.textContent = depto.nome;

            if (String(depto.id) === String(departamentoSelecionado)) {
                option.selected = true;
            }

            departamentoSelect.appendChild(option);
        });
    }

    async function carregarDepartamentosPorPredio(predioId, departamentoSelecionado = '') {
        if (!departamentoSelect) return;

        departamentoSelect.innerHTML = '<option value="">Carregando departamentos...</option>';

        if (!predioId) {
            departamentoSelect.innerHTML = '<option value="">Selecione um departamento</option>';
            return;
        }

        try {
            const response = await fetch(`/api/departamentos-por-predio/?predio_id=${predioId}`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar departamentos.');
            }

            preencherSelectDepartamentos(data.data, departamentoSelecionado);

            if (!Array.isArray(data.data) || data.data.length === 0) {
                departamentoSelect.innerHTML = '<option value="">Nenhum departamento encontrado</option>';
            }
        } catch (error) {
            console.error('Erro ao carregar departamentos:', error);
            departamentoSelect.innerHTML = '<option value="">Erro ao carregar departamentos</option>';
        }
    }

    function resetarTipos(options = {}) {
        if (!tipoEquipamento) return;

        tipoEquipamento.innerHTML = '<option value="">Selecione um tipo de equipamento</option>';
        tipoEquipamento.disabled = !grupoSelect || !grupoSelect.value;
        resetarInspecao();
        atualizarCamposVencimento(options);
    }

    function preencherSelectTipos(tipos, tipoSelecionado = '') {
        if (!tipoEquipamento) return;

        tipoEquipamento.innerHTML = '<option value="">Selecione um tipo de equipamento</option>';

        if (!Array.isArray(tipos) || tipos.length === 0) {
            tipoEquipamento.innerHTML = '<option value="">Nenhum tipo encontrado para este grupo</option>';
            tipoEquipamento.disabled = true;
            return;
        }

        tipos.forEach((tipo) => {
            const option = document.createElement('option');
            option.value = tipo.id;
            option.textContent = tipo.nome;
            option.dataset.grupoId = tipo.grupo_id || '';
            option.dataset.grupoNome = tipo.grupo_nome || '';
            option.dataset.isExtintor = String(tipo.is_extintor === true);

            if (String(tipo.id) === String(tipoSelecionado)) {
                option.selected = true;
            }

            tipoEquipamento.appendChild(option);
        });

        tipoEquipamento.disabled = false;
    }

    async function carregarTiposPorGrupo(grupoId, tipoSelecionado = '', options = {}) {
        if (!tipoEquipamento) return;

        resetarTipos(options);

        if (!grupoId) return;

        tipoEquipamento.innerHTML = '<option value="">Carregando tipos...</option>';
        tipoEquipamento.disabled = true;

        try {
            const params = new URLSearchParams({
                grupo_id: grupoId,
                status: 'ativo',
                rows: 500,
                sort: 'asc'
            });
            const response = await fetch(`/api/tipos-equipamento/?${params.toString()}`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar tipos de equipamento.');
            }

            preencherSelectTipos(data.data, tipoSelecionado);

            if (tipoSelecionado && tipoEquipamento.value) {
                await carregarDetalhesPorTipo(tipoEquipamento.value, options);
            }
        } catch (error) {
            console.error('Erro ao carregar tipos por grupo:', error);
            tipoEquipamento.innerHTML = '<option value="">Erro ao carregar tipos</option>';
            tipoEquipamento.disabled = true;
        }
    }

    function renderizarResumoInspecao(data) {
        if (!inspectionSummary) return;

        const totalServicos = Number(data.total_servicos || 0);
        const totalItens = Number(data.total_itens || 0);
        const periodicidade = data.periodicidade_nome || 'Sem periodicidade definida';

        inspectionSummary.innerHTML = `
            <div class="inspection-stat">
                <span>Periodicidade base</span>
                <strong>${escapeHtml(periodicidade)}</strong>
            </div>
            <div class="inspection-stat">
                <span>Serviços configurados</span>
                <strong>${totalServicos}</strong>
            </div>
            <div class="inspection-stat">
                <span>Itens de checklist</span>
                <strong>${totalItens}</strong>
            </div>
        `;
    }

    function renderizarServicosInspecao(servicos) {
        if (!inspectionServices) return;

        if (!Array.isArray(servicos) || servicos.length === 0) {
            inspectionServices.innerHTML = `
                <div class="inspection-empty">
                    Nenhuma inspeção ou checklist configurado para este tipo.
                </div>
            `;
            return;
        }

        inspectionServices.innerHTML = servicos.map((servico) => `
            <div class="inspection-service-card">
                <div>
                    <strong>${escapeHtml(servico.tipo_servico_nome || 'Serviço')}</strong>
                    <span>${escapeHtml(servico.periodicidade_nome || 'Sem periodicidade')}</span>
                </div>
                <small>${Number(servico.itens_count || 0)} itens</small>
            </div>
        `).join('');
    }

    async function carregarDetalhesPorTipo(tipoId, options = {}) {
        resetarInspecao();
        atualizarCamposVencimento(options);

        if (!tipoId) return;

        try {
            const response = await fetch(`/api/tipo-equipamento-detalhe/?tipo_id=${tipoId}`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar detalhes do tipo de equipamento.');
            }

            if (inspectionBox) {
                inspectionBox.style.display = 'block';
            }

            if (inspectionTitle) {
                inspectionTitle.textContent = `INSPEÇÃO - ${String(data.tipo_equipamento || '').toUpperCase()}`;
            }

            renderizarResumoInspecao(data);
            renderizarServicosInspecao(data.servicos || []);
            atualizarCamposVencimento({ preservarValores: true });
        } catch (error) {
            console.error('Erro ao carregar detalhes do tipo:', error);
            resetarInspecao();
        }
    }

    function equipamentoPossuiVencimento() {
        const selecionado = document.querySelector('input[name="possui_vencimento"]:checked');
        if (!selecionado) return false;
        return ['true', 'True', '1'].includes(selecionado.value);
    }

    function tipoSelecionadoEhExtintor() {
        if (!tipoEquipamento || !tipoEquipamento.value) return false;

        const option = tipoEquipamento.options[tipoEquipamento.selectedIndex];
        if (option && option.dataset.isExtintor) {
            return option.dataset.isExtintor === 'true';
        }

        return option ? option.textContent.toLowerCase().includes('extintor') : false;
    }

    function limparCampo(input) {
        if (input) input.value = '';
    }

    function atualizarCamposVencimento(options = {}) {
        const preservarValores = options.preservarValores === true;
        const possuiVencimento = equipamentoPossuiVencimento();
        const isExtintor = tipoSelecionadoEhExtintor();

        if (genericExpirationFields) {
            genericExpirationFields.style.display = possuiVencimento && !isExtintor ? 'grid' : 'none';
        }

        if (extinguisherExpirationFields) {
            extinguisherExpirationFields.style.display = possuiVencimento && isExtintor ? 'grid' : 'none';
        }

        if (preservarValores) return;

        if (!possuiVencimento) {
            limparCampo(dataVencimento);
            limparCampo(vencimentoCarga);
            limparCampo(vencimentoTesteHidrostatico);
        } else if (isExtintor) {
            limparCampo(dataVencimento);
        } else {
            limparCampo(vencimentoCarga);
            limparCampo(vencimentoTesteHidrostatico);
        }
    }

    if (fotoInput) {
        fotoInput.addEventListener('change', function (event) {
            const file = event.target.files[0];

            if (!file) {
                resetarPreviewFoto();
                return;
            }

            if (!validarImagem(file)) {
                fotoInput.value = '';
                resetarPreviewFoto();
                return;
            }

            mostrarPreviewFoto(file);
        });
    }

    if (predioSelect && departamentoSelect) {
        predioSelect.addEventListener('change', async function () {
            await carregarDepartamentosPorPredio(this.value);
        });
    }

    if (grupoSelect && tipoEquipamento) {
        grupoSelect.addEventListener('change', async function () {
            await carregarTiposPorGrupo(this.value);
        });
    }

    if (tipoEquipamento) {
        tipoEquipamento.addEventListener('change', async function () {
            await carregarDetalhesPorTipo(this.value);
        });
    }

    vencimentoRadios.forEach((radio) => {
        radio.addEventListener('change', function () {
            atualizarCamposVencimento();
        });
    });

    if (predioSelect && departamentoSelect && predioSelect.value) {
        const departamentoAtual = departamentoSelect.value;
        carregarDepartamentosPorPredio(predioSelect.value, departamentoAtual);
    }

    if (grupoSelect && tipoEquipamento && grupoSelect.value) {
        const tipoAtual = tipoEquipamento.value;
        carregarTiposPorGrupo(grupoSelect.value, tipoAtual, { preservarValores: true });
    } else {
        resetarTipos();
    }

    atualizarCamposVencimento({ preservarValores: true });
});
