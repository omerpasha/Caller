#!/usr/bin/env python3
"""
Retell.ai Final Entegrasyonu - Türkiye Arama
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
                "dynamic_variables": dynamic_variables or {}
            }
            
            print(f"🎤 Retell.ai ile arama yapılıyor...")
            print(f"📞 From: {from_number}")
            print(f"📞 To: {to_number}")
            print(f"🤖 Agent ID: {self.agent_id}")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Arama başarıyla başlatıldı!")
                    print(f"📋 Call ID: {result.get('call_id', 'N/A')}")
                    print(f"�� Status: {result.get('status', 'N/A')}")
                    return result
                else:
                    print(f"❌ Hata: {response.status_code}")
                    print(f"📝 Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            return None

async def test_retell_call():
    """Retell.ai test araması"""
    try:
        # API key kontrolü
        api_key = os.getenv('RETELL_API_KEY')
        if not api_key or api_key == 'your_retell_api_key_here':
            print("❌ Retell.ai API key bulunamadı!")
            print("Lütfen config.env dosyasında RETELL_API_KEY'i güncelleyin")
            return False
        
        # Agent ID kontrolü
        agent_id = os.getenv('RETELL_AGENT_ID')
        if not agent_id or agent_id == 'your_agent_id_here':
            print("❌ Retell.ai Agent ID bulunamadı!")
            print("Lütfen config.env dosyasında RETELL_AGENT_ID'i güncelleyin")
            return False
        
        print("🚀 Retell.ai entegrasyonu test ediliyor...")
        
        # Retell.ai entegrasyonu
        retell = RetellAIIntegration()
        
        # Test araması
        from_number = "+15105440586"  # Twilio numarası
        to_number = "+905349188566"   # Test edilecek numara
        
        result = await retell.create_phone_call(
            from_number=from_number,
            to_number=to_number,
            dynamic_variables={
                "customer_name": "Test Müşteri",
                "call_purpose": "Su arıtma cihazı bakım danışmanlığı"
            }
        )
        
        if result:
            print("🎉 Test başarılı!")
            return True
        else:
            print("❌ Test başarısız!")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_retell_call())
