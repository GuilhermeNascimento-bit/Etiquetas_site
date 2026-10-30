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
  };

  const PTMM = 0.3528; // 1pt em mm (equivalência usada também no PDF)

  // Mesma estrutura de app.py:LINHAS — mantenha as duas iguais.
  const DATA = [['ln', 2], ['t', '/'], ['ln', 2], ['t', '/'], ['ln', 3.2]];
  const LINHAS = [
    { seg: [['b', 'Produto:'], ['sp', 0.4], ['fill']] },
    { seg: [['b', 'Fabricação/Abertura:'], ['sp', 0.4], ...DATA, ['sp', 1],
            ['b', 'Hora:'], ['sp', 0.4], ['ln', 1.8], ['t', ':'], ['ln', 1.8]] },
    { seg: [['b', 'VALIDADE:'], ['sp', 0.4], ...DATA], destaque: true },
    { seg: [['b', 'Conservação:'], ['sp', 0.5], ['box'], ['t', 'Refrigerado'], ['sp', 0.7],
            ['box'], ['t', 'Congelado'], ['sp', 0.7], ['box'], ['t', 'Ambiente']] },
  ];
  const CAIXA_EM = 0.75, CAIXA_GAP_EM = 0.3, FILL_MIN_EM = 3;

  const state = {
    config: { ...HARD_DEFAULT_CONFIG },
    logoImgEl: null,
  };

  const el = (id) => document.getElementById(id);

  // ── Config panel ────────────────────────────────────────────────
  function preencherCamposConfig() {
    el('nome-loja').value = state.config.nome_loja || '';
    el('largura-mm').value = state.config.largura_mm;
    el('altura-mm').value = state.config.altura_mm;
    el('cor-faixa').value = state.config.cor_faixa || '#000000';
    el('cor-texto-faixa').value = state.config.cor_texto_faixa || '#ffffff';
    el('cor-destaque').value = state.config.cor_destaque || '#000000';
    if (state.config.logo_base64) {
      el('logo-preview').src = state.config.logo_base64;
      el('logo-preview-wrap').hidden = false;
    } else {
      el('logo-preview-wrap').hidden = true;
    }
  }

  function bindConfigInputs() {
    el('nome-loja').addEventListener('input', (e) => { state.config.nome_loja = e.target.value; renderPreview(); });
    el('largura-mm').addEventListener('input', (e) => { state.config.largura_mm = Number(e.target.value) || HARD_DEFAULT_CONFIG.largura_mm; renderPreview(); });
    el('altura-mm').addEventListener('input', (e) => { state.config.altura_mm = Number(e.target.value) || HARD_DEFAULT_CONFIG.altura_mm; renderPreview(); });
    el('cor-faixa').addEventListener('input', (e) => { state.config.cor_faixa = e.target.value; renderPreview(); });
    el('cor-texto-faixa').addEventListener('input', (e) => { state.config.cor_texto_faixa = e.target.value; renderPreview(); });
    el('cor-destaque').addEventListener('input', (e) => { state.config.cor_destaque = e.target.value; renderPreview(); });

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

    const PXPERMM = 8;
    const mmpx = (v) => v * PXPERMM;
    const Wmm = Number(cfg.largura_mm) || 90;
    const Hmm = Number(cfg.altura_mm) || 42;
    canvas.width = Math.max(1, Math.round(mmpx(Wmm)));
    canvas.height = Math.max(1, Math.round(mmpx(Hmm)));
    const W = canvas.width, H = canvas.height;
    const pt = PTMM * PXPERMM; // 1pt em px

    const MARGEM = mmpx(2);
    const AREA_W = W - 2 * MARGEM;
    const FAIXA_H = H * 0.24;
    const FONT = 'Helvetica, Arial, sans-serif';
    const fontB = (px) => `bold ${px}px ${FONT}`;
    const fontR = (px) => `${px}px ${FONT}`;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = cfg.cor_faixa || '#000000';
    ctx.fillRect(0, 0, W, FAIXA_H);
    ctx.textBaseline = 'alphabetic';

    // Título à esquerda (2 linhas), loja/logo à direita
    const fonteTitulo = FAIXA_H * 0.32;
    ctx.fillStyle = cfg.cor_texto_faixa || '#ffffff';
    ctx.font = fontB(fonteTitulo);
    ctx.textAlign = 'left';
    ctx.fillText('IDENTIFICAÇÃO DO', MARGEM, FAIXA_H * 0.44);
    ctx.fillText('ALIMENTO', MARGEM, FAIXA_H * 0.84);
    const tituloW = ctx.measureText('IDENTIFICAÇÃO DO').width;
    const direitaMax = W - MARGEM - (MARGEM + tituloW + mmpx(3));

    const logoImg = state.logoImgEl;
    let desenhouLogo = false;
    if (cfg.logo_base64 && logoImg && logoImg.complete && logoImg.naturalWidth) {
      const ratio = logoImg.naturalWidth / logoImg.naturalHeight;
      let logoH = FAIXA_H - mmpx(2);
      const logoW = Math.min(logoH * ratio, direitaMax);
      logoH = logoW / ratio;
      ctx.drawImage(logoImg, W - MARGEM - logoW, (FAIXA_H - logoH) / 2, logoW, logoH);
      desenhouLogo = true;
    }

    const nomeLoja = (cfg.nome_loja || '').toUpperCase();
    if (nomeLoja && !desenhouLogo && direitaMax > 0) {
      let f = fonteTitulo;
      const minF = 4 * pt, passo = 0.25 * pt;
      ctx.font = fontB(f);
      let linhas = wrapTextCanvas(ctx, nomeLoja, direitaMax);
      while (f > minF && (linhas.length > 2 || linhas.some((l) => ctx.measureText(l).width > direitaMax))) {
        f -= passo;
        ctx.font = fontB(f);
        linhas = wrapTextCanvas(ctx, nomeLoja, direitaMax);
      }
      ctx.textAlign = 'right';
      const bases = linhas.length === 1 ? [0.62] : [0.44, 0.84];
      linhas.slice(0, 2).forEach((l, i) => ctx.fillText(l, W - MARGEM, FAIXA_H * bases[i]));
      ctx.textAlign = 'left';
    }

    // Corpo: linhas distribuídas por igual; a fonte acompanha a altura
    // da etiqueta e só encolhe se alguma linha não couber na largura.
    const corpoTopo = FAIXA_H + mmpx(0.8);
    const corpoBase = H - mmpx(1.2);
    const linhaH = (corpoBase - corpoTopo) / LINHAS.length;
    let fs = linhaH * 0.46;

    const larguraSeg = (s) => {
      switch (s[0]) {
        case 'b': ctx.font = fontB(fs); return ctx.measureText(s[1]).width;
        case 't': ctx.font = fontR(fs); return ctx.measureText(s[1]).width;
        case 'ln': case 'sp': return s[1] * fs;
        case 'box': return (CAIXA_EM + CAIXA_GAP_EM) * fs;
        case 'fill': return FILL_MIN_EM * fs;
        default: return 0;
      }
    };
    const maior = Math.max(...LINHAS.map((l) => l.seg.reduce((acc, s) => acc + larguraSeg(s), 0)));
    if (maior > AREA_W) fs *= AREA_W / maior;

    ctx.lineWidth = 0.6 * pt;
    LINHAS.forEach((linha, i) => {
      const cor = linha.destaque ? (cfg.cor_destaque || '#000000') : '#000000';
      ctx.fillStyle = cor;
      ctx.strokeStyle = cor;
      const y = corpoTopo + linhaH * (i + 0.5) + fs * 0.35;
      let x = MARGEM;
      for (const s of linha.seg) {
        const w = larguraSeg(s);
        if (s[0] === 'b' || s[0] === 't') {
          ctx.font = s[0] === 'b' ? fontB(fs) : fontR(fs);
          ctx.fillText(s[1], x, y);
        } else if (s[0] === 'ln') {
          ctx.beginPath(); ctx.moveTo(x, y + 0.6 * pt); ctx.lineTo(x + w, y + 0.6 * pt); ctx.stroke();
        } else if (s[0] === 'fill') {
          ctx.beginPath(); ctx.moveTo(x, y + 0.6 * pt); ctx.lineTo(W - MARGEM, y + 0.6 * pt); ctx.stroke();
          break;
        } else if (s[0] === 'box') {
          const lado = CAIXA_EM * fs;
          ctx.strokeRect(x, y + 0.5 * pt - lado, lado, lado);
        }
        x += w;
      }
    });
  }

  // ── Gerar PDF ───────────────────────────────────────────────────
  function statusMsg(texto, tipo) {
    const p = el('gerar-status');
    p.textContent = texto;
    p.className = 'status-msg' + (tipo ? ' ' + tipo : '');
  }

  el('gerar-pdf').addEventListener('click', async () => {
    const qtde = Number(el('qtde').value);
    if (!Number.isInteger(qtde) || qtde < 1) { statusMsg('Informe a quantidade de etiquetas.', 'erro'); return; }

    const btn = el('gerar-pdf');
    btn.disabled = true;
    statusMsg('Gerando PDF…');
    try {
      const resp = await fetch('/gerar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: state.config, qtde }),
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
          <div class="resumo">${h.etiquetas || 0} etiqueta(s)</div>
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
    renderPreview();
    carregarHistorico();
  }

  init();
})();
