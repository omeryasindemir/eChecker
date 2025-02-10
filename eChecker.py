import requests
from datetime import datetime, timedelta
import urllib.parse
import json
import math
import time

def get_tomorrow_date():
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%d/%m/%Y")

def create_search_data(page_number=1):
    tomorrow = get_tomorrow_date()
    
    data = {
        'kategori': '1',
        'tasinirTur': '',
        'tasinmazTur': '',
        'tasitTur': '',
        'ihaleBirimId': '',
        'ihaleBirimIl': '',
        'ihaleBaslangicFiyati': '',
        'ihaleBitisFiyati': '',
        'isFotografli': 'false',
        'isSecondAuction': 'false',
        'tasitMarka': '',
        'tasitModelBaslangic': '',
        'tasitModelBitis': '',
        'tasinmazIl': '',
        'tasinmazIlce': '',
        'ihaleBaslangicZamani': tomorrow,
        'ihaleBitisZamani': tomorrow,
        'isPilotMu': 'false',
        'isPazarlikUsulu': 'false',
        'pageNumber': str(page_number)
    }
    return data

def fetch_page(url, cookies, page_number):
    form_data = create_search_data(page_number)
    response = requests.post(
        url=url,
        data=form_data,
        cookies=cookies,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    )
    return response.json()

def main():
    jsessionid = input("Lütfen JSESSIONID değerini giriniz: ")
    
    cookies = {
        'JSESSIONID': jsessionid
    }
    
    url = 'https://esatis.uyap.gov.tr/main/esatis/ihaleDetayliArama_brd.ajx'
    
    try:
        # İlk sayfayı çek ve toplam sayfa sayısını hesapla
        first_page = fetch_page(url, cookies, 1)
        items_per_page = first_page[1]  # Sayfa başına öğe sayısı
        total_items = first_page[2]     # Toplam öğe sayısı
        total_pages = math.ceil(total_items / items_per_page)
        
        print(f"Toplam {total_items} öğe bulundu.")
        print(f"Toplam {total_pages} sayfa taranacak.")
        
        # Tüm sonuçları saklamak için liste
        all_results = []
        
        # Tüm sayfaları tara
        for page in range(1, total_pages + 1):
            print(f"Sayfa {page}/{total_pages} taranıyor...")
            page_data = fetch_page(url, cookies, page)
            if len(page_data) > 0 and isinstance(page_data[0], list):
                all_results.extend(page_data[0])
            time.sleep(1)  # Sunucuyu yormamak için her istek arasında 1 saniye bekle
        
        # Sonuçları JSON dosyasına kaydet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ihale_sonuc_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print(f"Sonuçlar {filename} dosyasına kaydedildi.")
        print(f"Toplam {len(all_results)} sonuç bulundu.")
            
    except Exception as e:
        print(f"Bir hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()
