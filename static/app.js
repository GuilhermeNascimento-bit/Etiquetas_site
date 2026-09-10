(() => {
  'use strict';

  const HARD_DEFAULT_CONFIG = {
    largura_mm: 90,
    altura_mm: 29,
    nome_loja: 'DILIONE FITNESS',
    cor_faixa: '#000000',
    cor_texto_faixa: '#FFFFFF',
    logo_base64: null,
  };

  const FIELDS = {
    roupa: [
      { key: 'nome', label: 'Nome do produto', type: 'text', required: true, full: true },
      { key: 'cor', label: 'Cor', type: 'text' },
      { key: 'tam', label: 'Tamanho', type: 'text' },
      { key: 'preco', label: 'Preço (R$)', type: 'text', required: true },
      { key: 'qtde', label: 'Qtde', type: 'number', default: 1 },
    ],
    validade: [
      { key: 'nome', label: 'Nome do produto', type: 'text', required: true, full: true },
      { key: 'fabricacao', label: 'Fabricação', type: 'date' },
      { key: 'validade', label: 'Validade', type: 'date', required: true },
      { key: 'lote', label: 'Lote (opcional)', type: 'text' },
      { key: 'qtde', label: 'Qtde', type: 'number', default: 1 },
    ],
  };

  const state = {
    tipo: 'roupa',
    config: { ...HARD_DEFAULT_CONFIG },
    produtos: [],
    logoImgEl: null,
  };

  const el = (id) => document.getElementById(id);

  function novoProduto(tipo) {
    const obj = {};
    FIELDS[tipo].forEach((f) => { obj[f.key] = f.default !== undefined ? f.default : ''; });
    return obj;
  }

  function formatDateBR(iso) {
    if (!iso) return '';
    const [y, m, d] = iso.split('-');
    if (!y || !m || !d) return iso;
    return `${d}/${m}/${y}`;
  }

  // ── Config panel ────────────────────────────────────────────────
  function preencherCamposConfig() {
    el('nome-loja').value = state.config.nome_loja || '';
    el('largura-mm').value = state.config.largura_mm;
    el('altura-mm').value = state.config.altura_mm;
    el('cor-faixa').value = state.config.cor_faixa || '#000000';
    el('cor-texto-faixa').value = state.config.cor_texto_faixa || '#ffffff';
    if (state.config.logo_base64) {
      el('logo-preview').src = state.config.logo_base64;
      el('logo-preview-wrap').hidden = false;
    } else {
      el('logo-preview-wrap').hidden = true;
    }
  }

  function bindConfigInputs() {
    el('nome-loja').addEventListener('input', (e) => {
      state.config.nome_loja = e.target.value; renderPreview();
    });
    el('largura-mm').addEventListener('input', (e) => {
      state.config.largura_mm = Number(e.target.value) || HARD_DEFAULT_CONFIG.largura_mm; renderPreview();
    });
    el('altura-mm').addEventListener('input', (e) => {
      state.config.altura_mm = Number(e.target.value) || HARD_DEFAULT_CONFIG.altura_mm; renderPreview();
    });
    el('cor-faixa').addEventListener('input', (e) => {
      state.config.cor_faixa = e.target.value; renderPreview();
    });
    el('cor-texto-faixa').addEventListener('input', (e) => {
      state.config.cor_texto_faixa = e.target.value; renderPreview();
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
    const fields = FIELDS[state.tipo];

    state.produtos.forEach((produto, idx) => {
      const card = document.createElement('div');
      card.className = 'produto-card';

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
        card.appendChild(btnDel);
      }

      const fullField = fields.find((f) => f.full);
      if (fullField) card.appendChild(criarInput(produto, fullField, idx));

      const linha = document.createElement('div');
      linha.className = 'linha';
      fields.filter((f) => !f.full).forEach((f) => linha.appendChild(criarInput(produto, f, idx)));
      card.appendChild(linha);

      wrap.appendChild(card);
    });

    if (state.produtos.length === 0) {
      const vazio = document.createElement('p');
      vazio.className = 'vazio';
      vazio.textContent = 'Nenhum produto adicionado.';
      wrap.appendChild(vazio);
    }
  }

  function criarInput(produto, field, idx) {
    const label = document.createElement('label');
    label.className = 'campo';
    const span = document.createElement('span');
    span.textContent = field.label;
    const input = document.createElement('input');
    input.type = field.type;
    input.value = produto[field.key] ?? '';
    if (field.type === 'number') input.min = '1';
    input.addEventListener('input', (e) => {
      produto[field.key] = field.type === 'number' ? e.target.value : e.target.value;
      renderPreview();
    });
    label.appendChild(span);
    label.appendChild(input);
    return label;
  }

  el('add-produto').addEventListener('click', () => {
    state.produtos.push(novoProduto(state.tipo));
    renderProdutos();
    renderPreview();
  });

  // ── Tipo switch ─────────────────────────────────────────────────
  document.querySelectorAll('.tipo-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tipo = btn.dataset.tipo;
      if (tipo === state.tipo) return;
      state.tipo = tipo;
      document.querySelectorAll('.tipo-btn').forEach((b) => b.classList.toggle('active', b === btn));
      el('import-tools').hidden = tipo !== 'roupa';
      state.produtos = [novoProduto(tipo)];
      renderProdutos();
      renderPreview();
    });
  });
  el('import-tools').hidden = state.tipo !== 'roupa';

  // ── Preview (canvas) ────────────────────────────────────────────
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
    const tipo = state.tipo;
    const produto = state.produtos[0] || {};

    const PXPERMM = 8;
    const Wmm = Number(cfg.largura_mm) || 90;
    const Hmm = Number(cfg.altura_mm) || 29;
    canvas.width = Math.max(1, Math.round(Wmm * PXPERMM));
    canvas.height = Math.max(1, Math.round(Hmm * PXPERMM));

    const MARGEM = 1.5;
    const AREA_W = Wmm - 2 * MARGEM;
    const escala = Hmm / 29;
    const FAIXA_H = Hmm * (8.5 / 29);
    const mmpx = (v) => v * PXPERMM;
    const ptpx = (pt) => pt * escala * 0.3528 * PXPERMM;
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
      const logoHmm = FAIXA_H - 2 * (1.2 * escala);
      const logoWmm = logoHmm * (logoImg.naturalWidth / logoImg.naturalHeight);
      const logoYmm = (FAIXA_H - logoHmm) / 2;
      ctx.drawImage(logoImg, mmpx(MARGEM), mmpx(logoYmm), mmpx(logoWmm), mmpx(logoHmm));
      textXmm = MARGEM + logoWmm + 1.5;
    }

    ctx.fillStyle = cfg.cor_texto_faixa || '#ffffff';
    ctx.font = `bold ${ptpx(7.5)}px ${FONT}`;
    ctx.fillText(cfg.nome_loja || 'DILIONE FITNESS', mmpx(textXmm), mmpx(FAIXA_H - 2.8 * escala));

    if (tipo === 'roupa') {
      const infoFaixa = [produto.cor, produto.tam].filter(Boolean).join(' | ');
      if (infoFaixa) {
        ctx.font = `${ptpx(5.5)}px ${FONT}`;
        ctx.textAlign = 'right';
        ctx.fillText(infoFaixa, mmpx(Wmm - MARGEM), mmpx(FAIXA_H - 2.8 * escala));
        ctx.textAlign = 'left';
      }
    }

    ctx.fillStyle = '#000000';
    ctx.font = `bold ${ptpx(6.5)}px ${FONT}`;
    const nomeLines = wrapTextCanvas(ctx, (produto.nome || '').toUpperCase(), mmpx(AREA_W));
    const yNomeMm = FAIXA_H + 4.5 * escala;
    nomeLines.slice(0, 2).forEach((line, i) => {
      ctx.fillText(line, mmpx(MARGEM), mmpx(yNomeMm + i * 3.8 * escala));
    });

    const detalhes = [];
    if (tipo === 'roupa') {
      if (produto.cor) detalhes.push('Cor: ' + produto.cor);
      if (produto.tam) detalhes.push('Tam: ' + produto.tam);
    } else {
      if (produto.fabricacao) detalhes.push('Fab: ' + formatDateBR(produto.fabricacao));
      if (produto.lote) detalhes.push('Lote: ' + produto.lote);
    }
    if (detalhes.length) {
      ctx.font = `${ptpx(6)}px ${FONT}`;
      ctx.fillStyle = '#444444';
      const yDetMm = FAIXA_H + (4.5 + Math.min(nomeLines.length, 2) * 3.8) * escala;
      ctx.fillText(detalhes.join('   |   '), mmpx(MARGEM), mmpx(yDetMm));
    }

    ctx.strokeStyle = '#cccccc';
    ctx.lineWidth = Math.max(1, mmpx(0.4));
    ctx.beginPath();
    const yLineMm = Hmm - 7.2 * escala;
    ctx.moveTo(mmpx(MARGEM), mmpx(yLineMm));
    ctx.lineTo(mmpx(Wmm - MARGEM), mmpx(yLineMm));
    ctx.stroke();

    ctx.fillStyle = '#000000';
    ctx.font = `bold ${ptpx(12)}px ${FONT}`;
    const yBottomMm = Hmm - 2.8 * escala;
    let rotulo;
    if (tipo === 'roupa') {
      const preco = (produto.preco || '').toString();
      const precoFmt = preco.startsWith('R$') ? preco : `R$ ${preco}`;
      ctx.fillText(precoFmt, mmpx(MARGEM), mmpx(yBottomMm));
      rotulo = 'PRECO SUGERIDO';
    } else {
      ctx.fillText(`VAL: ${formatDateBR(produto.validade)}`, mmpx(MARGEM), mmpx(yBottomMm));
      rotulo = 'DATA DE VALIDADE';
    }
    ctx.font = `${ptpx(5)}px ${FONT}`;
    ctx.fillStyle = '#888888';
    ctx.textAlign = 'right';
    ctx.fillText(rotulo, mmpx(Wmm - MARGEM), mmpx(yBottomMm));
    ctx.textAlign = 'left';
  }

  // ── Gerar PDF ───────────────────────────────────────────────────
  function statusMsg(texto, tipo) {
    const p = el('gerar-status');
    p.textContent = texto;
    p.className = 'status-msg' + (tipo ? ' ' + tipo : '');
  }

  function validarProdutos() {
    const fields = FIELDS[state.tipo].filter((f) => f.required);
    for (const p of state.produtos) {
      for (const f of fields) {
        if (!String(p[f.key] || '').trim()) return `Preencha "${f.label}" em todos os produtos.`;
      }
    }
    return null;
  }

  function montarPayloadProdutos() {
    const fields = FIELDS[state.tipo];
    return state.produtos.map((p) => {
      const out = {};
      fields.forEach((f) => {
        out[f.key] = f.type === 'date' ? formatDateBR(p[f.key]) : p[f.key];
      });
      out.qtde = Number(p.qtde) || 1;
      return out;
    });
  }

  el('gerar-pdf').addEventListener('click', async () => {
    if (state.produtos.length === 0) { statusMsg('Adicione ao menos um produto.', 'erro'); return; }
    const erro = validarProdutos();
    if (erro) { statusMsg(erro, 'erro'); return; }

    const btn = el('gerar-pdf');
    btn.disabled = true;
    statusMsg('Gerando PDF…');
    try {
      const resp = await fetch('/gerar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tipo: state.tipo, config: state.config, produtos: montarPayloadProdutos() }),
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

  // ── Importação (só etiqueta de roupa) ──────────────────────────
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

  function aplicarImportacao(produtos) {
    if (!produtos || !produtos.length) { statusMsg('Nenhum produto encontrado.', 'erro'); return; }
    state.produtos = produtos.map((p) => ({
      nome: p.nome || '', cor: p.cor || '', tam: p.tam || '',
      preco: p.preco || '', qtde: p.qtde || 1,
    }));
    renderProdutos();
    renderPreview();
    statusMsg(`${produtos.length} produto(s) importado(s).`, 'ok');
  }

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
        const tipoLabel = h.tipo === 'validade' ? 'validade' : 'roupa';
        item.innerHTML = `
          <div class="linha1">
            <span>${h.data || ''}</span>
            <span class="badge">${tipoLabel}</span>
          </div>
          <div>${h.produtos || 0} produto(s) · ${h.etiquetas || 0} etiqueta(s)</div>
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
    state.produtos = [novoProduto(state.tipo)];
    renderProdutos();
    renderPreview();
    carregarHistorico();
  }

  init();
})();
