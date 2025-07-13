// bot.js

const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js'); // <-- Tambahkan MessageMedia
const qrcode = require('qrcode-terminal');

// ... (Inisialisasi Express dan Client WhatsApp tetap sama) ...
const app = express();
app.use(express.json());
const PORT = 3000;

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true, // Pastikan berjalan di mode headless
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', qr => {
    console.log('Scan QR Code ini dengan WhatsApp Anda:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ WhatsApp Client sudah siap!');
});

client.on('message', msg => {
    if (msg.body == '!ping') {
        msg.reply('pong');
    }
});

client.initialize(); 

client.on('message', async (msg) => {
    // Cek apakah pesan yang masuk adalah '!infogrup'
    if (msg.body.toLowerCase() === '!infogrup') {
        const chat = await msg.getChat();
        // Cek apakah pesan ini dikirim di dalam sebuah grup
        if (chat.isGroup) {
            console.log(`Perintah !infogrup diterima di grup: ${chat.name}`);
            
            // Balas pesan dengan informasi nama grup dan ID-nya
            msg.reply(
`*Informasi Grup*
Nama: ${chat.name}
ID Grup: ${chat.id._serialized}`
            );
        } else {
            msg.reply('Perintah ini hanya bisa digunakan di dalam grup.');
        }
    }
});



// Endpoint untuk menerima perintah dari server Python
app.post('/kirim-pesan', async (req, res) => {
    // Ambil message dan imageUrl dari body
    const { groupId, message, imageUrl } = req.body;

    if (!groupId) {
        return res.status(400).json({ error: 'groupId diperlukan' });
    }

    try {
        // Cek apakah ada URL gambar
        if (imageUrl) {
            console.log(`Mengunduh gambar dari: ${imageUrl}`);
            // Unduh media dari URL
            const media = await MessageMedia.fromUrl(imageUrl, { unsafeMime: true });
            
            console.log(`Mengirim gambar dengan caption "${message}" ke grup ${groupId}`);
            // Kirim gambar dengan teks sebagai caption
            await client.sendMessage(groupId, media, { caption: message });

        } else if (message) {
            // Jika tidak ada gambar, kirim teks biasa
            console.log(`Mengirim teks "${message}" ke grup ${groupId}`);
            await client.sendMessage(groupId, message);
        }
        
        res.status(200).json({ success: true, message: 'Pesan berhasil diproses.' });
    } catch (error) {
        console.error('Gagal memproses pesan:', error);
        res.status(500).json({ success: false, message: 'Gagal memproses pesan.' });
    }
});


// Jalankan server Express
app.listen(PORT, () => {
    console.log(`🚀 Server Bot WhatsApp berjalan di http://localhost:${PORT}`);
});