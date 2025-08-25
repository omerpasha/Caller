#!/bin/bash

echo "🚀 Cloudflare Tunnel Başlatılıyor..."

# Eski tunnel'ları durdur
pkill -f cloudflared 2>/dev/null
sleep 2

# Yeni tunnel başlat ve URL'ini yakala
echo "📡 Yeni tunnel oluşturuluyor..."
TUNNEL_OUTPUT=$(cloudflared tunnel --url http://localhost:8000 2>&1)

# URL'ini çıkar
TUNNEL_URL=$(echo "$TUNNEL_OUTPUT" | grep -o 'https://[^[:space:]]*\.trycloudflare\.com' | head -1)

if [ -n "$TUNNEL_URL" ]; then
    # Domain kısmını çıkar
    DOMAIN=$(echo "$TUNNEL_URL" | sed 's|https://||')
    
    echo "✅ Tunnel başlatıldı: $TUNNEL_URL"
    echo "🌐 Domain: $DOMAIN"
    
    # Config.env'yi güncelle
    if [ -f "config.env" ]; then
        # PUBLIC_HOST satırını güncelle
        if grep -q "PUBLIC_HOST=" config.env; then
            sed -i.bak "s|PUBLIC_HOST=.*|PUBLIC_HOST=$DOMAIN|" config.env
            echo "📝 Config.env güncellendi: PUBLIC_HOST=$DOMAIN"
        else
            echo "PUBLIC_HOST=$DOMAIN" >> config.env
            echo "📝 Config.env'e PUBLIC_HOST eklendi"
        fi
        
        # Backup dosyasını sil
        rm -f config.env.bak
        
        echo "🔄 Şimdi uvicorn'u yeniden başlatın:"
        echo "   uvicorn main:app --host 0.0.0.0 --port 8000"
    else
        echo "❌ config.env dosyası bulunamadı!"
    fi
else
    echo "❌ Tunnel URL'i alınamadı!"
    echo "Tunnel çıktısı:"
    echo "$TUNNEL_OUTPUT"
fi

echo ""
echo "💡 Tunnel çalışırken bu terminal'i açık tutun!"
echo "   Ctrl+C ile durdurmak için" 