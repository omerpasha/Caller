from fastapi import FastAPI, WebSocket, Response, HTTPException, Request, Depends
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from starlette.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv
import os
import json
import asyncio
import base64
from openai import AsyncOpenAI
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv('config.env')

# Initialize FastAPI app
app = FastAPI()

# Add middleware for proxy headers
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize clients
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)
openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# JWT settings
JWT_SECRET = os.getenv('JWT_SECRET', os.urandom(32).hex())
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 5

# Twilio signature verification settings
DISABLE_TWILIO_SIG = os.getenv("DISABLE_TWILIO_SIG") == "1"
twilio_validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))

def create_stream_token():
    """Create a short-lived JWT token for WebSocket authentication"""
    expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    return jwt.encode(
        {"exp": expiration},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

def verify_stream_token(token: str):
    """Verify WebSocket JWT token"""
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True
    except:
        return False

def verify_twilio_signature(request: Request, body: str = ""):
    """Verify Twilio request signature"""
    if DISABLE_TWILIO_SIG:
        return True
        
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    
    return twilio_validator.validate(url, body, signature)

class CallRequest(BaseModel):
    to_number: str

@app.post("/call")
@limiter.limit("10/minute")
async def start_call(call_request: CallRequest, request: Request):
    """Dış aramayı başlat"""
    try:
        # Generate stream token
        stream_token = create_stream_token()
        
        # Twilio üzerinden arama başlat
        answer_url = os.getenv('TWILIO_ANSWER_URL') or f"https://{os.getenv('PUBLIC_HOST')}/answer"
        call = twilio_client.calls.create(
            to=call_request.to_number,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            url=answer_url
        )
        return {"status": "success", "call_sid": call.sid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/answer")
async def answer(request: Request):
    """TwiML yanıtını oluştur"""
    # Verify Twilio signature
    if not verify_twilio_signature(request):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    
    # Generate stream token
    stream_token = create_stream_token()
    
    twiml = f"""
    <Response>
        <Say language="tr-TR">Merhaba, birazdan yapay zeka asistanımız bağlanacak.</Say>
        <Connect>
            <Stream url="wss://{os.getenv('PUBLIC_HOST')}/stream?token={stream_token}" />
        </Connect>
    </Response>
    """
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/stream")
async def stream_endpoint(websocket: WebSocket):
    """WebSocket köprüsü"""
    # Verify token (can be bypassed for debugging)
    token = websocket.query_params.get("token")
    if os.getenv("ALLOW_UNAUTH_STREAM") == "1":
        pass
    elif not token or not verify_stream_token(token):
        await websocket.close(code=4003)
        return
        
    await websocket.accept()
    print("WebSocket connected")
    
    try:
        # OpenAI ses stream'i başlat
        openai_stream = await openai_client.audio.speech.create_streaming(
            model="tts-1",
            voice="alloy",
            input="Merhaba, ben yapay zeka asistanınız. Size nasıl yardımcı olabilirim?"
        )
        print("OpenAI stream started")
        
        while True:
            # Twilio'dan gelen ses paketlerini al
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            print(f"Received event: {payload['event']}")
            
            if payload["event"] == "media":
                # Base64 encoded ses verisini decode et
                audio_data = base64.b64decode(payload["media"]["payload"])
                
                # OpenAI'ya ses verisini gönder ve yanıt al
                response = await openai_client.audio.speech.create(
                    model="whisper-1",
                    file=("audio.raw", audio_data)
                )
                
                print(f"Transcribed text: {response.text}")
                
                # OpenAI'dan gelen metni tekrar sese çevir
                audio_response = await openai_client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=response.text
                )
                
                # Sesi Twilio'ya geri gönder
                await websocket.send_bytes(audio_response.content)
                print("Sent audio response")

    except Exception as e:
        print(f"Error in WebSocket connection: {str(e)}")
    finally:
        print("WebSocket disconnected")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
# Webhook endpoint'leri
@app.post("/webhook/call")
async def webhook_call(data: dict):
    """Dinamik arama webhook'u"""
    try:
        to_number = data.get("to_number")
        agent_type = data.get("agent_type", "default")
        custom_prompt = data.get("custom_prompt", "")
        
        if not to_number:
            return {"error": "to_number is required"}
        
        # Arama başlat
        call_result = await start_dynamic_call(to_number, agent_type, custom_prompt)
        return {"status": "success", "call_id": call_result}
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook/status")
async def webhook_status(data: dict):
    """Arama durumu webhook'u"""
    try:
        call_sid = data.get("call_sid")
        status = data.get("status")
        
        print(f"Call {call_sid} status: {status}")
        return {"status": "received"}
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/github/webhook")
async def github_webhook(data: dict):
    """GitHub webhook - otomatik deploy"""
    try:
        # GitHub'dan gelen değişiklikleri işle
        print("GitHub webhook received")
        
        # Otomatik deploy (opsiyonel)
        # subprocess.run(["git", "pull"])
        # subprocess.run(["pip", "install", "-r", "requirements.txt"])
        
        return {"status": "success", "message": "GitHub webhook received"}
        
    except Exception as e:
        return {"error": str(e)}

# Dinamik arama fonksiyonu
async def start_dynamic_call(to_number: str, agent_type: str = "default", custom_prompt: str = ""):
    """Dinamik arama başlat"""
    try:
        # Twilio ile arama yap
        call = twilio_client.calls.create(
            to=to_number,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            url=f"https://{os.getenv('PUBLIC_HOST')}/answer"
        )
        
        return call.sid
        
    except Exception as e:
        print(f"Call error: {e}")
        raise e
