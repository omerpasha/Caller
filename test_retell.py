#!/usr/bin/env python3
"""
Retell.ai TTS Test Script
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")

async def test_retell_tts():
    """Test Retell.ai TTS functionality"""
    try:
        # Import the function
        from main import retell_tts_synthesize
        
        test_text = "Merhaba, ben Retell.ai ile oluşturulmuş yapay zeka asistanınız. Size nasıl yardımcı olabilirim?"
        
        print("🎤 Retell.ai TTS testi başlatılıyor...")
        print(f"📝 Test metni: {test_text}")
        
        # Test Retell.ai TTS
        audio_data = await retell_tts_synthesize(test_text)
        
        print(f"✅ Retell.ai TTS başarılı!")
        print(f"📊 Ses verisi boyutu: {len(audio_data)} bytes")
        
        # Save test audio
        with open("retell_test_audio.wav", "wb") as f:
            f.write(audio_data)
        print("💾 Test sesi 'retell_test_audio.wav' olarak kaydedildi")
        
        return True
        
    except Exception as e:
        print(f"❌ Retell.ai TTS hatası: {e}")
        return False

async def test_azure_tts():
    """Test Azure TTS functionality"""
    try:
        from main import tts_synthesize
        
        test_text = "Merhaba, ben Azure TTS ile oluşturulmuş yapay zeka asistanınız."
        
        print("\n🎤 Azure TTS testi başlatılıyor...")
        print(f"📝 Test metni: {test_text}")
        
        audio_data = await tts_synthesize(test_text)
        
        print(f"✅ Azure TTS başarılı!")
        print(f"📊 Ses verisi boyutu: {len(audio_data)} bytes")
        
        # Save test audio
        with open("azure_test_audio.wav", "wb") as f:
            f.write(audio_data)
        print("💾 Test sesi 'azure_test_audio.wav' olarak kaydedildi")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure TTS hatası: {e}")
        return False

async def main():
    print("🚀 TTS Karşılaştırma Testi")
    print("=" * 50)
    
    # Test Retell.ai
    retell_success = await test_retell_tts()
    
    # Test Azure
    azure_success = await test_azure_tts()
    
    print("\n📊 Test Sonuçları:")
    print(f"Retell.ai TTS: {'✅ Başarılı' if retell_success else '❌ Başarısız'}")
    print(f"Azure TTS: {'✅ Başarılı' if azure_success else '❌ Başarısız'}")
    
    if retell_success and azure_success:
        print("\n🎉 Her iki TTS de çalışıyor! Ses dosyalarını dinleyerek karşılaştırın.")
    elif retell_success:
        print("\n✅ Retell.ai TTS çalışıyor, Azure TTS'de sorun var.")
    elif azure_success:
        print("\n✅ Azure TTS çalışıyor, Retell.ai TTS'de sorun var.")
    else:
        print("\n❌ Her iki TTS'de de sorun var.")

if __name__ == "__main__":
    asyncio.run(main())
