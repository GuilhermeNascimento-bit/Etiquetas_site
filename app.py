import os, re, json, datetime, tempfile
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

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/gerar', methods=['POST'])
def gerar():
    try:
        produtos = request.json.get('produtos', [])
        if not produtos: return jsonify({'erro': 'Nenhum produto'}), 400
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.close()
        c = canvas.Canvas(tmp.name, pagesize=(W, H))
        total = 0
        for p in produtos:
            for _ in range(int(p.get('qtde', 1))):
                desenhar_etiqueta(c, p['nome'], p.get('cor',''), p.get('tam',''), p['preco'])
                total += 1
        c.save()
        return send_file(tmp.name, as_attachment=True, download_name='etiquetas.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
