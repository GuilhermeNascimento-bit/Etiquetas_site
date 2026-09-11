(() => {
  'use strict';

  const HARD_DEFAULT_CONFIG = {
    largura_mm: 90,
    altura_mm: 42,
    nome_loja: 'DILIONE FITNESS',
    cor_faixa: '#000000',
    cor_texto_faixa: '#FFFFFF',
    cor_destaque: '#000000',
    logo_base64: null,
    fonte_nome: 9,
    fonte_destaque: 16,
    fonte_detalhe: 7,
  };

  const PTMM = 0.3528; // 1pt em mm (equivalência usada também no PDF)

  const state = {
    config: { ...HARD_DEFAULT_CONFIG },
    produtos: [],
    logoImgEl: null,
  };

  const el = (id) => document.getElementById(id);

  function novoProduto() {
    return {
      nome: '',
      campos: [
        { rotulo: 'Fabricação', valor: '', destaque: true },
        { rotulo: 'Validade', valor: '', destaque: true },
      ],
      qtde: 1,
    };
  }

  // ── Config panel ────────────────────────────────────────────────
  function preencherCamposConfig() {
    el('nome-loja').value = state.config.nome_loja || '';
    el('largura-mm').value = state.config.largura_mm;
    el('altura-mm').value = state.config.altura_mm;
    el('cor-faixa').value = state.config.cor_faixa || '#000000';
    el('cor-texto-faixa').value = state.config.cor_texto_faixa || '#ffffff';
    el('cor-destaque').value = state.config.cor_destaque || '#000000';
    el('fonte-nome').value = state.config.fonte_nome;
    el('fonte-destaque').value = state.config.fonte_destaque;
    el('fonte-detalhe').value = state.config.fonte_detalhe;
    atualizarBadgesFonte();
    if (state.config.logo_base64) {
      el('logo-preview').src = state.config.logo_base64;
      el('logo-preview-wrap').hidden = false;
    } else {
      el('logo-preview-wrap').hidden = true;
    }
  }

  function atualizarBadgesFonte() {
    el('v-fonte-nome').textContent = `${Number(el('fonte-nome').value).toFixed(1)}pt`;
    el('v-fonte-destaque').textContent = `${Number(el('fonte-destaque').value).toFixed(1)}pt`;
    el('v-fonte-detalhe').textContent = `${Number(el('fonte-detalhe').value).toFixed(1)}pt`;
  }

  function bindConfigInputs() {
    el('nome-loja').addEventListener('input', (e) => { state.config.nome_loja = e.target.value; renderPreview(); });
    el('largura-mm').addEventListener('input', (e) => { state.config.largura_mm = Number(e.target.value) || HARD_DEFAULT_CONFIG.largura_mm; renderPreview(); });
    el('altura-mm').addEventListener('input', (e) => { state.config.altura_mm = Number(e.target.value) || HARD_DEFAULT_CONFIG.altura_mm; renderPreview(); });
    el('cor-faixa').addEventListener('input', (e) => { state.config.cor_faixa = e.target.value; renderPreview(); });
    el('cor-texto-faixa').addEventListener('input', (e) => { state.config.cor_texto_faixa = e.target.value; renderPreview(); });
    el('cor-destaque').addEventListener('input', (e) => { state.config.cor_destaque = e.target.value; renderPreview(); });

    ['fonte-nome', 'fonte-destaque', 'fonte-detalhe'].forEach((id) => {
      el(id).addEventListener('input', (e) => {
        state.config[id.replace('-', '_')] = Number(e.target.value);
        atualizarBadgesFonte();
        renderPreview();
      });
    });

    el('logo-input').addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        state.config.logo_base64 = reader.result;
        const img = new Image();
        img.onload = renderPreview;
        img.src = reader.result;
        state.logoImgEl = img;
        el('logo-preview').src = reader.result;
        el('logo-preview-wrap').hidden = false;
      };
      reader.readAsDataURL(file);
    });

    el('logo-remove').addEventListener('click', () => {
      state.config.logo_base64 = null;
      state.logoImgEl = null;
      el('logo-input').value = '';
      el('logo-preview-wrap').hidden = true;
      renderPreview();
    });

    el('restaurar-padrao').addEventListener('click', () => {
      state.config = { ...HARD_DEFAULT_CONFIG };
      state.logoImgEl = null;
      el('logo-input').value = '';
      preencherCamposConfig();
      renderPreview();
    });
  }

  // ── Produtos ────────────────────────────────────────────────────
  function renderProdutos() {
    const wrap = el('produtos-lista');
    wrap.innerHTML = '';

    state.produtos.forEach((produto, idx) => {
      const card = document.createElement('div');
      card.className = 'produto-card';

      const topo = document.createElement('div');
      topo.className = 'produto-topo';

      const nomeLabel = document.createElement('label');
      nomeLabel.className = 'campo';
      nomeLabel.innerHTML = '<span>Nome do produto</span>';
      const nomeInput = document.createElement('input');
      nomeInput.type = 'text';
      nomeInput.className = 'nome-input';
      nomeInput.placeholder = 'Ex: Penne Artesanal';
      nomeInput.value = produto.nome;
      nomeInput.addEventListener('input', (e) => { produto.nome = e.target.value; renderPreview(); });
      nomeLabel.appendChild(nomeInput);

      const qtdeLabel = document.createElement('label');
      qtdeLabel.className = 'campo';
      qtdeLabel.innerHTML = '<span>Qtde</span>';
      const qtdeInput = document.createElement('input');
      qtdeInput.type = 'number';
      qtdeInput.min = '1';
      qtdeInput.className = 'qtde-input';
      qtdeInput.value = produto.qtde;
      qtdeInput.addEventListener('input', (e) => { produto.qtde = e.target.value; });
      qtdeLabel.appendChild(qtdeInput);

      topo.appendChild(nomeLabel);
      topo.appendChild(qtdeLabel);

      if (state.produtos.length > 1) {
        const btnDel = document.createElement('button');
        btnDel.type = 'button';
        btnDel.className = 'remover-produto';
        btnDel.title = 'Remover produto';
        btnDel.textContent = '✕';
        btnDel.addEventListener('click', () => {
          state.produtos.splice(idx, 1);
          renderProdutos();
          renderPreview();
        });
        topo.appendChild(btnDel);
      }
      card.appendChild(topo);

      const label = document.createElement('div');
      label.className = 'campos-label';
      label.textContent = 'Campos (ligue o interruptor pra destacar)';
      card.appendChild(label);

      const camposWrap = document.createElement('div');
      produto.campos.forEach((campo, cidx) => camposWrap.appendChild(criarLinhaCampo(produto, campo, cidx)));
      card.appendChild(camposWrap);

      const addRow = document.createElement('div');
      addRow.className = 'add-campo-row';
      const btnAddDestaque = document.createElement('button');
      btnAddDestaque.type = 'button';
      btnAddDestaque.textContent = '+ Campo em destaque';
      btnAddDestaque.addEventListener('click', () => {
        produto.campos.push({ rotulo: '', valor: '', destaque: true });
        renderProdutos();
        renderPreview();
      });
      const btnAddDetalhe = document.createElement('button');
      btnAddDetalhe.type = 'button';
      btnAddDetalhe.textContent = '+ Campo detalhe';
      btnAddDetalhe.addEventListener('click', () => {
        produto.campos.push({ rotulo: '', valor: '', destaque: false });
        renderProdutos();
        renderPreview();
      });
      addRow.appendChild(btnAddDestaque);
      addRow.appendChild(btnAddDetalhe);
      card.appendChild(addRow);

      wrap.appendChild(card);
    });

    if (state.produtos.length === 0) {
      const vazio = document.createElement('p');
      vazio.className = 'vazio';
      vazio.textContent = 'Nenhum produto adicionado.';
      wrap.appendChild(vazio);
    }
  }

  function criarLinhaCampo(produto, campo, cidx) {
    const tpl = el('tpl-campo').content.cloneNode(true);
    const row = tpl.querySelector('.campo-row');
    const rotuloInput = row.querySelector('.campo-rotulo');
    const valorInput = row.querySelector('.campo-valor');
    const destaqueInput = row.querySelector('.campo-destaque');
    const removerBtn = row.querySelector('.campo-remover');

    rotuloInput.value = campo.rotulo || '';
    valorInput.value = campo.valor || '';
    destaqueInput.checked = !!campo.destaque;

    rotuloInput.addEventListener('input', (e) => { campo.rotulo = e.target.value; renderPreview(); });
    valorInput.addEventListener('input', (e) => { campo.valor = e.target.value; renderPreview(); });
    destaqueInput.addEventListener('change', (e) => { campo.destaque = e.target.checked; renderPreview(); });
    removerBtn.addEventListener('click', () => {
      produto.campos.splice(cidx, 1);
      renderProdutos();
      renderPreview();
    });

    return row;
  }

  el('add-produto').addEventListener('click', () => {
    state.produtos.push(novoProduto());
    renderProdutos();
    renderPreview();
  });

  // ── Preview (canvas) — espelha exatamente app.py:desenhar_etiqueta ─
  function wrapTextCanvas(ctx, text, maxWidth) {
    const words = text.split(' ').filter(Boolean);
    const lines = [];
    let current = '';
    for (const w of words) {
      const test = (current + ' ' + w).trim();
      if (ctx.measureText(test).width <= maxWidth) current = test;
      else { if (current) lines.push(current); current = w; }
    }
    if (current) lines.push(current);
    return lines;
  }

  function renderPreview() {
    const canvas = el('preview-canvas');
    const ctx = canvas.getContext('2d');
    const cfg = state.config;
    const produto = state.produtos[0] || { nome: '', campos: [], qtde: 1 };

    const PXPERMM = 8;
    const Wmm = Number(cfg.largura_mm) || 90;
    const Hmm = Number(cfg.altura_mm) || 42;
    canvas.width = Math.max(1, Math.round(Wmm * PXPERMM));
    canvas.height = Math.max(1, Math.round(Hmm * PXPERMM));

    const MARGEM = 1.5;
    const AREA_W = Wmm - 2 * MARGEM;
    const FAIXA_H = Hmm * (8.5 / 29);
    const mmpx = (v) => v * PXPERMM;
    const ptmm = (pt) => pt * PTMM;
    const ptpx = (pt) => mmpx(ptmm(pt));
    const FONT = 'Helvetica, Arial, sans-serif';

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = cfg.cor_faixa || '#000000';
    ctx.fillRect(0, 0, canvas.width, mmpx(FAIXA_H));

    ctx.textAlign = 'left';
    ctx.textBaseline = 'alphabetic';

    let textXmm = MARGEM;
    const logoImg = state.logoImgEl;
    if (cfg.logo_base64 && logoImg && logoImg.complete && logoImg.naturalWidth) {
      const logoHmm = FAIXA_H - 2.4;
      const logoWmm = logoHmm * (logoImg.naturalWidth / logoImg.naturalHeight);
      const logoYmm = (FAIXA_H - logoHmm) / 2;
      ctx.drawImage(logoImg, mmpx(MARGEM), mmpx(logoYmm), mmpx(logoWmm), mmpx(logoHmm));
      textXmm = MARGEM + logoWmm + 1.5;
    }

    if (cfg.nome_loja) {
      const fonteLoja = Math.max(6, Math.min(13, Hmm * 0.3));
      ctx.fillStyle = cfg.cor_texto_faixa || '#ffffff';
      ctx.font = `bold ${ptpx(fonteLoja)}px ${FONT}`;
      ctx.fillText(cfg.nome_loja, mmpx(textXmm), mmpx(FAIXA_H * 0.64));
    }

    const campos = produto.campos || [];
    const destaques = campos.filter((c) => c.destaque && (c.valor || c.rotulo));
    const detalhes = campos.filter((c) => !c.destaque && (c.valor || c.rotulo));

    ctx.font = `bold ${ptpx(cfg.fonte_nome)}px ${FONT}`;
    const nomeLines = wrapTextCanvas(ctx, (produto.nome || '').toUpperCase(), mmpx(AREA_W)).slice(0, 2);

    function alturaNecessaria(fnPt, fdPt, fxPt, fator) {
      const fn = ptmm(fnPt) * fator, fd = ptmm(fdPt) * fator;
      let h = 2.6 * fator + fn * 0.85;
      if (nomeLines.length > 1) h += fn * 1.2;
      h += fn * 0.55 + 1.6 * fator;
      if (detalhes.length) h += fd * 0.8 + fd * 0.4 + 1.6 * fator;
      h += 1.4 * fator + 2.6 * fator;
      if (destaques.length) {
        const legenda = ptmm(Math.max(5, fdPt * 0.82)) * fator;
        h += legenda * 0.85 + legenda * 0.4 + 0.8 * fator + ptmm(fxPt) * fator * 0.78;
      }
      return h;
    }

    const disponivel = Hmm - FAIXA_H;
    const alvo = Math.max(0, disponivel - 1.2);
    let fator = 1.0;
    const necessario = alturaNecessaria(cfg.fonte_nome, cfg.fonte_detalhe, cfg.fonte_destaque, 1.0);
    if (necessario > alvo && necessario > 0) {
      fator = Math.max(0.4, alvo / necessario);
    }

    let cursor = FAIXA_H;
    cursor += 2.6 * fator;
    const fnMM = ptmm(cfg.fonte_nome) * fator;
    ctx.fillStyle = '#000000';
    ctx.font = `bold ${ptpx(cfg.fonte_nome * fator)}px ${FONT}`;
    cursor += fnMM * 0.85;
    ctx.fillText(nomeLines[0] || '', mmpx(MARGEM), mmpx(cursor));
    if (nomeLines.length > 1) {
      cursor += fnMM * 1.2;
      ctx.fillText(nomeLines[1], mmpx(MARGEM), mmpx(cursor));
    }
    cursor += fnMM * 0.55 + 1.6 * fator;

    if (detalhes.length) {
      const txt = detalhes.map((d) => (d.rotulo && d.valor) ? `${d.rotulo}: ${d.valor}` : (d.valor || d.rotulo || '')).join('   |   ');
      const fdMM = ptmm(cfg.fonte_detalhe) * fator;
      ctx.font = `${ptpx(cfg.fonte_detalhe * fator)}px ${FONT}`;
      ctx.fillStyle = '#555555';
      cursor += fdMM * 0.8;
      ctx.fillText(txt, mmpx(MARGEM), mmpx(cursor));
      cursor += fdMM * 0.4 + 1.6 * fator;
    }

    cursor += 1.4 * fator;
    const yLinha = cursor;
    ctx.strokeStyle = '#cccccc';
    ctx.lineWidth = Math.max(1, mmpx(0.5));
    ctx.beginPath();
    ctx.moveTo(mmpx(MARGEM), mmpx(yLinha));
    ctx.lineTo(mmpx(Wmm - MARGEM), mmpx(yLinha));
    ctx.stroke();
    cursor += 2.6 * fator;

    if (destaques.length) {
      const n = destaques.length;
      const colW = AREA_W / n;
      const legendaPt = Math.max(5, cfg.fonte_detalhe * 0.82) * fator;
      const legendaMM = ptmm(legendaPt);
      cursor += legendaMM * 0.85;
      const yLegenda = cursor;
      ctx.font = `${ptpx(legendaPt)}px ${FONT}`;
      ctx.fillStyle = '#777777';
      destaques.forEach((d, i) => {
        const x = MARGEM + i * colW;
        ctx.fillText((d.rotulo || '').toUpperCase(), mmpx(x), mmpx(yLegenda));
      });
      cursor += legendaMM * 0.4 + 0.8 * fator;
      const fxMM = ptmm(cfg.fonte_destaque) * fator;
      cursor += fxMM * 0.78;
      const yValor = cursor;
      destaques.forEach((d, i) => {
        const x = MARGEM + i * colW;
        const maxWmm = colW - (i < n - 1 ? 2 : 0);
        const valorTxt = d.valor || '';
        let fPt = cfg.fonte_destaque * fator;
        ctx.font = `bold ${ptpx(fPt)}px ${FONT}`;
        const wMm = ctx.measureText(valorTxt).width / PXPERMM;
        if (maxWmm > 0 && wMm > maxWmm) {
          fPt = Math.max(6, fPt * (maxWmm / wMm));
        }
        ctx.font = `bold ${ptpx(fPt)}px ${FONT}`;
        ctx.fillStyle = cfg.cor_destaque || '#000000';
        ctx.fillText(valorTxt, mmpx(x), mmpx(yValor));
      });
    }
  }

  // ── Gerar PDF ───────────────────────────────────────────────────
  function statusMsg(texto, tipo) {
    const p = el('gerar-status');
    p.textContent = texto;
    p.className = 'status-msg' + (tipo ? ' ' + tipo : '');
  }

  function montarPayloadProdutos() {
    return state.produtos.map((p) => ({
      nome: p.nome,
      campos: (p.campos || []).map((c) => ({ rotulo: c.rotulo || '', valor: c.valor || '', destaque: !!c.destaque })),
      qtde: Number(p.qtde) || 1,
    }));
  }

  el('gerar-pdf').addEventListener('click', async () => {
    if (state.produtos.length === 0) { statusMsg('Adicione ao menos um produto.', 'erro'); return; }
    if (state.produtos.some((p) => !String(p.nome || '').trim())) {
      statusMsg('Preencha o nome de todos os produtos.', 'erro');
      return;
    }

    const btn = el('gerar-pdf');
    btn.disabled = true;
    statusMsg('Gerando PDF…');
    try {
      const resp = await fetch('/gerar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: state.config, produtos: montarPayloadProdutos() }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.erro || 'Falha ao gerar PDF');
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'etiquetas.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      statusMsg('PDF gerado com sucesso.', 'ok');
      carregarHistorico();
    } catch (e) {
      statusMsg(e.message, 'erro');
    } finally {
      btn.disabled = false;
    }
  });

  // ── Importação (mapeada pro modelo universal de campos) ─────────
  function aplicarImportacao(produtos) {
    if (!produtos || !produtos.length) { statusMsg('Nenhum produto encontrado.', 'erro'); return; }
    state.produtos = produtos.map((p) => {
      const campos = [];
      if (p.preco) {
        const preco = String(p.preco).startsWith('R$') ? p.preco : `R$ ${p.preco}`;
        campos.push({ rotulo: 'Preço', valor: preco, destaque: true });
      }
      if (p.cor) campos.push({ rotulo: 'Cor', valor: p.cor, destaque: false });
      if (p.tam) campos.push({ rotulo: 'Tam', valor: p.tam, destaque: false });
      return { nome: p.nome || '', campos, qtde: p.qtde || 1 };
    });
    renderProdutos();
    renderPreview();
    statusMsg(`${produtos.length} produto(s) importado(s).`, 'ok');
  }

  el('btn-importar-texto').addEventListener('click', async () => {
    const texto = el('importar-texto-area').value;
    if (!texto.trim()) return;
    try {
      const resp = await fetch('/importar_texto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto }),
      });
      const data = await resp.json();
      if (data.erro) throw new Error(data.erro);
      aplicarImportacao(data.produtos);
    } catch (e) {
      statusMsg(e.message, 'erro');
    }
  });

  el('importar-xlsx-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('arquivo', file);
    try {
      const resp = await fetch('/importar_xlsx', { method: 'POST', body: form });
      const data = await resp.json();
      if (data.erro) throw new Error(data.erro);
      aplicarImportacao(data.produtos);
    } catch (e2) {
      statusMsg(e2.message, 'erro');
    } finally {
      e.target.value = '';
    }
  });

  el('importar-nf-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('arquivo', file);
    try {
      const resp = await fetch('/ler_nf', { method: 'POST', body: form });
      const data = await resp.json();
      if (data.erro) throw new Error(data.erro);
      aplicarImportacao(data.produtos);
    } catch (e2) {
      statusMsg(e2.message, 'erro');
    } finally {
      e.target.value = '';
    }
  });

  // ── Histórico ───────────────────────────────────────────────────
  async function carregarHistorico() {
    const wrap = el('historico-lista');
    try {
      const resp = await fetch('/historico');
      const lista = await resp.json();
      wrap.innerHTML = '';
      if (!lista.length) {
        wrap.innerHTML = '<p class="vazio">Nenhuma geração ainda.</p>';
        return;
      }
      lista.forEach((h) => {
        const item = document.createElement('div');
        item.className = 'historico-item';
        item.innerHTML = `
          <div class="linha1"><span>${h.data || ''}</span></div>
          <div class="resumo">${h.produtos || 0} produto(s) · ${h.etiquetas || 0} etiqueta(s)</div>
          <div class="acoes">
            <a href="/historico/download/${encodeURIComponent(h.nome_arquivo || h.id)}">baixar</a>
            <button type="button" class="excluir">excluir</button>
          </div>`;
        item.querySelector('.excluir').addEventListener('click', async () => {
          await fetch(`/historico/${encodeURIComponent(h.id)}`, { method: 'DELETE' });
          carregarHistorico();
        });
        wrap.appendChild(item);
      });
    } catch (e) {
      wrap.innerHTML = '<p class="vazio">Não foi possível carregar o histórico.</p>';
    }
  }

  // ── Inicialização ───────────────────────────────────────────────
  async function init() {
    try {
      const resp = await fetch('/config/default');
      const cfg = await resp.json();
      state.config = { ...HARD_DEFAULT_CONFIG, ...cfg };
    } catch (e) {
      state.config = { ...HARD_DEFAULT_CONFIG };
    }
    bindConfigInputs();
    preencherCamposConfig();
    state.produtos = [novoProduto()];
    renderProdutos();
    renderPreview();
    carregarHistorico();
  }

  init();
})();
