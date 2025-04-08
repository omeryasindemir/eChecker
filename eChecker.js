const axios = require('axios');
const fs = require('fs').promises;

function getTomorrowDate() {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toLocaleDateString('tr-TR').replace(/\./g, '/');
}

function createSearchData(pageNumber = 1) {
    const tomorrow = getTomorrowDate();
    
    return {
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
        'pageNumber': pageNumber.toString()
    };
}

async function fetchPageWithRetry(url, cookies, pageNumber, maxRetries = 3) {
    const formData = new URLSearchParams(createSearchData(pageNumber));
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const response = await axios.post(url, formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Cookie': `JSESSIONID=${cookies.JSESSIONID}`,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                timeout: 30000, // 30 saniye timeout
                validateStatus: function (status) {
                    return status >= 200 && status < 300; // Sadece 2xx yanıtları başarılı kabul et
                }
            });
            
            return response.data;
        } catch (error) {
            console.error(`Sayfa ${pageNumber} için deneme ${attempt}/${maxRetries} başarısız:`, error.message);
            
            if (attempt === maxRetries) {
                throw new Error(`Sayfa ${pageNumber} için maksimum deneme sayısına ulaşıldı: ${error.message}`);
            }
            
            // Hata türüne göre bekleme süresini ayarla
            const waitTime = attempt * 2000; // Her denemede bekleme süresini artır
            console.log(`${waitTime/1000} saniye sonra tekrar denenecek...`);
            await sleep(waitTime);
        }
    }
}

// Bekleme fonksiyonu
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
    const readline = require('readline').createInterface({
        input: process.stdin,
        output: process.stdout
    });

    const question = (query) => new Promise((resolve) => {
        readline.question(query, resolve);
    });

    try {
        const jsessionid = await question('Lütfen JSESSIONID değerini giriniz: ');
        readline.close();

        const cookies = {
            JSESSIONID: jsessionid
        };

        const url = 'https://esatis.uyap.gov.tr/main/esatis/ihaleDetayliArama_brd.ajx';

        // İlk sayfayı çek
        console.log('İlk sayfa alınıyor...');
        const firstPage = await fetchPageWithRetry(url, cookies, 1);
        
        if (!Array.isArray(firstPage) || firstPage.length < 3) {
            throw new Error('Geçersiz yanıt formatı veya oturum süresi dolmuş olabilir.');
        }

        const itemsPerPage = firstPage[1];
        const totalItems = firstPage[2];
        const totalPages = Math.ceil(totalItems / itemsPerPage);

        console.log(`Toplam ${totalItems} öğe bulundu.`);
        console.log(`Toplam ${totalPages} sayfa taranacak.`);

        let allResults = [];
        let failedPages = [];

        // Tüm sayfaları tara
        for (let page = 1; page <= totalPages; page++) {
            try {
                console.log(`Sayfa ${page}/${totalPages} taranıyor...`);
                const pageData = await fetchPageWithRetry(url, cookies, page);
                
                if (pageData.length > 0 && Array.isArray(pageData[0])) {
                    allResults = allResults.concat(pageData[0]);
                } else {
                    console.warn(`Sayfa ${page} için geçersiz veri formatı`);
                }
                
                await sleep(1500); // Bekleme süresini 1.5 saniyeye çıkardık
            } catch (error) {
                console.error(`Sayfa ${page} alınamadı:`, error.message);
                failedPages.push(page);
            }
        }

        // Başarısız sayfaları raporla
        if (failedPages.length > 0) {
            console.warn(`\nAlınamayan sayfalar: ${failedPages.join(', ')}`);
        }

        // Sonuçları kaydet
        if (allResults.length > 0) {
            const timestamp = new Date().toISOString()
                .replace(/[:.]/g, '')
                .replace('T', '_')
                .split('Z')[0];
            const filename = `veriler.json`;

            await fs.writeFile(
                filename, 
                JSON.stringify(allResults, null, 2),
                'utf8'
            );

            console.log(`\nSonuçlar ${filename} dosyasına kaydedildi.`);
            console.log(`Toplam ${allResults.length} sonuç bulundu.`);
        } else {
            throw new Error('Hiç sonuç alınamadı!');
        }

    } catch (error) {
        console.error('\nKritik hata:', error.message);
        process.exit(1);
    }
}

main(); 