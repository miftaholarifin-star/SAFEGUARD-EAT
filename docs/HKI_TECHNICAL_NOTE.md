# Catatan Teknis HKI SAFEGUARD EAT

## 1. Identitas

- Nama program: SAFEGUARD EAT
- Versi: 1.0.0
- Tahun pada dokumen: 2025
- Jenis ciptaan yang dituju: Program Komputer
- Tim: JOSJIS
- Pemegang Hak Cipta: Telkom University Purwokerto

## 2. Ruang lingkup implementasi

Kode dalam repositori mewujudkan ekspresi program berikut:

1. struktur data batch, telemetri, gizi, pengiriman, evaluasi, dan audit;
2. API untuk merekam dan membaca siklus batch pangan;
3. quality gate deterministik dengan kebijakan konfigurabel;
4. QR token untuk akses traceability publik;
5. hash-chain SHA-256 untuk mendeteksi perubahan catatan;
6. dashboard web untuk menjalankan alur demonstrasi;
7. smart contract escrow referensi;
8. unit test, dokumentasi, dan contoh data sintetis.

Hak Cipta melindungi ekspresi kode, struktur program, dokumentasi, dan antarmuka yang orisinal. Hak Cipta tidak memberi monopoli atas gagasan umum blockchain, IoT, QR code, traceability, quality gate, atau Program MBG.

## 3. Matriks klaim dan bukti

| Komponen pada lampiran | Bukti dalam repositori | Status |
|---|---|---|
| Registrasi batch dan QR | API, SQLite, QR token | Diimplementasikan |
| Monitoring IoT | Endpoint telemetri dan log | Diimplementasikan sebagai penerima data sintetis |
| Verifikasi gizi | Endpoint dan tabel nutrition | Diimplementasikan sebagai pencatatan hasil verifikasi |
| Ketepatan distribusi | Data jadwal, penerimaan, dan kalkulasi delay | Diimplementasikan |
| Quality gate | `quality_engine.py` | Diimplementasikan |
| Audit integritas | Hash-chain lokal SHA-256 | Diimplementasikan |
| Dashboard multi-pihak | Dashboard demonstrasi | Sebagian, tanpa autentikasi multi-peran |
| Smart contract | Kontrak Solidity referensi | Tersedia, belum diaudit atau diterapkan |
| Blockchain terdistribusi | Tidak ada node atau transaksi jaringan | Belum diimplementasikan |
| IoT fisik dan GPS | Tidak ada perangkat dan data koordinat | Belum diimplementasikan |
| Pembayaran otomatis | Hanya rekomendasi quality gate | Belum diimplementasikan |
| Predictive analytics | Tidak ada model, data latih, atau metrik | Belum diimplementasikan |
| Integrasi laboratorium | Referensi hasil verifikasi manual | Belum diimplementasikan |

## 4. Koreksi teknis penting

Repositori menggunakan istilah `hash-chain lokal` dan tidak menyebutnya blockchain produksi. Ini menjaga konsistensi antara bukti kode dan klaim.

Status quality gate tidak memindahkan dana. Sistem hanya menghasilkan rekomendasi. Kontrak Solidity dipisahkan dan diberi peringatan audit agar kode demonstrasi tidak dianggap siap digunakan dengan dana nyata.

Ambang suhu, keterlambatan, dan gizi berasal dari draf. Ambang tersebut diklasifikasikan sebagai konfigurasi ilustratif. Penerapan nyata harus memakai parameter spesifik produk dan persetujuan otoritas.

## 5. Reproduksibilitas

Perintah pengujian:

```bash
python -m unittest discover -s backend/tests -v
```

Pengujian memeriksa:

- batch patuh dan tidak patuh;
- bukti yang belum lengkap;
- sifat eksklusif ambang keterlambatan 30 menit;
- determinisme hash;
- deteksi manipulasi payload;
- alur SQLite end-to-end;
- validitas QR token;
- respons API dan status 404.

## 6. Bukti versi untuk pengajuan

Simpan bukti berikut:

1. URL repositori;
2. URL commit permanen;
3. arsip ZIP rilis;
4. hash SHA-256 arsip;
5. hasil GitHub Actions;
6. tangkapan layar cover dan dashboard;
7. lampiran HKI yang konsisten dengan fitur aktual.

Cabang `main` dapat berubah. Gunakan URL commit tetap sebagai tautan bukti pada dokumen pengajuan.

## 7. Catatan data sensitif

Repositori hanya memuat data sintetis. Jangan mengunggah identitas siswa, orang tua, penerima, petugas, koordinat rinci, kredensial, rekam kesehatan, atau data transaksi riil ke repositori publik.
