// editor_tipo_equipamento.js - Notchfire

const tipoEquipamentoId = typeof TIPO_EQUIPAMENTO_ID !== 'undefined'
  ? TIPO_EQUIPAMENTO_ID
  : parseInt(window.location.pathname.split('/').filter(Boolean)[1], 10);

let servicoAtualId = null;
let servicoEditMode = false;
let servicoAtualAtivo = true;
let confirmResolver = null;
let checklistDraft = [];
let nextDraftSecaoId = -1;
let nextDraftItemId = -1;

document.addEventListener('DOMContentLoaded', () => {
  configurarModaisGlobais();
  configurarFormImagem();
  configurarBuscaServicos();
  configurarBotoesServicoModal();
  configurarPreviewPergunta();
});

function configurarBotoesServicoModal() {
  const btnExcluir = document.getElementById('btnExcluirServico');
  const btnDesabilitar = document.getElementById('btnDesabilitarServico');
  const btnSalvar = document.getElementById('btnSalvarServico');

  if (btnExcluir) {
    btnExcluir.addEventListener('click', () => {
      if (servicoAtualId) excluirServico(servicoAtualId);
    });
  }

  if (btnDesabilitar) {
    btnDesabilitar.addEventListener('click', alternarServicoAtivo);
  }

  if (btnSalvar) {
    btnSalvar.onclick = salvarServicoModal;
  }
}

function configurarModaisGlobais() {
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        if (overlay.id === 'confirmModal') resolverConfirmacao(false);
        else closeModal(overlay.id);
      }
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (document.getElementById('confirmModal')?.classList.contains('open')) {
        resolverConfirmacao(false);
        return;
      }
      document.querySelectorAll('.modal-overlay.open').forEach((modal) => {
        closeModal(modal.id);
      });
    }
  });
}

function configurarBuscaServicos() {
  const input = document.getElementById('servicoSearch');
  const list = document.getElementById('servicosList');
  if (!input || !list) return;

  const empty = document.createElement('div');
  empty.className = 'empty-state no-service-results';
  empty.innerHTML = `
    <i class="fa-solid fa-search"></i>
    <h3>Nenhum checklist encontrado</h3>
    <p>A busca não encontrou checklists configurados.</p>
  `;
  list.appendChild(empty);

  input.addEventListener('input', () => {
    const term = normalizarTexto(input.value);
    const rows = [...list.querySelectorAll('.servico-row')];
    let visible = 0;

    rows.forEach((row) => {
      const haystack = normalizarTexto(row.dataset.search || row.textContent);
      const match = !term || haystack.includes(term);
      row.style.display = match ? '' : 'none';
      if (match) visible += 1;
    });

    empty.style.display = visible === 0 && rows.length > 0 ? 'block' : 'none';
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;

  modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  const focusable = modal.querySelector('input, select, textarea, button');
  if (focusable && !focusable.classList.contains('modal-close')) {
    setTimeout(() => focusable.focus(), 80);
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;

  modal.classList.remove('open');

  if (!document.querySelector('.modal-overlay.open')) {
    document.body.style.overflow = '';
  }
}

function switchTab(btn) {
  const tabId = btn.dataset.tab;
  const modal = btn.closest('.modal-box');

  modal.querySelectorAll('.tab-btn').forEach((button) => button.classList.remove('active'));
  modal.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.remove('active'));

  btn.classList.add('active');
  const panel = document.getElementById(tabId);
  if (panel) panel.classList.add('active');
}

function execCmd(cmd) {
  const editor = document.getElementById('itemDetalhamento');
  if (!editor) return;
  editor.focus();
  document.execCommand(cmd, false, null);
}

async function salvarTipoEquipamentoInfo() {
  const nome = getValue('editNome').trim();
  const grupoId = getValue('editGrupo');
  const descricao = getValue('editDescricao');
  const status = getValue('editStatus') === 'true';
  const periodicidadeId = getValue('editPeriodicidade') || null;

  if (!nome) {
    mostrarToast('O nome do tipo de equipamento é obrigatório.', true);
    return;
  }

  if (!grupoId) {
    mostrarToast('Selecione um grupo.', true);
    return;
  }

  try {
    const data = await fetchJson(`/api/tipos-equipamento/${tipoEquipamentoId}/info/`, {
      method: 'POST',
      body: {
        nome,
        grupo_id: parseInt(grupoId, 10),
        periodicidade_id: periodicidadeId ? parseInt(periodicidadeId, 10) : null,
        descricao,
        status
      }
    });

    setText('displayNome', nome);
    setText('displayDescricao', descricao || 'Nenhuma descrição');
    setText('displayGrupo', textoSelecionado('editGrupo') || '—');
    setText('displayPeriodicidade', textoSelecionado('editPeriodicidade') || 'Nenhuma');

    const subtitle = document.querySelector('.editor-subtitle');
    if (subtitle) {
      const periodicidade = textoSelecionado('editPeriodicidade');
      subtitle.textContent = periodicidade
        ? `${textoSelecionado('editGrupo')} · ${periodicidade}`
        : textoSelecionado('editGrupo');
    }

    closeModal('editInfoModal');
    mostrarToast(data.message || 'Informações salvas com sucesso.');
  } catch (error) {
    mostrarToast(error.message, true);
  }
}

async function abrirModalServico(id) {
  servicoAtualId = id;
  servicoEditMode = false;

  const btnSalvar = document.getElementById('btnSalvarServico');
  if (btnSalvar) btnSalvar.onclick = salvarServicoModal;

  _setServicoEditMode(false);
  renderChecklistLoading();
  openModal('servicoModal');

  try {
    const data = await fetchJson(`/api/tipos-equipamento/servicos/${id}/`);
    preencherServicoModal(data.servico);
  } catch (error) {
    mostrarToast(error.message, true);
    closeModal('servicoModal');
  }
}

function preencherServicoModal(servico) {
  servicoAtualAtivo = servico.ativo !== false;

  const title = document.getElementById('servicoModalTitle');
  if (title) {
    title.innerHTML = `<i class="fa-solid fa-list-check"></i> ${escapeHtml(servico.tipo_servico_nome || 'Checklist')}`;
  }

  setText('viewTipoServico', servico.tipo_servico_nome || '—');
  setText('viewPeriodicidade', servico.periodicidade_nome || '—');
  setText('modalTotalSecoes', servico.secoes_count || 0);
  setText('modalTotalPerguntas', servico.itens_count || 0);
  setText('modalStatusServico', servicoAtualAtivo ? 'Ativo' : 'Inativo');

  setValue('modalTipoServico', servico.tipo_servico_id || '');
  setValue('modalPeriodicidade', servico.periodicidade_id || '');
  setChecked('modalObrigatorio', servico.obrigatorio);
  setChecked('modalVencimentoFinalMes', servico.vencimento_final_mes);
  setChecked('modalHabilitarAssinatura', servico.habilitar_assinatura);
  setChecked('modalAssinaturaObrigatoria', servico.assinatura_obrigatoria);
  setChecked('modalAcoesObrigatorias', servico.acoes_obrigatorias);
  setChecked('modalPermitirMassa', servico.permitir_servicos_massa);

  toggleAssinaturaOpcoes();
  atualizarBotaoStatusServico();
  atualizarAcoesChecklistModal();
  resetChecklistDraft(servico.secoes || []);
}

function resetChecklistDraft(secoes = []) {
  checklistDraft = (secoes || []).map((secao, secaoIndex) => {
    const secaoId = secao.id || gerarDraftSecaoId();
    return {
      id: secaoId,
      nome: secao.nome || '',
      descricao: secao.descricao || '',
      ordem: Number.isFinite(Number(secao.ordem)) ? Number(secao.ordem) : secaoIndex,
      itens: (secao.itens || []).map((item, itemIndex) => ({
        id: item.id || gerarDraftItemId(),
        secao_id: secaoId,
        pergunta: item.pergunta || '',
        tipo_resposta: item.tipo_resposta || 'sim_nao',
        detalhamento: item.detalhamento || '',
        ordem: Number.isFinite(Number(item.ordem)) ? Number(item.ordem) : itemIndex,
        obrigatorio: item.obrigatorio !== false,
        imagem: item.imagem || item.imagem_url || ''
      }))
    };
  });

  renderChecklist(checklistDraft);
}

function gerarDraftSecaoId() {
  const id = nextDraftSecaoId;
  nextDraftSecaoId -= 1;
  return id;
}

function gerarDraftItemId() {
  const id = nextDraftItemId;
  nextDraftItemId -= 1;
  return id;
}

function serializarChecklistDraft() {
  return checklistDraft.map((secao, secaoIndex) => ({
    id: idPersistidoOuNull(secao.id),
    nome: secao.nome,
    descricao: secao.descricao || '',
    ordem: Number.isFinite(Number(secao.ordem)) ? Number(secao.ordem) : secaoIndex,
    itens: (secao.itens || []).map((item, itemIndex) => ({
      id: idPersistidoOuNull(item.id),
      pergunta: item.pergunta,
      tipo_resposta: item.tipo_resposta || 'sim_nao',
      detalhamento: item.detalhamento || '',
      ordem: Number.isFinite(Number(item.ordem)) ? Number(item.ordem) : itemIndex,
      obrigatorio: item.obrigatorio !== false
    }))
  }));
}

function idPersistidoOuNull(id) {
  const parsed = parseInt(id, 10);
  return parsed > 0 ? parsed : null;
}

function encontrarSecaoDraft(secaoId) {
  return checklistDraft.find((secao) => String(secao.id) === String(secaoId));
}

function encontrarItemDraft(itemId) {
  for (const secao of checklistDraft) {
    const index = (secao.itens || []).findIndex((item) => String(item.id) === String(itemId));
    if (index >= 0) {
      return { secao, item: secao.itens[index], index };
    }
  }
  return null;
}

function removerItemDraft(itemId) {
  const encontrado = encontrarItemDraft(itemId);
  if (!encontrado) return false;
  encontrado.secao.itens.splice(encontrado.index, 1);
  return true;
}

function atualizarAcoesChecklistModal() {
  const btnExcluir = document.getElementById('btnExcluirServico');
  if (btnExcluir) btnExcluir.style.display = servicoAtualId ? '' : 'none';
}

function toggleServicoEditMode() {
  servicoEditMode = !servicoEditMode;
  _setServicoEditMode(servicoEditMode);
}

function _setServicoEditMode(edit) {
  const view = document.getElementById('servicoCamposView');
  const form = document.getElementById('servicoCamposEdit');
  if (view) view.style.display = edit ? 'none' : 'block';
  if (form) form.style.display = edit ? 'block' : 'none';
}

function toggleAssinaturaOpcoes() {
  const checked = !!document.getElementById('modalHabilitarAssinatura')?.checked;
  const wrapper = document.getElementById('modalAssinaturaOpcoes');
  if (wrapper) wrapper.style.display = checked ? 'block' : 'none';
  if (!checked) setChecked('modalAssinaturaObrigatoria', false);
}

function alternarServicoAtivo() {
  servicoAtualAtivo = !servicoAtualAtivo;
  setText('modalStatusServico', servicoAtualAtivo ? 'Ativo' : 'Inativo');
  atualizarBotaoStatusServico();
}

function atualizarBotaoStatusServico() {
  const btn = document.getElementById('btnDesabilitarServico');
  if (!btn) return;

  btn.innerHTML = servicoAtualAtivo
    ? '<i class="fa-solid fa-ban"></i> Desabilitar'
    : '<i class="fa-solid fa-circle-check"></i> Habilitar';
}

async function salvarServicoModal() {
  if (!servicoAtualId) return;

  const tipoServico = getValue('modalTipoServico');
  const periodicidade = getValue('modalPeriodicidade');

  if (!tipoServico || !periodicidade) {
    mostrarToast('Selecione o checklist e a periodicidade.', true);
    return;
  }

  try {
    const data = await fetchJson(`/api/tipos-equipamento/servicos/${servicoAtualId}/editar/`, {
      method: 'PUT',
      body: montarPayloadServico({
        ativo: servicoAtualAtivo,
        secoes: serializarChecklistDraft()
      })
    });

    mostrarToast(data.message || 'Checklist salvo com sucesso.');
    setTimeout(() => window.location.reload(), 650);
  } catch (error) {
    mostrarToast(error.message, true);
  }
}

async function apagarChecklist() {
  const ok = await confirmarAcao({
    title: 'Apagar checklist',
    message: 'Todas as seções e perguntas deste checklist serão removidas do rascunho.',
    actionText: 'Apagar checklist'
  });

  if (!ok) return;

  resetChecklistDraft([]);
  mostrarToast('Checklist limpo. Clique em Salvar Checklist para aplicar.');
}

function abrirModalNovoServico() {
  servicoAtualId = null;
  servicoAtualAtivo = true;
  servicoEditMode = true;

  setValue('modalTipoServico', '');
  setValue('modalPeriodicidade', '');
  setChecked('modalObrigatorio', true);
  setChecked('modalVencimentoFinalMes', false);
  setChecked('modalHabilitarAssinatura', false);
  setChecked('modalAssinaturaObrigatoria', false);
  setChecked('modalAcoesObrigatorias', false);
  setChecked('modalPermitirMassa', false);
  toggleAssinaturaOpcoes();

  const title = document.getElementById('servicoModalTitle');
  if (title) title.innerHTML = '<i class="fa-solid fa-plus"></i> Novo Checklist';

  setText('viewTipoServico', '—');
  setText('viewPeriodicidade', '—');
  setText('modalTotalSecoes', 0);
  setText('modalTotalPerguntas', 0);
  setText('modalStatusServico', 'Ativo');
  atualizarBotaoStatusServico();
  atualizarAcoesChecklistModal();
  _setServicoEditMode(true);
  resetChecklistDraft([]);

  const btnSalvar = document.getElementById('btnSalvarServico');
  if (btnSalvar) btnSalvar.onclick = criarServico;

  openModal('servicoModal');
}

async function criarServico() {
  const tipoServico = getValue('modalTipoServico');
  const periodicidade = getValue('modalPeriodicidade');

  if (!tipoServico || !periodicidade) {
    mostrarToast('Selecione o checklist e a periodicidade.', true);
    return;
  }

  try {
    const data = await fetchJson('/api/tipos-equipamento/servicos/criar/', {
      method: 'POST',
      body: montarPayloadServico({
        ativo: servicoAtualAtivo,
        secoes: serializarChecklistDraft()
      })
    });

    mostrarToast(data.message || 'Checklist criado com sucesso.');
    setTimeout(() => window.location.reload(), 650);
  } catch (error) {
    mostrarToast(error.message, true);
  }
}

function montarPayloadServico(extra = {}) {
  return {
    tipo_equipamento_id: tipoEquipamentoId,
    tipo_servico_id: parseInt(getValue('modalTipoServico'), 10) || null,
    periodicidade_id: parseInt(getValue('modalPeriodicidade'), 10) || null,
    obrigatorio: !!document.getElementById('modalObrigatorio')?.checked,
    vencimento_final_mes: !!document.getElementById('modalVencimentoFinalMes')?.checked,
    habilitar_assinatura: !!document.getElementById('modalHabilitarAssinatura')?.checked,
    assinatura_obrigatoria: !!document.getElementById('modalAssinaturaObrigatoria')?.checked,
    acoes_obrigatorias: !!document.getElementById('modalAcoesObrigatorias')?.checked,
    permitir_servicos_massa: !!document.getElementById('modalPermitirMassa')?.checked,
    ...extra
  };
}

function renderChecklistLoading() {
  const container = document.getElementById('checklistContent');
  if (!container) return;
  container.innerHTML = `
    <div class="checklist-empty">
      <i class="fa-solid fa-spinner fa-spin" style="display:block;font-size:28px;margin-bottom:8px;color:var(--laranja-nothfire)"></i>
      Carregando checklist...
    </div>
  `;
}

function renderChecklist(secoes) {
  const container = document.getElementById('checklistContent');
  if (!container) return;

  const listaSecoes = secoes || [];
  const totalPerguntas = listaSecoes.reduce((total, secao) => total + ((secao.itens || []).length), 0);

  setText('modalTotalSecoes', listaSecoes.length);
  setText('modalTotalPerguntas', totalPerguntas);
  atualizarSelectSecoes(listaSecoes);

  if (listaSecoes.length === 0) {
    container.innerHTML = `
      <div class="checklist-empty">
        <i class="fa-solid fa-clipboard" style="display:block;font-size:28px;margin-bottom:8px;opacity:.35;color:var(--texto-suave)"></i>
        Nenhuma seção criada.
      </div>
    `;
    return;
  }

  container.innerHTML = listaSecoes.map((secao) => `
    <div class="checklist-section-block" data-secao-id="${secao.id}">
      <div class="checklist-section-header response-style">
        <div>
          <div class="checklist-section-name">
            <i class="fa-solid fa-list-check"></i>
            ${escapeHtml(secao.nome)}
          </div>
          <span class="section-preview-label">Modelo da seção no checklist</span>
        </div>
        <div class="checklist-section-actions">
          <span class="section-score-preview">100.00%</span>
          <button class="icon-btn btn-sm" onclick="editarSecao(${secao.id}, '${escapeAttr(secao.nome)}', '${escapeAttr(secao.descricao || '')}')" title="Editar seção">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button class="icon-btn icon-btn-danger btn-sm" onclick="excluirSecao(${secao.id})" title="Excluir seção">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>

      ${secao.descricao ? `<div class="checklist-section-desc">${escapeHtml(secao.descricao)}</div>` : ''}

      <div class="checklist-section-tools">
        <button class="btn btn-sm btn-outline" onclick="abrirModalCriarItem(${secao.id}, '${escapeAttr(secao.nome)}')">
          <i class="fa-solid fa-plus"></i> Criar Pergunta
        </button>
      </div>

      ${(secao.itens && secao.itens.length > 0) ? secao.itens.map((item, index) => `
        <div class="service-check-item" data-item-id="${item.id}">
          ${item.imagem
            ? `<div class="item-thumb"><img src="${escapeHtml(item.imagem)}" alt=""></div>`
            : `<div class="check-question-marker"><i class="fa-solid fa-check"></i></div>`}
          <div class="service-check-main">
            <p>${index + 1} - ${escapeHtml(item.pergunta)}</p>
            <div class="service-answer-options">
              ${renderRespostaModelo(item.tipo_resposta)}
            </div>
            <small>${escapeHtml(rotuloTipoResposta(item.tipo_resposta))}${item.obrigatorio ? ' · Obrigatória' : ''}${item.detalhamento ? ' · Com detalhamento' : ''}</small>
          </div>
          <button type="button" class="service-action-preview" disabled>Adicionar ação</button>
          <div class="item-actions">
            <button class="icon-btn btn-sm" onclick="editarItem(${item.id}, ${secao.id}, '${escapeAttr(item.pergunta)}', '${escapeAttr(item.tipo_resposta)}', '${escapeAttr(item.detalhamento || '')}', ${item.ordem || 0}, ${item.obrigatorio ? 'true' : 'false'})" title="Editar pergunta">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="icon-btn icon-btn-danger btn-sm" onclick="excluirItem(${item.id})" title="Excluir pergunta">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      `).join('') : `<div class="checklist-empty">Nenhuma pergunta nesta seção</div>`}

      <div class="add-question-row" onclick="abrirModalCriarItem(${secao.id}, '${escapeAttr(secao.nome)}')">
        <i class="fa-solid fa-plus"></i> Adicionar pergunta
      </div>
    </div>
  `).join('');
}

function abrirModalCriarSecao(servicoId) {
  setValue('secaoId', '');
  setValue('secaoServicoId', servicoId || servicoAtualId || '');
  setValue('secaoNome', '');
  setValue('secaoDescricao', '');
  const title = document.getElementById('secaoModalTitle');
  if (title) title.innerHTML = '<i class="fa-solid fa-folder-plus"></i> Nova Seção';
  openModal('secaoModal');
}

function editarSecao(id, nome, descricao) {
  setValue('secaoId', id);
  setValue('secaoNome', nome || '');
  setValue('secaoDescricao', descricao || '');
  const title = document.getElementById('secaoModalTitle');
  if (title) title.innerHTML = '<i class="fa-solid fa-folder"></i> Editar Seção';
  openModal('secaoModal');
}

async function salvarSecao() {
  const nome = getValue('secaoNome').trim();
  const secaoId = getValue('secaoId');
  const descricao = getValue('secaoDescricao');

  if (!nome) {
    mostrarToast('Informe o nome da seção.', true);
    return;
  }

  if (secaoId) {
    const secao = encontrarSecaoDraft(secaoId);
    if (!secao) {
      mostrarToast('Seção não encontrada no checklist.', true);
      return;
    }

    secao.nome = nome;
    secao.descricao = descricao;
  } else {
    checklistDraft.push({
      id: gerarDraftSecaoId(),
      nome,
      descricao,
      ordem: checklistDraft.length,
      itens: []
    });
  }

  closeModal('secaoModal');
  renderChecklist(checklistDraft);
  mostrarToast('Seção salva no checklist. Clique em Salvar Checklist para gravar.');
}

async function excluirSecao(id) {
  const ok = await confirmarAcao({
    title: 'Excluir seção',
    message: 'A seção e todas as perguntas dentro dela serão removidas do rascunho.',
    actionText: 'Excluir seção'
  });

  if (!ok) return;

  checklistDraft = checklistDraft.filter((secao) => String(secao.id) !== String(id));
  renderChecklist(checklistDraft);
  mostrarToast('Seção removida. Clique em Salvar Checklist para aplicar.');
}

function abrirModalCriarItem(secaoId, secaoNome) {
  setValue('itemId', '');
  setValue('itemServicoId', servicoAtualId || '');
  setValue('itemPergunta', '');
  setValue('itemTipoResposta', 'sim_nao');
  setValue('itemOrdem', 0);
  setChecked('itemObrigatorio', true);

  const detalhamento = document.getElementById('itemDetalhamento');
  if (detalhamento) detalhamento.innerHTML = '';

  garantirOpcaoSecao(secaoId, secaoNome);
  if (secaoId) setValue('itemSeccao', secaoId);

  const title = document.getElementById('itemModalTitle');
  if (title) title.innerHTML = '<i class="fa-solid fa-circle-question"></i> Nova Pergunta';
  setText('itemModalSubtitle', secaoNome ? `Seção: ${secaoNome}` : 'Seção: —');
  resetItemTabs();
  atualizarPreviewPergunta();
  openModal('itemModal');
}

function abrirModalCriarItemPorServico(servicoId) {
  abrirModalCriarItem(null, null);
  setValue('itemServicoId', servicoId);
}

function editarItem(id, secaoId, pergunta, tipoResposta, detalhamento, ordem, obrigatorio) {
  setValue('itemId', id);
  setValue('itemSeccao', secaoId);
  setValue('itemPergunta', pergunta || '');
  setValue('itemTipoResposta', tipoResposta || 'sim_nao');
  setValue('itemOrdem', ordem || 0);
  setChecked('itemObrigatorio', obrigatorio === true || obrigatorio === 'true');

  const editor = document.getElementById('itemDetalhamento');
  if (editor) editor.innerHTML = detalhamento || '';

  const title = document.getElementById('itemModalTitle');
  if (title) title.innerHTML = '<i class="fa-solid fa-circle-question"></i> Editar Pergunta';
  atualizarSubtitleSecao();
  resetItemTabs();
  atualizarPreviewPergunta();
  openModal('itemModal');
}

function resetItemTabs() {
  const modal = document.getElementById('itemModal');
  if (!modal) return;
  modal.querySelectorAll('.tab-btn').forEach((button, index) => button.classList.toggle('active', index === 0));
  modal.querySelectorAll('.tab-panel').forEach((panel, index) => panel.classList.toggle('active', index === 0));
}

function atualizarSubtitleSecao() {
  const select = document.getElementById('itemSeccao');
  const texto = select?.options[select.selectedIndex]?.text || '';
  setText('itemModalSubtitle', texto ? `Seção: ${texto}` : 'Seção: —');
  atualizarPreviewPergunta();
}

function configurarPreviewPergunta() {
  ['itemPergunta', 'itemTipoResposta', 'itemObrigatorio'].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    const eventName = element.type === 'checkbox' || element.tagName === 'SELECT' ? 'change' : 'input';
    element.addEventListener(eventName, atualizarPreviewPergunta);
  });
}

function atualizarPreviewPergunta() {
  const pergunta = getValue('itemPergunta').trim() || 'A pergunta aparecerá aqui';
  const tipoResposta = getValue('itemTipoResposta') || 'sim_nao';
  const obrigatorio = !!document.getElementById('itemObrigatorio')?.checked;

  setText('itemPreviewPergunta', `1 - ${pergunta}`);
  setText('itemPreviewObrigatorio', obrigatorio ? 'Obrigatória' : 'Opcional');

  const respostas = document.getElementById('itemPreviewResposta');
  if (respostas) respostas.innerHTML = renderRespostaModelo(tipoResposta);
}

async function salvarItem() {
  const secao = getValue('itemSeccao');
  const pergunta = getValue('itemPergunta').trim();
  const itemId = getValue('itemId');

  if (!secao) {
    mostrarToast('Selecione uma seção.', true);
    return;
  }

  if (!pergunta) {
    mostrarToast('Digite a pergunta.', true);
    return;
  }

  const secaoDestino = encontrarSecaoDraft(secao);
  if (!secaoDestino) {
    mostrarToast('Selecione uma seção válida.', true);
    return;
  }

  const detalhamento = document.getElementById('itemDetalhamento')?.innerHTML || '';
  const itemExistente = itemId ? encontrarItemDraft(itemId) : null;
  const itemPayload = {
    id: itemId || gerarDraftItemId(),
    secao_id: secaoDestino.id,
    pergunta,
    tipo_resposta: getValue('itemTipoResposta') || 'sim_nao',
    detalhamento,
    ordem: parseInt(getValue('itemOrdem'), 10) || 0,
    obrigatorio: !!document.getElementById('itemObrigatorio')?.checked,
    imagem: itemExistente?.item?.imagem || ''
  };

  if (itemExistente) {
    if (String(itemExistente.secao.id) !== String(secaoDestino.id)) {
      itemExistente.secao.itens.splice(itemExistente.index, 1);
      secaoDestino.itens.push(itemPayload);
    } else {
      Object.assign(itemExistente.item, itemPayload);
    }
  } else {
    secaoDestino.itens.push(itemPayload);
  }

  closeModal('itemModal');
  renderChecklist(checklistDraft);
  mostrarToast('Pergunta salva no checklist. Clique em Salvar Checklist para gravar.');
}

async function excluirItem(id) {
  const ok = await confirmarAcao({
    title: 'Excluir pergunta',
    message: 'Esta pergunta será removida do checklist.',
    actionText: 'Excluir pergunta'
  });

  if (!ok) return;

  removerItemDraft(id);
  renderChecklist(checklistDraft);
  mostrarToast('Pergunta removida. Clique em Salvar Checklist para aplicar.');
}

async function recarregarChecklistModal() {
  if (!servicoAtualId) return;

  const data = await fetchJson(`/api/tipos-equipamento/servicos/${servicoAtualId}/`);
  preencherServicoModal(data.servico);
}

async function excluirServico(id) {
  const ok = await confirmarAcao({
    title: 'Excluir checklist',
    message: 'O checklist e todas as seções configuradas nele serão removidos.',
    actionText: 'Excluir checklist'
  });

  if (!ok) return;

  try {
    const data = await fetchJson(`/api/tipos-equipamento/servicos/${id}/excluir/`, { method: 'DELETE' });
    mostrarToast(data.message || 'Checklist excluído com sucesso.');
    setTimeout(() => window.location.reload(), 650);
  } catch (error) {
    mostrarToast(error.message, true);
  }
}

function editarServico(id) {
  abrirModalServico(id);
}

async function excluirTipoEquipamento() {
  const ok = await confirmarAcao({
    title: 'Excluir tipo de equipamento',
    message: 'Este tipo de equipamento será removido permanentemente.',
    actionText: 'Excluir tipo'
  });

  if (!ok) return;

  try {
    const data = await fetchJson(`/api/tipos-equipamento/${tipoEquipamentoId}/excluir/`, { method: 'DELETE' });
    mostrarToast(data.message || 'Tipo de equipamento excluído.');
    setTimeout(() => window.location.href = '/tipos-equipamento/', 650);
  } catch (error) {
    mostrarToast(error.message, true);
  }
}

function abrirModalAdicionarAnexo() {
  mostrarToast('Anexos serão conectados ao armazenamento em uma próxima etapa.');
}

function configurarFormImagem() {
  const area = document.querySelector('.img-upload-area');
  const input = document.getElementById('imgUploadInput');
  if (!area || !input) return;

  area.addEventListener('click', () => input.click());
  input.addEventListener('change', function () {
    if (!this.files || !this.files[0]) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      area.innerHTML = `<img src="${event.target.result}" alt="Preview" style="max-height:160px;border-radius:8px;">`;
    };
    reader.readAsDataURL(this.files[0]);
  });
}

function atualizarSelectSecoes(secoes) {
  const select = document.getElementById('itemSeccao');
  if (!select) return;

  const selected = select.value;
  select.innerHTML = '<option value="">Selecione uma seção...</option>';

  secoes.forEach((secao) => {
    const option = document.createElement('option');
    option.value = secao.id;
    option.textContent = secao.nome;
    select.appendChild(option);
  });

  if (selected) select.value = selected;
}

function garantirOpcaoSecao(secaoId, secaoNome) {
  const select = document.getElementById('itemSeccao');
  if (!select || !secaoId) return;

  if (![...select.options].some((option) => String(option.value) === String(secaoId))) {
    const option = document.createElement('option');
    option.value = secaoId;
    option.textContent = secaoNome || `Seção ${secaoId}`;
    select.appendChild(option);
  }
}

function confirmarAcao({ title = 'Confirmar ação', message = 'Tem certeza?', actionText = 'Confirmar' }) {
  return new Promise((resolve) => {
    confirmResolver = resolve;
    setText('confirmTitle', title);
    setText('confirmMessage', message);
    setText('confirmActionBtn', actionText);
    openModal('confirmModal');
  });
}

function resolverConfirmacao(result) {
  closeModal('confirmModal');
  if (confirmResolver) {
    confirmResolver(result);
    confirmResolver = null;
  }
}

async function fetchJson(url, options = {}) {
  const fetchOptions = {
    method: options.method || 'GET',
    headers: {
      'X-CSRFToken': getCookie('csrftoken'),
      'X-Requested-With': 'XMLHttpRequest',
      ...(options.headers || {})
    }
  };

  if (options.body !== undefined) {
    fetchOptions.headers['Content-Type'] = 'application/json';
    fetchOptions.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, fetchOptions);
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

function getCookie(name) {
  if (name === 'csrftoken' && typeof CSRF_TOKEN !== 'undefined' && CSRF_TOKEN) {
    return CSRF_TOKEN;
  }

  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

function getValue(id) {
  const element = document.getElementById(id);
  return element ? element.value : '';
}

function setValue(id, value) {
  const element = document.getElementById(id);
  if (element) element.value = value;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function setChecked(id, value) {
  const element = document.getElementById(id);
  if (element) element.checked = !!value;
}

function textoSelecionado(id) {
  const select = document.getElementById(id);
  return select?.options[select.selectedIndex]?.text || '';
}

function normalizarTexto(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function renderRespostaModelo(tipo) {
  if (tipo === 'texto') {
    return '<span class="answer-text-preview"><i class="fa-solid fa-align-left"></i> Campo de texto</span>';
  }

  if (tipo === 'numero') {
    return '<span class="answer-text-preview"><i class="fa-solid fa-hashtag"></i> Campo numérico</span>';
  }

  if (tipo === 'data') {
    return '<span class="answer-text-preview"><i class="fa-solid fa-calendar-day"></i> Campo de data</span>';
  }

  if (tipo === 'foto') {
    return '<span class="answer-text-preview"><i class="fa-solid fa-camera"></i> Enviar foto</span>';
  }

  return `
    <span><i class="answer-radio checked"></i> Atende</span>
    <span><i class="answer-radio"></i> Não atende</span>
    <span><i class="answer-radio"></i> Não se aplica</span>
  `;
}

function rotuloTipoResposta(tipo) {
  const labels = {
    sim_nao: 'Atende / Não atende / Não se aplica',
    texto: 'Texto',
    numero: 'Número',
    data: 'Data',
    foto: 'Foto'
  };
  return labels[tipo] || tipo || 'Resposta';
}

function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeAttr(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/\r?\n/g, ' ');
}
