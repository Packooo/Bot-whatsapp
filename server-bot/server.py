from flask import Flask, request, abort
import json
import requests # <-- Tambahkan ini

app = Flask(__name__)
VERIFY_TOKEN = "123"


# URL tempat server Node.js Anda berjalan
WHATSAPP_BOT_URL = "http://localhost:3000/kirim-pesan" # <-- Ganti port jika perlu

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # ... (Kode verifikasi GET tetap sama) ...
        token_sent = request.args.get("hub.verify_token")
        if token_sent == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return 'Verification token mismatch', 403

    elif request.method == 'POST':
        data = request.get_json()
        print("Menerima data dari Facebook:")
        print(json.dumps(data, indent=2))
        
        try:
            # Pastikan ini adalah notifikasi 'feed' dari 'page'
            if data.get('object') == 'page':
                change = data['entry'][0]['changes'][0]
                
                if change.get('field') == 'feed':
                    post_value = change['value']
                    
                    # Ambil teks postingan (jika ada)
                    pesan = post_value.get('message', '') # Default ke string kosong jika tidak ada teks
                    
                    # Ambil URL gambar (jika ada)
                    # Untuk postingan foto, biasanya ada di 'link' atau di dalam 'attachments'
                    # Kita cek 'link' dulu karena lebih umum untuk postingan foto tunggal
                    url_gambar = post_value.get('link', None)
                    
                    # Periksa apakah ini event penambahan foto
                    if post_value.get('item') == 'photo':
                        # Untuk postingan foto, 'message' mungkin kosong, jadi kita buat teks default
                        if not pesan:
                             pesan = "Ada foto baru di Fanspage!"
                    
                    # Hanya proses jika ada pesan atau gambar
                    if pesan or url_gambar:
                        payload = {
                            'groupId': '120363417848982331@g.us', # <-- Ganti dengan ID Grup
                            'message': pesan,
                            'imageUrl': url_gambar # Kirim None jika tidak ada gambar
                        }
                        
                        print(f"Mengirim ke bot WhatsApp: Pesan='{pesan}', Gambar='{url_gambar}'")
                        requests.post(WHATSAPP_BOT_URL, json=payload)

        except (KeyError, IndexError):
            pass # Abaikan jika struktur data tidak sesuai

        return 'Data diterima', 200
    else:
        abort(405)

if __name__ == '__main__':
    app.run(port=5000, debug=True)