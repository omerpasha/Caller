# AI-Powered Phone Call System

Bu uygulama Twilio ve OpenAI kullanarak yapay zeka destekli telefon görüşmeleri yapmanızı sağlar.

## Kurulum

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

2. `config.env` dosyasını düzenleyin ve aşağıdaki bilgileri ekleyin:
   - TWILIO_ACCOUNT_SID (Twilio Console'dan)
   - TWILIO_AUTH_TOKEN (Twilio Console'dan)
   - TWILIO_PHONE_NUMBER (Twilio'dan aldığınız numara)
   - OPENAI_API_KEY (OpenAI API anahtarınız)
   - BASE_URL (Uygulamanızın domain adresi)

## Kullanım

1. Uygulamayı başlatın:
```bash
python app.py
```

2. Arama başlatmak için HTTP POST isteği gönderin:
```bash
curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{"to_number": "+901234567890"}'
```

## Endpoint'ler

- POST `/call`: Yeni bir arama başlatır
- POST `/answer`: Twilio TwiML yanıtını oluşturur
- WebSocket `/stream`: Ses akışı için WebSocket bağlantısı

## Önemli Notlar

- Uygulamanın çalışması için public bir domain'e ihtiyacınız var
- SSL sertifikası gerekli (WebSocket bağlantısı için)
- Twilio hesabınızda yeterli kredi olmalı
- OpenAI API kullanımı için kredi gerekli
- Türkçe ses desteği için "tr-TR" dil kodu kullanılıyor

## Güvenlik

- API anahtarlarını güvenli bir şekilde saklayın
- Rate limiting uygulayın
- WebSocket bağlantılarını kontrol edin
- İstemci doğrulaması ekleyin

## Hata Ayıklama

Hata durumunda logları kontrol edin. WebSocket bağlantısı ve ses akışı ile ilgili hatalar console'da görüntülenir. 