from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
from datetime import datetime
import base64
import requests

app = Flask(__name__, template_folder='templates')

# ===================== CONFIGURAÇÕES =====================
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

REGISTROS_FILE = 'registros.json'

LOCATIONIQ_API_KEY = 'pk.c0ba6d710c4ffc32ce1b37b22774810a'

# ===================== FUNÇÕES =====================
def carregar_registros():
    if os.path.exists(REGISTROS_FILE):
        with open(REGISTROS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_registro(registro):
    registros = carregar_registros()
    registros.append(registro)
    with open(REGISTROS_FILE, 'w', encoding='utf-8') as f:
        json.dump(registros, f, ensure_ascii=False, indent=4)

def obter_endereco(latitude, longitude):
    print(f"\n🔍 Tentando obter endereço para: {latitude}, {longitude}")

    try:
        url = "https://us1.locationiq.com/v1/reverse"
        params = {
            'key': LOCATIONIQ_API_KEY,
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'accept-language': 'pt',
            'addressdetails': 1,
            'zoom': 18
        }
        
        response = requests.get(url, params=params, timeout=10)
        print(f"LocationIQ Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            endereco = data.get('display_name', 'Não encontrado')
            print(f"✅ LocationIQ sucesso: {endereco[:120]}...")
            return {
                "endereco_completo": endereco,
                "fonte": "LocationIQ"
            }
    except Exception as e:
        print(f"❌ Erro LocationIQ: {e}")

    return {
        "endereco_completo": "Não foi possível obter o endereço",
        "fonte": "Falha"
    }

# ===================== ROTAS =====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    try:
        print("📥 Requisição recebida - Content-Type:", request.content_type)
        
        data = request.get_json(silent=True)
        if data is None:
            raw_data = request.get_data(as_text=True)
            print("❌ Dados recebidos (raw):", raw_data[:300])
            return jsonify({"erro": "Dados JSON inválidos ou vazios. Verifique o envio do frontend."}), 400

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        foto_base64 = data.get('foto')

        print(f"📍 Recebido → Lat: {latitude}, Lon: {longitude}, Foto: {len(foto_base64) if foto_base64 else 0} caracteres")

        if not latitude or not longitude or not foto_base64:
            return jsonify({"erro": "Faltam dados: latitude, longitude ou foto"}), 400

        # Obtém endereço
        endereco_info = obter_endereco(latitude, longitude)

        # Salva a foto
        try:
            if ',' in foto_base64:
                header, img_data = foto_base64.split(',', 1)
            else:
                img_data = foto_base64
            foto_bytes = base64.b64decode(img_data)
        except Exception as e:
            print("❌ Erro ao decodificar foto:", e)
            return jsonify({"erro": "Foto inválida (base64 mal formado)"}), 400

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"registro_{timestamp}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        with open(filepath, 'wb') as f:
            f.write(foto_bytes)

        # Salva registro
        registro = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco": endereco_info.get("endereco_completo"),
            "fonte_endereco": endereco_info.get("fonte"),
            "foto": filename
        }

        salvar_registro(registro)

        print(f"✅ Registro salvo com sucesso! Foto: {filename}")

        return jsonify({
            "mensagem": "Registro realizado com sucesso!",
            "foto": filename,
            "endereco": endereco_info.get("endereco_completo"),
            "fonte": endereco_info.get("fonte")
        })

    except Exception as e:
        print("❌ ERRO GERAL NO SERVIDOR:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro interno no servidor: {str(e)}"}), 500

if __name__ == '__main__':
    print("🚀 Servidor rodando em http://127.0.0.1:5000")
    print("Verifique os logs no terminal para diagnosticar o problema.")
    app.run(debug=True, host='0.0.0.0', port=5000)
