import json
import requests
import os
import re
import zipfile
import pandas as pd

# Kullanıcıdan JSESSIONID çerezini al
jsessionid = input("Lütfen JSESSIONID değerini girin: ").strip()

# JSON dosyanızın adı (İçinde kayitID değerleri olmalı)
json_dosya_adi = "veriler.json"
hedef_klasor = "indirilenler"

# Ana URL formatı
url_template = "https://esatis.uyap.gov.tr/main/jsp/esatis/evrak_indir_brd.uyap?kayitId={}&islemTuru=satis"

# Klasörü oluştur (varsa hata vermez)
os.makedirs(hedef_klasor, exist_ok=True)

# JSON dosyasını yükle
with open(json_dosya_adi, "r", encoding="utf-8") as dosya:
    veriler = json.load(dosya)

# Yüzölçümü değerlerini saklamak için veriler listesini güncelleyeceğiz
for item in veriler:
    kayit_id = item["kayitID"]
    url = url_template.format(kayit_id)
    udf_dosya_adi = f"{hedef_klasor}/dosya_{kayit_id}.udf"

    print(f"İndiriliyor: {url} -> {udf_dosya_adi}")
    response = requests.get(url, cookies={"JSESSIONID": jsessionid})

    if response.status_code == 200:
        with open(udf_dosya_adi, "wb") as dosya:
            dosya.write(response.content)
        print(f"✅ İndirildi: {udf_dosya_adi}")

        # ZIP olup olmadığını kontrol et
        if zipfile.is_zipfile(udf_dosya_adi):
            with zipfile.ZipFile(udf_dosya_adi, "r") as zip_dosya:
                if "content.xml" in zip_dosya.namelist():
                    with zip_dosya.open("content.xml") as content_dosyasi:
                        content_xml = content_dosyasi.read().decode("utf-8", errors="ignore")

                    # Yüzölçümü değerini regex ile bul
                    match = re.search(r"Yüzölçümü\s*:?\s*([\d.,]+)\s*m2?", content_xml, re.IGNORECASE)
                    yuzolcumu = match.group(1) if match else "Bilinmiyor"
                    print(f"📏 Yüzölçümü: {yuzolcumu} m²")
                    
                    # Yüzölçümü değerini JSON verisine ekle
                    item["yuzolcumu"] = yuzolcumu
                else:
                    print("⚠️ content.xml bulunamadı!")
                    item["yuzolcumu"] = "Bulunamadı"
        else:
            print("⚠️ UDF dosyası ZIP formatında değil!")
            item["yuzolcumu"] = "ZIP değil"

        # Eski UDF dosyasını sil
        os.remove(udf_dosya_adi)
        print(f"🗑️ {udf_dosya_adi} silindi.")
    else:
        print(f"❌ Hata: {kayit_id} için dosya indirilemedi! HTTP Kodu: {response.status_code}")
        item["yuzolcumu"] = "İndirilemedi"

# DataFrame'e çevirmeden önce sayısal değerleri düzenle
for item in veriler:
    # Yüzölçümü sayısal değere çevir
    if 'yuzolcumu' in item:
        try:
            item['yuzolcumu'] = float(item['yuzolcumu'].replace(',', '.').replace(' m²', ''))
        except:
            item['yuzolcumu'] = None
    
    # m2 fiyatını hesapla
    if 'yuzolcumu' in item and item['yuzolcumu'] and isinstance(item['yuzolcumu'], (int, float)):
        item['m2_fiyati'] = item['topluKiymetBilgisi'] / item['yuzolcumu']
    else:
        item['m2_fiyati'] = None

# Verileri DataFrame'e çevir
df = pd.DataFrame(veriler)

# İstenmeyen sütunları çıkar
istenmeyen_sutunlar = [
    'resimAdi', 'fesihDavasiVar', 'ihaleSirasi', 'ihale115eGoreUzadi',
    'dosyaID', 'ihaleBaslangicZamani', 'teklifSuresiBitmisMi', 'kayitID'
]
df = df.drop(columns=istenmeyen_sutunlar, errors='ignore')

# malAciklama'dan bilgileri ayıkla
def adres_bilgilerini_ayikla(aciklama):
    bilgiler = {
        'il': '',
        'ilce': '',
        'mahalle': '',
        'ada': '',
        'parsel': ''
    }
    
    if isinstance(aciklama, str):
        # İlk virgüle kadar olan kısımdan il ve ilçeyi al
        ilk_kisim = aciklama.split(',')[:2]  # İlk iki parça
        
        if len(ilk_kisim) >= 1:
            # İlk parça il
            il_match = re.search(r'(.+?)\s+İl', ilk_kisim[0])
            if il_match:
                bilgiler['il'] = il_match.group(1).strip().upper()
        
        if len(ilk_kisim) >= 2:
            # İkinci parça ilçe
            ilce_match = re.search(r'(.+?)\s+İlçe', ilk_kisim[1])
            if ilce_match:
                bilgiler['ilce'] = ilce_match.group(1).strip().upper()
        
        # Mahalle, Ada ve Parsel bilgilerini bul
        for parca in aciklama.split(','):
            parca = parca.strip()
            if "Mahalle/Köy" in parca:
                mahalle_match = re.search(r'(.+?)\s+Mahalle/Köy', parca)
                if mahalle_match:
                    bilgiler['mahalle'] = mahalle_match.group(1).strip().upper()
            elif "Ada" in parca:
                ada_match = re.search(r'(\d+)\s*Ada', parca)
                if ada_match:
                    bilgiler['ada'] = ada_match.group(1)
            elif "Parsel" in parca:
                parsel_match = re.search(r'(\d+)\s*Parsel', parca)
                if parsel_match:
                    bilgiler['parsel'] = parsel_match.group(1)
    
    return bilgiler

# Her bir satır için adres bilgilerini ayıkla
adres_bilgileri = df['malAciklama'].apply(adres_bilgilerini_ayikla)
adres_df = pd.DataFrame(adres_bilgileri.tolist())

# Yeni sütunları ana DataFrame'e ekle
df = pd.concat([df, adres_df], axis=1)

# Sütun sıralamasını düzenle
sutun_sirasi = [
    'dosyaNoTurKod', 'il', 'ilce', 'mahalle', 'ada', 'parsel',
    'yuzolcumu', 'topluKiymetBilgisi', 'sonTeklif', 'm2_fiyati',
    'birimAdi', 'birimIlAdi', 'birimIlceAdi', 'teklifSayi',
    'ihaleBitisZamani', 'malAciklama'
]

# Sadece mevcut olan sütunları seç
mevcut_sutunlar = [col for col in sutun_sirasi if col in df.columns]
df = df.reindex(columns=mevcut_sutunlar)

# Sayısal değerleri formatla
df['topluKiymetBilgisi'] = df['topluKiymetBilgisi'].apply(lambda x: '{:,.0f}'.format(x).replace(',', '.'))
df['sonTeklif'] = df['sonTeklif'].apply(lambda x: '{:,.0f}'.format(x).replace(',', '.'))
df['m2_fiyati'] = df['m2_fiyati'].apply(lambda x: '{:,.2f}'.format(x).replace(',', '.') if pd.notnull(x) else '')
df['yuzolcumu'] = df['yuzolcumu'].apply(lambda x: '{:,.2f}'.format(x).replace(',', '.') if pd.notnull(x) else '')

# İcra dairelerini kırmızı yapma
def style_icra(row):
    if 'İcra' in str(row['birimAdi']):
        return ['color: red'] * len(row)
    return [''] * len(row)

# Excel dosyasına kaydet
excel_dosya_adi = "sonuclar.xlsx"
with pd.ExcelWriter(excel_dosya_adi, engine='openpyxl') as writer:
    df.style.apply(style_icra, axis=1).to_excel(writer, index=False)

# TXT dosyasına kaydet
txt_dosya_adi = "sonuclar.txt"
with open(txt_dosya_adi, 'w', encoding='utf-8') as f:
    for index, row in df.iterrows():
        f.write(f"İhale No: {row['dosyaNoTurKod']}\n")
        f.write(f"İl: {row['il']}\n")
        f.write(f"İlçe: {row['ilce']}\n")
        f.write(f"Mahalle: {row['mahalle']}\n")
        f.write(f"Ada: {row['ada']}\n")
        f.write(f"Parsel: {row['parsel']}\n")
        if 'yuzolcumu' in row and row['yuzolcumu'] not in ['Bilinmiyor', 'Bulunamadı', 'ZIP değil', 'İndirilemedi']:
            f.write(f"Yüzölçümü: {row['yuzolcumu']} m²\n")
        f.write(f"Muhammen Bedel: {row['topluKiymetBilgisi']} TL\n")
        f.write(f"Son Teklif: {row['sonTeklif']} TL\n")
        if pd.notnull(row['m2_fiyati']):
            f.write(f"m² Fiyatı: {row['m2_fiyati']} TL\n")
        f.write(f"Teklif Sayısı: {row['teklifSayi']}\n")
        f.write(f"İhale Bitiş Zamanı: {row['ihaleBitisZamani']}\n")
        f.write(f"Birim İl: {row['birimIlAdi']}\n")
        f.write(f"Birim İlçe: {row['birimIlceAdi']}\n")
        f.write(f"Birim: {row['birimAdi']}\n")
        f.write(f"Açıklama: {row['malAciklama']}\n")
        f.write("-" * 80 + "\n\n")

print(f"📝 TXT dosyası oluşturuldu: {txt_dosya_adi}")

print("🎉 Tüm işlemler tamamlandı!")
