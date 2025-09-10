#!/usr/bin/env python3
"""
Retell.ai Working Entegrasyonu - Türkiye Arama
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
                "llm_dynamic_variables": dynamic_variables or {}
            }
            
            print(f"🎤 Retell.ai arama başlatılıyor...")
            print(f"📞 From: {from_number}")
            print(f"📞 To: {to_number}")
            print(f"🤖 Agent ID: {self.agent_id}")
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Retell.ai arama başarılı!")
                    print(f"📋 Call ID: {result.get('call_id', 'N/A')}")
                    print(f"📊 Status: {result.get('status', 'N/A')}")
                    return result
                else:
                    print(f"❌ Retell.ai API hatası: {response.status_code}")
                    print(f"📄 Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Retell.ai entegrasyon hatası: {str(e)}")
            return None

async def main():
    """Ana test fonksiyonu"""
    retell = RetellAIIntegration()
    
    # Test araması
    from_number = os.getenv('RETELL_FROM_NUMBER', '+15105440586')
    to_number = '+905349188566'
    
    print("🚀 Retell.ai entegrasyon testi başlatılıyor...")
    
    result = await retell.create_phone_call(from_number, to_number)
    
    if result:
        print("🎉 Test başarılı!")
    else:
        print("❌ Test başarısız!")

if __name__ == "__main__":
    asyncio.run(main())
