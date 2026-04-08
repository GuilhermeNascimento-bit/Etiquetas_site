import os, re, json, datetime, tempfile, base64
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

app = Flask(__name__)
CORS(app)

W, H      = 90*mm, 29*mm
MARGEM    = 1.5*mm
AREA_W    = W - 2*MARGEM
FAIXA_H   = 8.5*mm
NOME_LOJA = "DILIONE FITNESS"
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

def desenhar_etiqueta(c, nome, cor, tam, preco):
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.rect(0, H - FAIXA_H, W, FAIXA_H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGEM, H - FAIXA_H + 2.8*mm, NOME_LOJA)
    info_faixa = " | ".join(filter(None, [cor, tam]))
    if info_faixa:
        c.setFont("Helvetica", 5.5)
        c.drawRightString(W - MARGEM, H - FAIXA_H + 2.8*mm, info_faixa)
    nome_lines = wrap_text(c, nome.upper(), "Helvetica-Bold", 6.5, AREA_W)
    c.setFillColor(colors.black)
    y_nome = H - FAIXA_H - 4.5*mm
    for i, line in enumerate(nome_lines[:2]):
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(MARGEM, y_nome - i*3.8*mm, line)
    detalhes = []
    if cor: detalhes.append(f"Cor: {cor}")
    if tam: detalhes.append(f"Tam: {tam}")
    if detalhes:
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor('#444444'))
        y_det = H - FAIXA_H - (4.5 + min(len(nome_lines),2)*3.8)*mm
        c.drawString(MARGEM, y_det, "   |   ".join(detalhes))
    c.setStrokeColor(colors.HexColor('#CCCCCC'))
    c.setLineWidth(0.4)
    c.line(MARGEM, 7.2*mm, W-MARGEM, 7.2*mm)
    preco_fmt = f"R$ {preco}" if not str(preco).startswith("R$") else str(preco)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEM, 2.8*mm, preco_fmt)
    c.setFont("Helvetica", 5)
    c.setFillColor(colors.HexColor('#888888'))
    c.drawRightString(W-MARGEM, 2.8*mm, "PRECO SUGERIDO")
    c.showPage()

def gerar_pdf_arquivo(produtos):
    nome_arquivo = f"etiquetas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho = os.path.join(PDFS_DIR, nome_arquivo)
    c = canvas.Canvas(caminho, pagesize=(W, H))
    total = 0
    for p in produtos:
        for _ in range(int(p.get('qtde', 1))):
            desenhar_etiqueta(c, p['nome'], p.get('cor',''), p.get('tam',''), p['preco'])
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
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/gerar', methods=['POST'])
def gerar():
    try:
        produtos = request.json.get('produtos', [])
        if not produtos: return jsonify({'erro': 'Nenhum produto'}), 400
        caminho, total, nome_arquivo = gerar_pdf_arquivo(produtos)
        salvar_historico({
            'id': nome_arquivo,
            'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
            'produtos': len(produtos),
            'etiquetas': total,
            'arquivo': caminho,
            'nome_arquivo': nome_arquivo,
            'lista': [{'nome': p['nome'], 'cor': p.get('cor',''), 'tam': p.get('tam',''),
                       'preco': p['preco'], 'qtde': p.get('qtde',1)} for p in produtos]
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
    """Usa Claude AI para extrair produtos de qualquer NF em PDF"""
    try:
        import anthropic
        f = request.files.get('arquivo')
        if not f: return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

        # Lê o PDF como base64
        pdf_bytes = f.read()
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')

        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

        prompt = """Analise esta nota fiscal / romaneio e extraia TODOS os produtos listados.

Para cada produto, retorne um JSON array com objetos no formato:
{
  "nome": "nome do produto",
  "cor": "cor (ou vazio se não houver)",
  "tam": "tamanho como G, M, P, GG (ou vazio se não houver)",
  "preco": "preço sugerido de venda no formato 00,00 (use o maior preço da linha, geralmente 'preço sugerido' ou 'valor varejo')",
  "qtde": quantidade como número inteiro
}

IMPORTANTE:
- Retorne APENAS o JSON array, sem texto adicional, sem markdown, sem explicações
- Use o preço SUGERIDO DE VENDA (não o preço de custo/atacado)
- Se houver cor e tamanho juntos na mesma linha, separe em campos diferentes
- A quantidade deve ser um número inteiro
- Se não encontrar preço sugerido, use o maior valor da linha"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )

        texto = response.content[0].text.strip()
        # Limpa markdown se houver
        texto = re.sub(r'```json|```', '', texto).strip()
        produtos = json.loads(texto)

        # Normaliza
        resultado = []
        for p in produtos:
            if not p.get('nome'): continue
            preco = str(p.get('preco', '0')).replace('.', ',')
            if ',' not in preco:
                preco = preco + ',00'
            resultado.append({
                'nome': str(p.get('nome', '')).strip(),
                'cor':  str(p.get('cor', '')).strip(),
                'tam':  str(p.get('tam', '')).strip(),
                'preco': preco,
                'qtde': int(p.get('qtde', 1))
            })

        return jsonify({'produtos': resultado, 'total': len(resultado)})

    except json.JSONDecodeError as e:
        return jsonify({'erro': f'Erro ao interpretar resposta da IA: {str(e)}', 'raw': texto}), 500
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
