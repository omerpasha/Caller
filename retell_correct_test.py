#!/usr/bin/env python3
"""
Retell.ai Doğru API Test
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")

async def test_retell_api():
    """Retell.ai API testi"""
    try:
        retell_api_key = os.getenv('RETELL_API_KEY')
        if not retell_api_key or retell_api_key == 'your_retell_api_key_here':
            print("❌ Retell.ai API key bulunamadı!")
            print("Lütfen config.env dosyasında RETELL_API_KEY'i güncelleyin")
            return False
        
        print("🎤 Retell.ai API testi...")
        
        # Retell.ai API ile telefon araması yap
        url = "https://api.retellai.com/v2/create-phone-call"
        headers = {
            "Authorization": f"Bearer {retell_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from_number": "+18482925928",  # Twilio numaranız
            "to_number": "+905349188566",   # Test numarası
            "retell_llm_dynamic_variables": {
                "name": "Test Kullanıcı",
                "company": "Test Şirketi"
            }
        }
        
        print(f"📞 Arama yapılıyor: {payload['from_number']} -> {payload['to_number']}")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retell.ai araması başarılı!")
                print(f"📊 Call ID: {data.get('call_id', 'N/A')}")
                print(f"📊 Status: {data.get('status', 'N/A')}")
                return True
            else:
                print(f"❌ Retell.ai hatası: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Retell.ai test hatası: {e}")
        return False

async def main():
    print("🚀 Retell.ai Doğru API Test")
    print("=" * 40)
    
    success = await test_retell_api()
    
    if success:
        print("\n🎉 Retell.ai entegrasyonu çalışıyor!")
        print("📞 Telefon araması başlatıldı")
    else:
        print("\n❌ Retell.ai entegrasyonunda sorun var")
        print("🔧 API key'i kontrol edin")

if __name__ == "__main__":
    asyncio.run(main())
