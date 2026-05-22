from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
from datetime import datetime
import base64
import requests

app = Flask(__name__, template_folder='templates')
CORS(app)

# ===================== CONFIGURAÇÕES =====================

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ===================== MONGODB =====================

MONGO_URI = "SUA_URI_MONGODB"

client = MongoClient(MONGO_URI)

db = client["registros_db"]
colecao = db["registros"]

# ===================== LOCATIONIQ =====================

LOCATIONIQ_API_KEY = 'SUA_API_KEY'

# ===================== FUNÇÕES =====================

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

            return jsonify({
                "erro": "Dados JSON inválidos ou vazios."
            }), 400

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        foto_base64 = data.get('foto')

        print(
            f"📍 Recebido → Lat: {latitude}, Lon: {longitude}"
        )

        if not latitude or not longitude or not foto_base64:
            return jsonify({
                "erro": "Faltam dados."
            }), 400

        # ===================== ENDEREÇO =====================

        endereco_info = obter_endereco(latitude, longitude)

        # ===================== FOTO =====================

        try:
            if ',' in foto_base64:
                header, img_data = foto_base64.split(',', 1)
            else:
                img_data = foto_base64

            foto_bytes = base64.b64decode(img_data)

        except Exception as e:
            print("❌ Erro ao decodificar foto:", e)

            return jsonify({
                "erro": "Foto inválida"
            }), 400

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"registro_{timestamp}.jpg"

        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )

        with open(filepath, 'wb') as f:
            f.write(foto_bytes)

        # ===================== REGISTRO =====================

        registro = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco": endereco_info.get("endereco_completo"),
            "fonte_endereco": endereco_info.get("fonte"),
            "foto": filename
        }

        # ===================== SALVA NO MONGODB =====================

        colecao.insert_one(registro)

        print(f"✅ Registro salvo no MongoDB! Foto: {filename}")

        return jsonify({
            "mensagem": "Registro realizado com sucesso!",
            "foto": filename,
            "endereco": endereco_info.get("endereco_completo"),
            "fonte": endereco_info.get("fonte")
        })

    except Exception as e:
        print("❌ ERRO GERAL:", str(e))

        import traceback
        traceback.print_exc()

        return jsonify({
            "erro": f"Erro interno: {str(e)}"
        }), 500

# ===================== SERVIDOR =====================

if __name__ == '__main__':
    print("🚀 Servidor rodando...")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
