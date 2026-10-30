import os, json, datetime, base64, io
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
CORS(app)

# Configuração padrão da etiqueta. As medidas são as da bobina da impressora.
DEFAULT_CONFIG = {
    'largura_mm': 90,
    'altura_mm': 42,
    'nome_loja': 'DILIONE FITNESS',
    'cor_faixa': '#000000',
    'cor_texto_faixa': '#FFFFFF',
    'cor_destaque': '#000000',
    'logo_base64': None,
}
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
HIST_FILE = os.path.join(BASE_DIR, "historico.json")
PDFS_DIR  = os.path.join(BASE_DIR, "pdfs_gerados")
os.makedirs(PDFS_DIR, exist_ok=True)

# Estrutura fixa da etiqueta "Identificação do Alimento". Cada linha é uma
# sequência de segmentos:
#   ('b', txt) rótulo em negrito   ('t', txt) texto normal
#   ('ln', em) linha em branco     ('sp', em) espaço
#   ('campo', chave, vazio)  valor digitado pelo usuário (dados[chave]); se
#       vier vazio, desenha os segmentos de `vazio` (ou linha até o fim, se None)
#   ('box', opcao)  caixinha de marcar; sai marcada se dados['conservacao'] == opcao
# Larguras em "em" (múltiplos do tamanho da fonte). Esta mesma tabela
# existe em static/app.js para a pré-visualização — mantenha as duas iguais.
DATA = [('ln', 2), ('t', '/'), ('ln', 2), ('t', '/'), ('ln', 3.2)]
HORA = [('ln', 1.8), ('t', ':'), ('ln', 1.8)]
LINHAS = [
    {'seg': [('b', 'Produto:'), ('sp', .4), ('campo', 'produto', None)]},
    {'seg': [('b', 'Fabricação/Abertura:'), ('sp', .4), ('campo', 'fabricacao', DATA), ('sp', 1),
             ('b', 'Hora:'), ('sp', .4), ('campo', 'hora', HORA)]},
    {'seg': [('b', 'VALIDADE:'), ('sp', .4), ('campo', 'validade', DATA)], 'destaque': True},
    {'seg': [('b', 'Conservação:'), ('sp', .5),
             ('box', 'Refrigerado'), ('t', 'Refrigerado'), ('sp', .7),
             ('box', 'Congelado'), ('t', 'Congelado'), ('sp', .7),
             ('box', 'Ambiente'), ('t', 'Ambiente')]},
]
CAIXA_EM, CAIXA_GAP_EM, FILL_MIN_EM = .75, .3, 3

# ── Helpers PDF ──────────────────────────────────────────────────
def wrap_text(c, text, font, size, max_width):
    words = text.split()
    lines, current = [], ''
    for word in words:
        test = (current + ' ' + word).strip()
        if c.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines

def largura_seg(c, s, fs):
    tipo = s[0]
    if tipo == 'b':    return c.stringWidth(s[1], "Helvetica-Bold", fs)
    if tipo == 't':    return c.stringWidth(s[1], "Helvetica", fs)
    if tipo in ('ln', 'sp'): return s[1] * fs
    if tipo == 'box':  return (CAIXA_EM + CAIXA_GAP_EM) * fs
    if tipo == 'campo':
        if s[2] is None: return FILL_MIN_EM * fs
        return sum(largura_seg(c, sub, fs) for sub in s[2])
    return 0

def desenhar_seg(c, s, x, y, fs, dados, x_fim):
    """Desenha um segmento com a linha de base em y; x_fim é onde
    termina a área útil (usado pelo campo que vai até o fim da linha)."""
    tipo = s[0]
    if tipo in ('b', 't'):
        c.setFont("Helvetica-Bold" if tipo == 'b' else "Helvetica", fs)
        c.drawString(x, y, s[1])
    elif tipo == 'ln':
        c.line(x, y - 0.6, x + s[1]*fs, y - 0.6)
    elif tipo == 'box':
        lado = CAIXA_EM * fs
        c.rect(x, y - 0.5, lado, lado, fill=0, stroke=1)
        if dados.get('conservacao') == s[1]:
            p = lado * 0.2
            c.line(x + p, y - 0.5 + p, x + lado - p, y - 0.5 + lado - p)
            c.line(x + p, y - 0.5 + lado - p, x + lado - p, y - 0.5 + p)
    elif tipo == 'campo':
        largura = (x_fim - x) if s[2] is None else largura_seg(c, s, fs)
        valor = str(dados.get(s[1]) or '').strip()
        if not valor:
            if s[2] is None:
                c.line(x, y - 0.6, x_fim, y - 0.6)
            for sub in s[2] or []:
                desenhar_seg(c, sub, x, y, fs, dados, x_fim)
                x += largura_seg(c, sub, fs)
            return
        # Valor digitado sobre a linha; encolhe a fonte se não couber.
        f, max_w = fs, largura - 0.3*fs
        w = c.stringWidth(valor, "Helvetica", f)
        if w > max_w > 0:
            f = max(fs * 0.5, f * max_w / w)
        c.setFont("Helvetica", f)
        c.drawString(x + 0.15*fs, y, valor)
        c.line(x, y - 0.6, x + largura, y - 0.6)

def desenhar_etiqueta(c, cfg, dados):
    """Etiqueta de identificação do alimento no tamanho da bobina. Campos
    preenchidos em `dados` saem impressos; os vazios ficam com linha em
    branco para preencher à mão."""
    W = cfg['largura_mm'] * mm
    H = cfg['altura_mm'] * mm
    MARGEM  = 2 * mm
    AREA_W  = W - 2*MARGEM
    FAIXA_H = H * 0.24

    cor_faixa       = colors.HexColor(cfg.get('cor_faixa') or '#000000')
    cor_texto_faixa = colors.HexColor(cfg.get('cor_texto_faixa') or '#FFFFFF')
    cor_destaque    = colors.HexColor(cfg.get('cor_destaque') or '#000000')
    nome_loja       = (cfg.get('nome_loja') or '').upper()

    # Fundo + faixa superior
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(cor_faixa)
    c.rect(0, H - FAIXA_H, W, FAIXA_H, fill=1, stroke=0)

    # Título à esquerda (2 linhas), loja/logo à direita
    fonte_titulo = FAIXA_H * 0.32
    c.setFillColor(cor_texto_faixa)
    c.setFont("Helvetica-Bold", fonte_titulo)
    c.drawString(MARGEM, H - FAIXA_H*0.44, "IDENTIFICAÇÃO DO")
    c.drawString(MARGEM, H - FAIXA_H*0.84, "ALIMENTO")
    titulo_w = c.stringWidth("IDENTIFICAÇÃO DO", "Helvetica-Bold", fonte_titulo)
    direita_max = W - MARGEM - (MARGEM + titulo_w + 3*mm)

    logo_b64 = cfg.get('logo_base64')
    desenhou_logo = False
    if logo_b64:
        try:
            b64data = logo_b64.split(',', 1)[1] if ',' in logo_b64 else logo_b64
            img = ImageReader(io.BytesIO(base64.b64decode(b64data)))
            iw, ih = img.getSize()
            logo_h = FAIXA_H - 2*mm
            logo_w = min(logo_h * (iw/ih), direita_max)
            logo_h = logo_w * (ih/iw)
            c.drawImage(img, W - MARGEM - logo_w, H - FAIXA_H + (FAIXA_H - logo_h)/2,
                        width=logo_w, height=logo_h, mask='auto', preserveAspectRatio=True)
            desenhou_logo = True
        except Exception:
            pass

    if nome_loja and not desenhou_logo and direita_max > 0:
        f = fonte_titulo
        linhas = wrap_text(c, nome_loja, "Helvetica-Bold", f, direita_max)
        while f > 4 and (len(linhas) > 2 or any(
                c.stringWidth(l, "Helvetica-Bold", f) > direita_max for l in linhas)):
            f -= 0.25
            linhas = wrap_text(c, nome_loja, "Helvetica-Bold", f, direita_max)
        c.setFont("Helvetica-Bold", f)
        bases = [0.62] if len(linhas) == 1 else [0.44, 0.84]
        for l, b in zip(linhas[:2], bases):
            c.drawRightString(W - MARGEM, H - FAIXA_H*b, l)

    # Corpo: linhas distribuídas por igual; a fonte acompanha a altura
    # da etiqueta e só encolhe se alguma linha não couber na largura.
    corpo_topo = H - FAIXA_H - 0.8*mm
    corpo_base = 1.2*mm
    linha_h = (corpo_topo - corpo_base) / len(LINHAS)
    fs = linha_h * 0.46
    maior = max(sum(largura_seg(c, s, fs) for s in l['seg']) for l in LINHAS)
    if maior > AREA_W:
        fs *= AREA_W / maior

    c.setLineWidth(0.6)
    for i, linha in enumerate(LINHAS):
        cor = cor_destaque if linha.get('destaque') else colors.black
        c.setFillColor(cor)
        c.setStrokeColor(cor)
        y = corpo_topo - linha_h*(i + 0.5) - fs*0.35
        x = MARGEM
        for seg in linha['seg']:
            desenhar_seg(c, seg, x, y, fs, dados, W - MARGEM)
            x += largura_seg(c, seg, fs)

    c.showPage()

def gerar_pdf_arquivo(qtde, cfg=None, dados=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    W = cfg['largura_mm'] * mm
    H = cfg['altura_mm'] * mm
    nome_arquivo = f"etiquetas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    caminho = os.path.join(PDFS_DIR, nome_arquivo)
    c = canvas.Canvas(caminho, pagesize=(W, H))
    for _ in range(qtde):
        desenhar_etiqueta(c, cfg, dados or {})
    c.save()
    return caminho, nome_arquivo

# ── Histórico ────────────────────────────────────────────────────
def salvar_historico(entrada):
    historico = []
    if os.path.exists(HIST_FILE):
        try: historico = json.load(open(HIST_FILE, encoding='utf-8'))
        except: pass
    historico.insert(0, entrada)
    json.dump(historico[:100], open(HIST_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def ler_historico():
    if not os.path.exists(HIST_FILE): return []
    try: return json.load(open(HIST_FILE, encoding='utf-8'))
    except: return []

# ── Rotas ────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/config/default')
def config_default():
    return jsonify(DEFAULT_CONFIG)

@app.route('/gerar', methods=['POST'])
def gerar():
    try:
        data = request.json or {}
        cfg = {**DEFAULT_CONFIG, **(data.get('config') or {})}
        try: qtde = int(data.get('qtde', 1))
        except (TypeError, ValueError): qtde = 0
        if qtde < 1: return jsonify({'erro': 'Informe a quantidade de etiquetas'}), 400
        if qtde > 1000: return jsonify({'erro': 'Máximo de 1000 etiquetas por vez'}), 400
        dados = data.get('dados') or {}
        caminho, nome_arquivo = gerar_pdf_arquivo(qtde, cfg, dados)
        salvar_historico({
            'id': nome_arquivo,
            'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
            'etiquetas': qtde,
            'produto': dados.get('produto') or '',
            'arquivo': caminho,
            'nome_arquivo': nome_arquivo,
        })
        return send_file(caminho, as_attachment=True, download_name='etiquetas.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/historico')
def historico():
    return jsonify(ler_historico())

@app.route('/historico/download/<nome_arquivo>')
def download_historico(nome_arquivo):
    caminho = os.path.join(PDFS_DIR, nome_arquivo)
    if not os.path.exists(caminho):
        return jsonify({'erro': 'Arquivo não encontrado. PDFs são mantidos por 7 dias.'}), 404
    return send_file(caminho, as_attachment=True, download_name=nome_arquivo, mimetype='application/pdf')

@app.route('/historico/<id>', methods=['DELETE'])
def deletar_historico(id):
    historico = ler_historico()
    historico = [h for h in historico if h.get('id') != id]
    json.dump(historico, open(HIST_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return jsonify({'ok': True})
