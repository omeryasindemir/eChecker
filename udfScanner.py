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

# Verileri DataFrame'e çevir ve Excel dosyasına kaydet
df = pd.DataFrame(veriler)
excel_dosya_adi = "sonuclar.xlsx"
df.to_excel(excel_dosya_adi, index=False)
print(f"📊 Excel dosyası oluşturuldu: {excel_dosya_adi}")

print("🎉 Tüm işlemler tamamlandı!")
