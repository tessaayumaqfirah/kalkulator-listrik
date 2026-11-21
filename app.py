"""
Kalkulator Biaya Listrik Harian Rumah Tangga
Proyek Akhir Komputasi Awan - dibangun dengan Python + Streamlit

Rumus inti:
    Energi harian (kWh) = (Daya Watt x Jam pakai x Jumlah unit) / 1000
    Biaya harian (Rp)   = Energi harian (kWh) x Tarif per kWh

Cara menjalankan:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

# =============================================================================
# 1. KONFIGURASI & DATA DEFAULT (ubah di sini jika ingin menyesuaikan)
# =============================================================================

st.set_page_config(
    page_title="Kalkulator Biaya Listrik Harian",
    page_icon="⚡",
    layout="wide",
)

# Tarif per kWh (Rp). Tarif PLN bisa berubah, silakan cek dan perbarui nilainya.
GOLONGAN_TARIF = {
    "R-1 / 900 VA (non-subsidi)": 1352.0,
    "R-1 / 1300 VA": 1444.70,
    "R-1 / 2200 VA": 1444.70,
    "Tarif manual": None,  # pengguna mengisi sendiri
}

# Daftar perangkat umum beserta perkiraan daya (Watt)
DAFTAR_PERANGKAT = {
    "Lampu LED": 10,
    "Kipas Angin": 50,
    "TV LED": 80,
    "Kulkas": 100,
    "AC 1/2 PK": 400,
    "AC 1 PK": 800,
    "Rice Cooker": 350,
    "Mesin Cuci": 300,
    "Setrika": 350,
    "Laptop": 65,
    "Charger HP": 10,
    "Dispenser": 350,
    "Pompa Air": 125,
    "Lainnya (isi manual)": 0,
}

# Nama kolom dipusatkan di sini agar mudah diubah
KOLOM_NAMA = "Perangkat"
KOLOM_DAYA = "Daya (Watt)"
KOLOM_JAM = "Jam/Hari"
KOLOM_JUMLAH = "Jumlah"

# Contoh data awal supaya tabel tidak kosong saat pertama dibuka
DATA_AWAL = [
    {KOLOM_NAMA: "Lampu LED", KOLOM_DAYA: 10, KOLOM_JAM: 8.0, KOLOM_JUMLAH: 5},
    {KOLOM_NAMA: "Kulkas", KOLOM_DAYA: 100, KOLOM_JAM: 24.0, KOLOM_JUMLAH: 1},
    {KOLOM_NAMA: "TV LED", KOLOM_DAYA: 80, KOLOM_JAM: 5.0, KOLOM_JUMLAH: 1},
]


# =============================================================================
# 2. FUNGSI PERHITUNGAN (logika inti, terpisah dari tampilan)
# =============================================================================

def hitung_energi_kwh(daya_watt, jam, jumlah):
    """Hitung energi harian dalam kWh."""
    return (daya_watt * jam * jumlah) / 1000


def hitung_hasil(df, tarif):
    """Tambahkan kolom Energi (kWh) dan Biaya Harian (Rp) ke tabel perangkat."""
    hasil = df.copy()
    # Bersihkan data: kosong -> 0, batasi nilai agar masuk akal
    hasil[KOLOM_DAYA] = pd.to_numeric(hasil[KOLOM_DAYA], errors="coerce").fillna(0).clip(lower=0)
    hasil[KOLOM_JAM] = pd.to_numeric(hasil[KOLOM_JAM], errors="coerce").fillna(0).clip(0, 24)
    hasil[KOLOM_JUMLAH] = pd.to_numeric(hasil[KOLOM_JUMLAH], errors="coerce").fillna(0).clip(lower=0)
    hasil[KOLOM_NAMA] = hasil[KOLOM_NAMA].fillna("Tanpa nama")

    hasil["Energi (kWh)"] = hitung_energi_kwh(
        hasil[KOLOM_DAYA], hasil[KOLOM_JAM], hasil[KOLOM_JUMLAH]
    )
    hasil["Biaya Harian (Rp)"] = hasil["Energi (kWh)"] * tarif
    return hasil


def format_rupiah(angka):
    """Format angka menjadi 'Rp 12.345' (gaya penulisan Indonesia)."""
    return "Rp " + f"{angka:,.0f}".replace(",", ".")


def buat_saran_hemat(hasil):
    """Buat saran hemat sederhana berdasarkan perangkat paling boros."""
    if hasil.empty or hasil["Energi (kWh)"].sum() == 0:
        return ["Tambahkan perangkat dan jam pemakaian untuk mendapatkan saran."]

    saran = []
    total = hasil["Energi (kWh)"].sum()
    boros = hasil.sort_values("Energi (kWh)", ascending=False).iloc[0]
    persen = boros["Energi (kWh)"] / total * 100
    saran.append(
        f"Perangkat paling boros: **{boros[KOLOM_NAMA]}** "
        f"({persen:.0f}% dari total pemakaian harian)."
    )

    nama_boros = str(boros[KOLOM_NAMA]).lower()
    if "ac" in nama_boros:
        saran.append("Atur suhu AC di 24-26°C dan matikan saat tidak ada orang di ruangan.")
    elif "setrika" in nama_boros or "rice" in nama_boros or "dispenser" in nama_boros:
        saran.append("Gunakan perangkat pemanas seperlunya dan cabut dari stopkontak setelah selesai.")
    elif "lampu" in nama_boros:
        saran.append("Matikan lampu yang tidak dipakai dan pilih lampu LED berdaya rendah.")
    else:
        saran.append("Kurangi durasi pemakaian atau pertimbangkan perangkat berlabel hemat energi.")

    saran.append("Cabut charger dan perangkat standby yang tidak digunakan.")
    return saran


# =============================================================================
# 3. STATE (menyimpan tabel perangkat selama sesi berjalan)
# =============================================================================

if "df_perangkat" not in st.session_state:
    st.session_state.df_perangkat = pd.DataFrame(DATA_AWAL)


# =============================================================================
# 4. SIDEBAR: PENGATURAN TARIF
# =============================================================================

with st.sidebar:
    st.header("⚙️ Pengaturan Tarif")
    golongan = st.selectbox("Golongan tarif PLN", list(GOLONGAN_TARIF.keys()))

    if GOLONGAN_TARIF[golongan] is None:
        tarif = st.number_input("Tarif per kWh (Rp)", min_value=0.0, value=1500.0, step=10.0)
    else:
        tarif = st.number_input(
            "Tarif per kWh (Rp)", min_value=0.0, value=GOLONGAN_TARIF[golongan], step=10.0,
            help="Nilai default dapat diubah jika tarif PLN berubah.",
        )

    hari_per_bulan = st.slider("Jumlah hari per bulan", 28, 31, 30)
    st.caption("Tarif default hanya perkiraan. Sesuaikan dengan tagihan listrik Anda.")


# =============================================================================
# 5. HALAMAN UTAMA: JUDUL
# =============================================================================

st.title("⚡ Kalkulator Biaya Listrik Harian Rumah Tangga")
st.write("Masukkan perangkat listrik di rumah Anda untuk menghitung konsumsi energi dan biaya per hari.")


# =============================================================================
# 6. FORM TAMBAH PERANGKAT
# =============================================================================

st.subheader("1. Tambah Perangkat")
kol1, kol2, kol3, kol4, kol5 = st.columns([2.5, 1.5, 1.5, 1.2, 1])

with kol1:
    pilihan = st.selectbox("Pilih perangkat", list(DAFTAR_PERANGKAT.keys()))
with kol2:
    daya_input = st.number_input("Daya (Watt)", min_value=0, value=DAFTAR_PERANGKAT[pilihan], step=5)
with kol3:
    jam_input = st.number_input("Jam/hari", min_value=0.0, max_value=24.0, value=4.0, step=0.5)
with kol4:
    jumlah_input = st.number_input("Jumlah", min_value=1, value=1, step=1)
with kol5:
    st.write("")  # spasi agar tombol sejajar
    st.write("")
    tombol_tambah = st.button("➕ Tambah", use_container_width=True)

if tombol_tambah:
    baris_baru = pd.DataFrame([{
        KOLOM_NAMA: pilihan if "Lainnya" not in pilihan else "Perangkat lain",
        KOLOM_DAYA: daya_input,
        KOLOM_JAM: jam_input,
        KOLOM_JUMLAH: jumlah_input,
    }])
    st.session_state.df_perangkat = pd.concat(
        [st.session_state.df_perangkat, baris_baru], ignore_index=True
    )
    st.rerun()


# =============================================================================
# 7. TABEL PERANGKAT (bisa diedit langsung, baris bisa dihapus)
# =============================================================================

st.subheader("2. Daftar Perangkat")
st.caption("Klik sel untuk mengubah nilai. Pilih baris lalu tekan Delete untuk menghapus.")

df_edit = st.data_editor(
    st.session_state.df_perangkat,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        KOLOM_NAMA: st.column_config.TextColumn(KOLOM_NAMA),
        KOLOM_DAYA: st.column_config.NumberColumn(KOLOM_DAYA, min_value=0, step=5),
        KOLOM_JAM: st.column_config.NumberColumn(KOLOM_JAM, min_value=0.0, max_value=24.0, step=0.5),
        KOLOM_JUMLAH: st.column_config.NumberColumn(KOLOM_JUMLAH, min_value=0, step=1),
    },
)
st.session_state.df_perangkat = df_edit  # simpan perubahan pengguna

if st.button("🔄 Reset ke data contoh"):
    st.session_state.df_perangkat = pd.DataFrame(DATA_AWAL)
    st.rerun()


# =============================================================================
# 8. HASIL PERHITUNGAN
# =============================================================================

st.subheader("3. Hasil Perhitungan")

hasil = hitung_hasil(df_edit, tarif)
total_kwh = hasil["Energi (kWh)"].sum()
biaya_harian = hasil["Biaya Harian (Rp)"].sum()
biaya_bulanan = biaya_harian * hari_per_bulan

m1, m2, m3 = st.columns(3)
m1.metric("Total energi per hari", f"{total_kwh:,.2f} kWh")
m2.metric("Biaya per hari", format_rupiah(biaya_harian))
m3.metric(f"Estimasi per bulan ({hari_per_bulan} hari)", format_rupiah(biaya_bulanan))

# Tabel rincian
tampil = hasil.copy()
tampil["Energi (kWh)"] = tampil["Energi (kWh)"].round(3)
tampil["Biaya Harian (Rp)"] = tampil["Biaya Harian (Rp)"].round(0)
st.dataframe(tampil, use_container_width=True, hide_index=True)


# =============================================================================
# 9. VISUALISASI
# =============================================================================

st.subheader("4. Perangkat Paling Boros")
if biaya_harian > 0:
    grafik = hasil.groupby(KOLOM_NAMA)["Biaya Harian (Rp)"].sum().sort_values(ascending=False)
    st.bar_chart(grafik)
else:
    st.info("Grafik akan tampil setelah ada perangkat dengan pemakaian lebih dari 0.")


# =============================================================================
# 10. SARAN HEMAT & UNDUH HASIL
# =============================================================================

st.subheader("5. Saran Hemat Energi")
for item in buat_saran_hemat(hasil):
    st.markdown(f"- {item}")

st.subheader("6. Unduh Hasil")
csv_data = hasil.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Unduh rincian (CSV)",
    data=csv_data,
    file_name="biaya_listrik_harian.csv",
    mime="text/csv",
)

st.divider()
st.caption("Proyek Akhir Komputasi Awan | Dibuat dengan Python & Streamlit")
