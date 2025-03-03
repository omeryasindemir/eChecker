import zipfile

# UDF dosyasını aç
with zipfile.ZipFile("dosya (14).udf", "r") as zip_dosya:
    if "content.xml" in zip_dosya.namelist():
        with zip_dosya.open("content.xml") as content_dosyasi:
            content_xml = content_dosyasi.read().decode("utf-8", errors="ignore")
            
            print("\n=== DOSYA (14) ANALIZI ===")
            
            # Tüm satırları kontrol et
            for line in content_xml.split('\n'):
                if 'Yüzölçümü' in line:
                    print("\nBulunan satır:")
                    print(line.strip())
                    print("\nHex formatında:")
                    print(line.strip().encode('utf-8').hex())
                    print("\nKarakter kodları:")
                    print([ord(c) for c in line.strip()]) 