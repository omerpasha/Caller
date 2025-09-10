#!/usr/bin/env python3
"""
Retell.ai Final Entegrasyonu - Doğal Akış
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")

class RetellAIIntegration:
    def __init__(self):
        self.api_key = os.getenv('RETELL_API_KEY')
        self.agent_id = os.getenv('RETELL_AGENT_ID')
        self.llm_id = os.getenv('RETELL_LLM_ID')
        self.base_url = "https://api.retellai.com/v2"
        
    async def create_phone_call(self, from_number, to_number, dynamic_variables=None):
        """Retell.ai ile telefon araması oluştur"""
        try:
            url = f"{self.base_url}/create-phone-call"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "from_number": from_number,
                "to_number": to_number,
                "agent_id": self.agent_id,
                "retell_llm_dynamic_variables": dynamic_variables or {}
            }
            
            print(f"📞 Retell.ai araması başlatılıyor...")
            print(f"📊 From: {from_number}")
            print(f"📊 To: {to_number}")
            print(f"📊 Agent ID: {self.agent_id}")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"📊 Status Code: {response.status_code}")
                print(f"📄 Response: {response.text}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"❌ Retell.ai hatası: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Retell.ai entegrasyon hatası: {e}")
            return None
    
    async def get_call_status(self, call_id):
        """Arama durumunu kontrol et"""
        try:
            url = f"{self.base_url}/get-call/{call_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
                    
        except Exception as e:
            print(f"❌ Call status hatası: {e}")
            return None

async def test_retell_flow():
    """Retell.ai doğal akış testi"""
    retell = RetellAIIntegration()
    
    # API key kontrolü
    if not retell.api_key or retell.api_key == 'your_actual_api_key_here':
        print("❌ Retell.ai API key bulunamadı!")
        print("Lütfen config.env dosyasında RETELL_API_KEY'i güncelleyin")
        return False
    
    # Test parametreleri
    from_number = "+18482925928"  # Twilio numaranız
    to_number = "+905349188566"   # Test numarası
    
    print("🎤 Retell.ai Doğal Akış Testi")
    print("=" * 40)
    
    # 1. Arama oluştur
    call_result = await retell.create_phone_call(
        from_number=from_number,
        to_number=to_number,
        dynamic_variables={
            "name": "Test Kullanıcı",
            "company": "Test Şirketi",
            "service": "Su arıtma cihazı bakımı",
            "phone": to_number
        }
    )
    
    if call_result:
        call_id = call_result.get('call_id')
        print(f"✅ Arama başlatıldı!")
        print(f"📊 Call ID: {call_id}")
        print(f"📊 Status: {call_result.get('status', 'N/A')}")
        
        # 2. Arama durumunu kontrol et
        print("\n⏳ Arama durumu kontrol ediliyor...")
        await asyncio.sleep(5)  # 5 saniye bekle
        
        status = await retell.get_call_status(call_id)
        if status:
            print(f"📊 Güncel durum: {status.get('status', 'N/A')}")
            print(f"📊 Süre: {status.get('duration', 'N/A')} saniye")
        
        return True
    else:
        print("❌ Arama oluşturulamadı")
        return False

async def main():
    print("🚀 Retell.ai Doğal Akış Başlatılıyor")
    print("=" * 50)
    
    success = await test_retell_flow()
    
    if success:
        print("\n🎉 Retell.ai doğal akış başarılı!")
        print("📞 Telefon araması Retell.ai üzerinden yapıldı")
        print("🎯 Doğal Türkçe konuşma başladı")
        print("🤖 AI agent: Su arıtma cihazı bakım danışmanı")
    else:
        print("\n❌ Retell.ai akışında sorun var")
        print("🔧 API key'i kontrol edin")

if __name__ == "__main__":
    asyncio.run(main())
