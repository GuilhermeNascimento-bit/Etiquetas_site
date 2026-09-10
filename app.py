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

# Configuração padrão da etiqueta — NÃO alterar sem querer mudar o
# comportamento default (90x29mm, faixa preta, "DILIONE FITNESS").
DEFAULT_CONFIG = {
    'largura_mm': 90,
    'altura_mm': 29,
    'nome_loja': 'DILIONE FITNESS',
    'cor_faixa': '#000000',
    'cor_texto_faixa': '#FFFFFF',
    'logo_base64': None,
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

def desenhar_etiqueta(c, p, tipo, cfg):
    W = cfg['largura_mm'] * mm
    H = cfg['altura_mm'] * mm
    MARGEM  = 1.5 * mm
    AREA_W  = W - 2*MARGEM
    # escala tipográfica: cresce com a altura, mas com limites pra não gerar
    # texto absurdo em etiquetas muito pequenas/grandes.
    escala  = max(0.6, min(2.2, cfg['altura_mm'] / 29.0))
    # espaçamentos entre blocos crescem mais devagar que a fonte — evita o
    # "vão" enorme no meio da etiqueta quando a altura é bem maior que 29mm.
    gap_escala = 1 + (escala - 1) * 0.4
    FAIXA_H = H * (8.5/29.0)
    cor_faixa       = colors.HexColor(cfg.get('cor_faixa') or '#000000')
    cor_texto_faixa = colors.HexColor(cfg.get('cor_texto_faixa') or '#FFFFFF')
    nome_loja       = cfg.get('nome_loja') or 'DILIONE FITNESS'

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
            logo_h = FAIXA_H - 2*(1.2*mm*escala)
            logo_w = logo_h * (iw/ih)
            logo_y = H - FAIXA_H + (FAIXA_H - logo_h)/2
            c.drawImage(img, MARGEM, logo_y, width=logo_w, height=logo_h,
                        mask='auto', preserveAspectRatio=True)
            text_x = MARGEM + logo_w + 1.5*mm
        except Exception:
            pass

    c.setFillColor(cor_texto_faixa)
    c.setFont("Helvetica-Bold", 7.5*escala)
    c.drawString(text_x, H - FAIXA_H + 2.8*mm*escala, nome_loja)

    if tipo == 'roupa':
        info_faixa = " | ".join(filter(None, [p.get('cor',''), p.get('tam','')]))
        if info_faixa:
            c.setFont("Helvetica", 5.5*escala)
            c.drawRightString(W - MARGEM, H - FAIXA_H + 2.8*mm*escala, info_faixa)

    nome_lines = wrap_text(c, p['nome'].upper(), "Helvetica-Bold", 6.5*escala, AREA_W)[:2]

    detalhes = []
    if tipo == 'roupa':
        if p.get('cor'): detalhes.append(f"Cor: {p['cor']}")
        if p.get('tam'): detalhes.append(f"Tam: {p['tam']}")
    else:
        if p.get('fabricacao'): detalhes.append(f"Fab: {p['fabricacao']}")
        if p.get('lote'): detalhes.append(f"Lote: {p['lote']}")

    if tipo == 'roupa':
        preco = p.get('preco', '')
        valor_txt = f"R$ {preco}" if not str(preco).startswith("R$") else str(preco)
        rotulo = "PRECO SUGERIDO"
    else:
        valor_txt = f"VAL: {p.get('validade','')}"
        rotulo = "DATA DE VALIDADE"

    # Bloco de conteúdo (nome + detalhes + linha + valor) é montado com
    # distâncias fixas entre si e depois centralizado verticalmente no
    # espaço abaixo da faixa — assim etiquetas mais altas ganham margem
    # extra em cima/embaixo do bloco, em vez de um vão solto no meio.
    S1, LINE_NOME, S3, S4, S5, S6 = (4.5*mm, 3.8*mm, 3.8*mm, 5.0*mm, 4.4*mm, 2.8*mm)
    extra_linhas = max(0, len(nome_lines) - 1)
    linhas_h = LINE_NOME*escala*extra_linhas       # altura do nome (fixa, nunca encolhe)
    gaps_base = S1 + S3 + S4 + S5 + S6
    gaps_h = gaps_base * gap_escala
    disponivel = H - FAIXA_H
    # Se mesmo os espaçamentos "encolhidos" não couberem (nome com 2 linhas
    # numa etiqueta baixa), reduz só os espaçamentos até caber — nunca deixa
    # a linha/valor vazarem pra fora ou colidirem com o texto.
    if gaps_h > 0 and (linhas_h + gaps_h) > disponivel:
        gap_escala *= max(0, disponivel - linhas_h) / gaps_h
        gaps_h = gaps_base * gap_escala
    content_h = linhas_h + gaps_h
    top_pad = max(0, (disponivel - content_h) / 2)

    cursor = H - FAIXA_H - top_pad
    cursor -= S1*gap_escala
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 6.5*escala)
    c.drawString(MARGEM, cursor, nome_lines[0] if nome_lines else '')
    if len(nome_lines) > 1:
        cursor -= LINE_NOME*escala
        c.drawString(MARGEM, cursor, nome_lines[1])
    cursor -= S3*gap_escala
    if detalhes:
        c.setFont("Helvetica", 6*escala)
        c.setFillColor(colors.HexColor('#444444'))
        c.drawString(MARGEM, cursor, "   |   ".join(detalhes))
    cursor -= S4*gap_escala
    y_linha = cursor
    c.setStrokeColor(colors.HexColor('#CCCCCC'))
    c.setLineWidth(0.4)
    c.line(MARGEM, y_linha, W-MARGEM, y_linha)
    cursor -= S5*gap_escala

    rotulo_font = 5*escala
    rotulo_w = c.stringWidth(rotulo, "Helvetica", rotulo_font)
    valor_font = 12*escala
    valor_w = c.stringWidth(valor_txt, "Helvetica-Bold", valor_font)
    espaco_livre = AREA_W - rotulo_w - 2*mm
    if espaco_livre > 0 and valor_w > espaco_livre:
        valor_font = max(6, valor_font * (espaco_livre/valor_w))

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", valor_font)
    c.drawString(MARGEM, cursor, valor_txt)
    c.setFont("Helvetica", rotulo_font)
    c.setFillColor(colors.HexColor('#888888'))
    c.drawRightString(W-MARGEM, cursor, rotulo)
    c.showPage()

def gerar_pdf_arquivo(produtos, tipo='roupa', cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    W = cfg['largura_mm'] * mm
    H = cfg['altura_mm'] * mm
    nome_arquivo = f"etiquetas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    caminho = os.path.join(PDFS_DIR, nome_arquivo)
    c = canvas.Canvas(caminho, pagesize=(W, H))
    total = 0
    for p in produtos:
        for _ in range(int(p.get('qtde', 1))):
            desenhar_etiqueta(c, p, tipo, cfg)
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
        tipo = data.get('tipo', 'roupa')
        cfg = {**DEFAULT_CONFIG, **(data.get('config') or {})}
        if not produtos: return jsonify({'erro': 'Nenhum produto'}), 400
        caminho, total, nome_arquivo = gerar_pdf_arquivo(produtos, tipo, cfg)
        salvar_historico({
            'id': nome_arquivo,
            'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
            'tipo': tipo,
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