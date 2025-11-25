from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
|#
app = Flask(__name__)
CORS(app)

API_KEY = "CHAVE_API_AQUI"

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

def verify_fact(query):
    """
    Verifica a veracidade de uma afirmação usando um LLM e pesquisa na web.
    """
    if not API_KEY or API_KEY == "SUA_CHAVE_AQUI":
        return "Erro: A chave de API não foi configurada. Por favor, adicione sua chave de API.", []

    try:
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"Verifique a seguinte afirmação com base em fontes da web. Retorne APENAS um objeto JSON com duas chaves: 'veredicto' e 'confianca'. O veredicto deve ser 'Fato Comprovado', 'Informação Controvertida' ou 'Teoria sem Base Factual'. A confiança deve ser 'Alta', 'Média' ou 'Baixa'.\n\nAfirmação: {query}"
                }]
            }],
            "tools": [{"google_search": {}}]
        }

        # Realiza a chamada à API do Gemini
        response = requests.post(f"{API_URL}?key={API_KEY}", json=payload)
        response.raise_for_status()

        result = response.json()
        candidate = result.get('candidates', [{}])[0]
        if not candidate or not candidate.get('content') or not candidate['content'].get('parts'):
            return "Erro: A resposta da API não contém um candidato válido.", []
            
        text = candidate['content']['parts'][0].get('text', '')

        # Adiciona um print para depuração, mostrando a resposta bruta
        print(f"Resposta bruta da API: {text}")

        # Tenta encontrar a parte do JSON na resposta, caso ela não seja um JSON puro
        try:
            json_start = text.find('{')
            json_end = text.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_string = text[json_start:json_end+1]
                verdict_data = json.loads(json_string)
            else:
                return "Erro: O formato da resposta da API não é JSON.", []
        except json.JSONDecodeError:
            # Caso a API retorne um texto que não seja um JSON, trata como erro
            return "Erro: O formato da resposta da API não é JSON.", []

        # Extrai as fontes
        sources = []
        grounding_metadata = candidate.get('groundingMetadata', {})
        grounding_attributions = grounding_metadata.get('groundingAttributions', [])
        for attribution in grounding_attributions:
            source = attribution.get('web', {})
            if source.get('uri') and source.get('title'):
                sources.append({
                    'uri': source['uri'],
                    'title': source['title']
                })

        return verdict_data, sources

    except requests.exceptions.RequestException as e:
        return f"Erro ao acessar a API: {e}", []
    except Exception as e:
        return f"Ocorreu um erro: {e}", []


@app.route('/verify', methods=['POST'])
def handle_verification():
    """
    Endpoint para a nova API de verificação de fatos.
    """
    try:
        data = request.get_json(force=True)
        query = data.get('query', '')

        if not query:
            return jsonify({"error": "Nenhuma pergunta ou afirmação fornecida."}), 400
        
        response_data, sources = verify_fact(query)

        # Se response_data é uma string, é uma mensagem de erro
        if isinstance(response_data, str):
            return jsonify({
                "response": response_data,
                "sources": sources
            })

        return jsonify({
            "response": response_data,
            "sources": sources
        })

    except Exception as e:
        # Se ocorrer um erro, ele será capturado e retornado ao cliente.
        print(f"Erro na requisição: {e}")
        return jsonify({"error": f"Ocorreu um erro interno. Detalhes: {e}"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)






