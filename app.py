import os, re, json, datetime, tempfile, base64, io
import pypdf
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# No topo do app.py, logo após os imports:
CORES = [
    'ROXO TRENDY', 'CROMO REFLETIVO', 'NAUTICO', 'BRANCO', 'DESEJO',
    'PRETO', 'SIDERAL', 'PINK', 'MARFIM', 'VIOLETA', 'RUBI',
    'BANDANA', 'LIQUOR', 'ORVALHO', 'ROSEWOOD',
]
app = Flask(__name__)
CORS(app)

# Configuração padrão da etiqueta (modelo único/universal).
DEFAULT_CONFIG = {
    'largura_mm': 90,
    'altura_mm': 42,
    'nome_loja': 'DILIONE FITNESS',
    'cor_faixa': '#000000',
    'cor_texto_faixa': '#FFFFFF',
    'cor_destaque': '#000000',
    'logo_base64': None,
    'fonte_nome': 9,
    'fonte_destaque': 16,
    'fonte_detalhe': 7,
}
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
HIST_FILE = os.path.join(BASE_DIR, "historico.json")
PDFS_DIR  = os.path.join(BASE_DIR, "pdfs_gerados")
os.makedirs(PDFS_DIR, exist_ok=True)

# ── Helpers PDF ──────────────────────────────────────────────────
def wrap_text(c, text, font, size, max_width):
    c.setFont(font, size)
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

def desenhar_etiqueta(c, p, cfg):
    """Etiqueta universal: nome do produto + lista livre de campos
    (rotulo/valor), cada um marcado ou não como "destaque". Campos em
    destaque são desenhados grandes, em colunas do mesmo tamanho, todos
    com o mesmo peso visual (ex.: Fabricação e Validade lado a lado)."""
    W = cfg['largura_mm'] * mm
    H = cfg['altura_mm'] * mm
    MARGEM  = 1.5 * mm
    AREA_W  = W - 2*MARGEM
    FAIXA_H = H * (8.5/29.0)

    cor_faixa       = colors.HexColor(cfg.get('cor_faixa') or '#000000')
    cor_texto_faixa = colors.HexColor(cfg.get('cor_texto_faixa') or '#FFFFFF')
    cor_destaque    = colors.HexColor(cfg.get('cor_destaque') or '#000000')
    nome_loja       = cfg.get('nome_loja') or ''

    fonte_nome     = float(cfg.get('fonte_nome') or 9)
    fonte_destaque = float(cfg.get('fonte_destaque') or 16)
    fonte_detalhe  = float(cfg.get('fonte_detalhe') or 7)

    # Fundo + faixa superior (logo/nome da loja)
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(cor_faixa)
    c.rect(0, H - FAIXA_H, W, FAIXA_H, fill=1, stroke=0)

    text_x = MARGEM
    logo_b64 = cfg.get('logo_base64')
    if logo_b64:
        try:
            b64data = logo_b64.split(',', 1)[1] if ',' in logo_b64 else logo_b64
            img = ImageReader(io.BytesIO(base64.b64decode(b64data)))
            iw, ih = img.getSize()
            logo_h = FAIXA_H - 2.4*mm
            logo_w = logo_h * (iw/ih)
            logo_y = H - FAIXA_H + (FAIXA_H - logo_h)/2
            c.drawImage(img, MARGEM, logo_y, width=logo_w, height=logo_h,
                        mask='auto', preserveAspectRatio=True)
            text_x = MARGEM + logo_w + 1.5*mm
        except Exception:
            pass

    if nome_loja:
        fonte_loja = max(6, min(13, cfg['altura_mm']*0.3))
        c.setFillColor(cor_texto_faixa)
        c.setFont("Helvetica-Bold", fonte_loja)
        c.drawString(text_x, H - FAIXA_H + FAIXA_H*0.36, nome_loja)

    # Campos: os marcados como destaque viram colunas grandes; o resto
    # vira uma linha pequena de detalhes logo abaixo do nome.
    campos    = p.get('campos') or []
    destaques = [x for x in campos if x.get('destaque') and (x.get('valor') or x.get('rotulo'))]
    detalhes  = [x for x in campos if not x.get('destaque') and (x.get('valor') or x.get('rotulo'))]

    nome_lines = wrap_text(c, (p.get('nome') or '').upper(), "Helvetica-Bold", fonte_nome, AREA_W)[:2]

    def altura_necessaria(fn, fd, fx, fator=1.0):
        h = 2.6*mm*fator + fn*fator*0.85
        if len(nome_lines) > 1: h += fn*fator*1.2
        h += fn*fator*0.55 + 1.6*mm*fator
        if detalhes: h += fd*fator*0.8 + fd*fator*0.4 + 1.6*mm*fator
        h += 1.4*mm*fator + 2.6*mm*fator
        if destaques:
            legenda = max(5, fd*0.82)*fator
            h += legenda*0.85 + legenda*0.4 + 0.8*mm*fator + fx*fator*0.78
        return h

    # Espaçamentos e fontes são as escolhas do usuário; só encolhem
    # (proporcionalmente, texto e espaço juntos) se não couberem na
    # altura da etiqueta — nunca deixam o conteúdo vazar ou sobrepor.
    disponivel = H - FAIXA_H
    alvo = max(0, disponivel - 1.2*mm)   # margem fixa de segurança no rodapé
    fator = 1.0
    necessario = altura_necessaria(fonte_nome, fonte_detalhe, fonte_destaque)
    if necessario > alvo and necessario > 0:
        fator = max(0.4, alvo / necessario)

    cursor = H - FAIXA_H - 2.6*mm*fator

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", fonte_nome*fator)
    cursor -= fonte_nome*fator*0.85
    c.drawString(MARGEM, cursor, nome_lines[0] if nome_lines else '')
    if len(nome_lines) > 1:
        cursor -= fonte_nome*fator*1.2
        c.drawString(MARGEM, cursor, nome_lines[1])
    cursor -= fonte_nome*fator*0.55 + 1.6*mm*fator

    if detalhes:
        texto_det = "   |   ".join(
            f"{d['rotulo']}: {d['valor']}" if d.get('rotulo') and d.get('valor')
            else (d.get('valor') or d.get('rotulo') or '')
            for d in detalhes
        )
        c.setFont("Helvetica", fonte_detalhe*fator)
        c.setFillColor(colors.HexColor('#555555'))
        cursor -= fonte_detalhe*fator*0.8
        c.drawString(MARGEM, cursor, texto_det)
        cursor -= fonte_detalhe*fator*0.4 + 1.6*mm*fator

    cursor -= 1.4*mm*fator
    y_linha = cursor
    c.setStrokeColor(colors.HexColor('#CCCCCC'))
    c.setLineWidth(0.5)
    c.line(MARGEM, y_linha, W-MARGEM, y_linha)
    cursor -= 2.6*mm*fator

    if destaques:
        n = len(destaques)
        col_w = AREA_W / n
        fonte_legenda = max(5, fonte_detalhe*0.82)*fator

        cursor -= fonte_legenda*0.85
        y_legenda = cursor
        c.setFont("Helvetica", fonte_legenda)
        c.setFillColor(colors.HexColor('#777777'))
        for i, d in enumerate(destaques):
            x = MARGEM + i*col_w
            c.drawString(x, y_legenda, (d.get('rotulo') or '').upper())

        cursor -= fonte_legenda*0.4 + 0.8*mm*fator
        cursor -= fonte_destaque*fator*0.78
        y_valor = cursor
        for i, d in enumerate(destaques):
            x = MARGEM + i*col_w
            max_w = col_w - (2*mm if i < n-1 else 0)
            valor_txt = d.get('valor') or ''
            f = fonte_destaque*fator
            w = c.stringWidth(valor_txt, "Helvetica-Bold", f)
            if max_w > 0 and w > max_w:
                f = max(6, f * (max_w/w))
            c.setFont("Helvetica-Bold", f)
            c.setFillColor(cor_destaque)
            c.drawString(x, y_valor, valor_txt)

    c.showPage()

def gerar_pdf_arquivo(produtos, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    W = cfg['largura_mm'] * mm
    H = cfg['altura_mm'] * mm
    nome_arquivo = f"etiquetas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    caminho = os.path.join(PDFS_DIR, nome_arquivo)
    c = canvas.Canvas(caminho, pagesize=(W, H))
    total = 0
    for p in produtos:
        for _ in range(int(p.get('qtde', 1))):
            desenhar_etiqueta(c, p, cfg)
            total += 1
    c.save()
    return caminho, total, nome_arquivo

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
        produtos = data.get('produtos', [])
        cfg = {**DEFAULT_CONFIG, **(data.get('config') or {})}
        if not produtos: return jsonify({'erro': 'Nenhum produto'}), 400
        caminho, total, nome_arquivo = gerar_pdf_arquivo(produtos, cfg)
        salvar_historico({
            'id': nome_arquivo,
            'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
            'produtos': len(produtos),
            'etiquetas': total,
            'arquivo': caminho,
            'nome_arquivo': nome_arquivo,
            'lista': produtos
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

@app.route('/importar_texto', methods=['POST'])
def importar_texto():
    try:
        texto = request.json.get('texto', '')
        produtos = []
        for linha in texto.strip().split('\n'):
            linha = linha.strip()
            if not linha or ':' not in linha: continue
            m = re.match(r'^(.+?):\s*[\d,\.]+\s*/\s*([\d,\.]+)\s*\((\d+)\)', linha)
            if m:
                preco = f"{float(m.group(2).replace(',','.')):.2f}".replace('.', ',')
                produtos.append({'nome': m.group(1).strip(), 'cor': '', 'tam': '', 'preco': preco, 'qtde': int(m.group(3))})
        return jsonify({'produtos': produtos})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/importar_xlsx', methods=['POST'])
def importar_xlsx():
    try:
        import openpyxl
        f = request.files['arquivo']
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        f.save(tmp.name)
        wb = openpyxl.load_workbook(tmp.name, data_only=True)
        ws = wb["Etiquetas"]
        produtos = []
        for row in ws.iter_rows(min_row=5, values_only=True):
            nome, cor, tam, preco, qtde = row[0], row[1], row[2], row[3], row[4]
            if not nome or not preco: continue
            try:
                produtos.append({
                    'nome': str(nome).strip(),
                    'cor':  str(cor).strip() if cor else '',
                    'tam':  str(tam).strip() if tam else '',
                    'preco': f"{float(preco):.2f}".replace('.', ','),
                    'qtde': int(qtde) if qtde else 1
                })
            except: pass
        os.unlink(tmp.name)
        return jsonify({'produtos': produtos})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/ler_nf', methods=['POST'])
def ler_nf():
    try:
        f = request.files.get('arquivo')
        if not f:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

        # 1. Extração Gratuita de Texto
        reader = pypdf.PdfReader(f)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() + "\n"

        # 2. Lógica de Parse (Extraída do seu código 'gerar_etiquetas.py')
        resultado = []
        for linha in texto_completo.split('\n'):
            linha = linha.strip()
            # Filtra apenas linhas que começam com o código de 5 dígitos (padrão da sua NF)
            if re.match(r'^\d{5}', linha):
                # Preço sugerido
                vals = re.findall(r'\d+,\d{2}', linha)
                preco_sug = vals[-1] if vals else '0,00'

                # Tamanho (G, M, P, GG)
                tam_m = re.search(r'\b(GG|G|M|P)\b\s+\d+\s+\d+,\d{2}', linha)
                tam = tam_m.group(1) if tam_m else ''

                # Cor (Busca na sua lista de CORES definida no topo)
                cor = ''
                for c in CORES:
                    if c in linha.upper():
                        cor = c
                        break

                # Quantidade
                qtde_m = re.search(r'\b(?:GG|G|M|P)\b\s+(\d+)\s+\d+,\d{2}', linha)
                qtde = int(qtde_m.group(1)) if qtde_m else 1

                # Nome do Produto (Extrai entre o código e a cor/tamanho)
                m = re.match(r'^\d{5}\s+\S+\s+\S+\s+\S+[-\s]+(.+)', linha)
                nome = m.group(1).split(tam)[0].strip() if m else "Produto"

                resultado.append({
                    'nome': nome.upper(),
                    'cor': cor,
                    'tam': tam,
                    'preco': preco_sug,
                    'qtde': qtde
                })

        # 3. Retorno IDÊNTICO ao que o seu Front-end já espera
        return jsonify({'produtos': resultado, 'total': len(resultado)})

    except Exception as e:
        return jsonify({'erro': f"Erro no processamento local: {str(e)}"}), 500
