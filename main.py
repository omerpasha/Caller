import os
from dotenv import load_dotenv

# Load environment variables first
print("Loading environment variables...")
load_dotenv("config.env")
print("Environment variables loaded")

import json
import base64
import asyncio
import time
import logging
from datetime import datetime
from fastapi import FastAPI, Request, Response, WebSocket, HTTPException
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt
import httpx
import websockets
from urllib.parse import quote_plus

# Configure comprehensive logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('call_system.log'),
        logging.FileHandler('callslog'),  # New detailed call log
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
PUBLIC_HOST = os.getenv("PUBLIC_HOST")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION", "westeurope")
DISABLE_TWILIO_SIG = os.getenv("DISABLE_TWILIO_SIG") == "1"

print(f"ACCOUNT_SID: {ACCOUNT_SID}")
print(f"AUTH_TOKEN: {AUTH_TOKEN}")
print(f"TWILIO_NUMBER: {TWILIO_NUMBER}")
print(f"PUBLIC_HOST: {PUBLIC_HOST}")

# Initialize Twilio client
twilio = Client(ACCOUNT_SID, AUTH_TOKEN)
validator = RequestValidator(AUTH_TOKEN)

# Log configuration
logger.info(f"Loading with ACCOUNT_SID: {ACCOUNT_SID}")
logger.info(f"Loading with AUTH_TOKEN: {AUTH_TOKEN}")
logger.info(f"Loading with PUBLIC_HOST: {PUBLIC_HOST}")
logger.info(f"Loading with TWILIO_NUMBER: {TWILIO_NUMBER}")
if DISABLE_TWILIO_SIG:
    logger.info("Twilio signature validation disabled")

def make_ws_token(ttl=300):
    """Generate JWT token for WebSocket authentication"""
    payload = {
        "exp": int(time.time()) + ttl,
        "iss": "ai-voice",
        "scopes": ["ws"]
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def verify_twilio_signature(request: Request, body: bytes):
    """Verify Twilio request signature"""
    if DISABLE_TWILIO_SIG:
        return True
    
    try:
        sig = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        
        # Get form data for validation
        form_data = dict(await request.form())
        
        if not validator.validate(url, form_data, sig):
            logger.error("❌ Twilio signature validation failed")
            return False
        
        logger.info("✅ Twilio signature validated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Twilio signature verification error: {e}")
        return False

def is_ending_response(text):
    """Check if the response contains ending phrases that would close the conversation"""
    endings = [
        "görüşürüz", "hoşça kal", "teşekkürler", "teşekkür ederim", 
        "iyi günler", "sağ olun", "kapattım", "tamam", "anladım",
        "görüşmek üzere", "hoşça kalın", "iyi akşamlar", "iyi geceler",
        "bye", "goodbye", "see you", "take care"
    ]
    text_lower = text.lower()
    return any(e in text_lower for e in endings)

def filter_response(text):
    """Filter and improve the response to keep conversation going"""
    if is_ending_response(text):
        logger.warning(f"⚠️ Response contains ending phrase: '{text}'")
        # Replace with continuation response
        return "Anladım. Başka bir konuda yardımcı olabilir miyim?"
    
    # Ensure response is not too short or generic
    if len(text.split()) < 3:
        return "Devam edebilirsiniz. Size nasıl yardımcı olabilirim?"
    
    return text

def log_call_event(event_type, details, call_sid=None):
    """Log call events with timestamps to callslog"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_entry = f"[{timestamp}] {event_type}: {details}"
    if call_sid:
        log_entry += f" (Call SID: {call_sid})"
    
    # Write to callslog file
    with open('callslog', 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')
    
    logger.info(log_entry)

app = FastAPI()

# Add middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/call")
@limiter.limit("5/minute;100/day")
async def start_call(request: Request):
    """Start an outbound call"""
    try:
        data = await request.json()
        to_number = data.get("to")
        
        if not to_number:
            raise HTTPException(400, "to number is required")
        
        log_call_event("CALL_START", f"Attempting to call {to_number} using {TWILIO_NUMBER}")
        
        call = twilio.calls.create(
            to=to_number,
            from_=TWILIO_NUMBER,
            url=f"https://{PUBLIC_HOST}/answer"
        )
        
        call_sid = call.sid
        log_call_event("CALL_CREATED", f"Call initiated with SID: {call_sid}", call_sid)
        
        return {"sid": call_sid, "status": "initiated"}
        
    except Exception as e:
        log_call_event("CALL_ERROR", f"Error in start_call: {str(e)}")
        logger.error(f"Error in start_call: {e}")
        raise HTTPException(500, str(e))

@app.post("/answer")
async def answer(request: Request):
    """Handle incoming call and create TwiML response"""
    try:
        body = await request.body()
        
        # Verify Twilio signature
        if not await verify_twilio_signature(request, body):
            raise HTTPException(403, "Invalid Twilio signature")
        
        # Generate WebSocket token
        stream_token = make_ws_token()
        
        log_call_event("ANSWER_ENDPOINT", f"Generated stream token: {stream_token}")
        
        # Create TwiML response
        response = VoiceResponse()
        
        # Short bridge announcement
        response.say(
            "Merhaba, yapay zeka asistanımız bağlanıyor.",
            voice="Polly.Filiz",
            language="tr-TR"
        )
        
        # Brief pause
        response.pause(length=1)
        
        # Connect to WebSocket stream with token in URL
        connect = response.connect()
        stream = connect.stream(
            url=f"wss://{PUBLIC_HOST}/stream?token={stream_token}",
            track="inbound_track",
            name="ai_stream"
        )
        
        log_call_event("TWIML_GENERATED", f"TwiML response created with WebSocket URL: wss://{PUBLIC_HOST}/stream?token={stream_token}")
        
        return Response(str(response), media_type="application/xml")
        
    except Exception as e:
        log_call_event("ANSWER_ERROR", f"Error in answer: {str(e)}")
        logger.error(f"Error in answer: {e}")
        logger.error(f"Traceback: {e.__traceback__}")
        raise HTTPException(500, str(e))

async def stt_connect():
    """Connect to AssemblyAI realtime WebSocket"""
    try:
        uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=8000&language=tr"
        ws = await websockets.connect(uri, extra_headers={"Authorization": ASSEMBLYAI_API_KEY})
        
        # Wait for initial message
        try:
            _hello = await asyncio.wait_for(ws.recv(), timeout=2)
            log_call_event("STT_CONNECTED", f"STT hello message: {_hello}")
        except asyncio.TimeoutError:
            pass
        
        # Send configuration
        try:
            await ws.send(json.dumps({"config": {"punctuate": True}}))
            log_call_event("STT_CONFIG", "STT configuration sent")
        except Exception as e:
            logger.warning(f"STT config failed: {e}")
        
        return ws
        
    except Exception as e:
        log_call_event("STT_ERROR", f"STT connection failed: {str(e)}")
        logger.error(f"STT connection failed: {e}")
        raise

async def stt_send_audio(ws_stt, audio_bytes):
    """Send audio to STT service"""
    try:
        audio_b64 = base64.b64encode(audio_bytes).decode()
        await ws_stt.send(json.dumps({"audio_data": audio_b64}))
        log_call_event("STT_AUDIO_SENT", f"Audio sent to STT: {len(audio_bytes)} bytes")
    except Exception as e:
        log_call_event("STT_SEND_ERROR", f"Failed to send audio to STT: {str(e)}")
        logger.error(f"Failed to send audio to STT: {e}")

async def stt_recv(ws_stt):
    """Receive messages from STT service"""
    try:
        msg = await ws_stt.recv()
        data = json.loads(msg)
        log_call_event("STT_MESSAGE", f"STT message: {data.get('message_type', 'unknown')}")
        return data
    except Exception as e:
        log_call_event("STT_RECV_ERROR", f"STT receive error: {str(e)}")
        logger.error(f"STT receive error: {e}")
        return None

async def llm_respond(text):
    """Get response from OpenAI LLM"""
    try:
        system_prompt = """Rolün: Su arıtma cihazı bakım danışmanı. 
        Türkçe, nazik, 2-3 cümlelik yanıtlar ver. 
        KVKK'ya uygun davran. 
        "Hayır, istemiyorum" diyenlere ısrar etme. 
        Hedefler: (1) Uygun zaman teyidi, (2) Filtre-bakım ihtiyacı, (3) Randevu, (4) WhatsApp bilgi.
        Kaçın: Uzun konuşma, teknik detaya boğma, fiyatı net sormadan söyleme.
        Duygular: Sakin, çözüm odaklı, saygılı."""
        
        user_prompt = f"Kullanıcının son sözü: {text}"
        
        log_call_event("LLM_REQUEST", f"LLM request for text: '{text[:50]}...'")
        
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.4
                }
            )
            r.raise_for_status()
            data = r.json()
            response = data["choices"][0]["message"]["content"].strip()
            
            # Filter response
            filtered_response = filter_response(response)
            
            log_call_event("LLM_RESPONSE", f"LLM response: '{filtered_response[:50]}...'")
            
            return filtered_response
            
    except Exception as e:
        log_call_event("LLM_ERROR", f"LLM error: {str(e)}")
        logger.error(f"LLM error: {e}")
        return "Anladım. Devam edebilirsiniz."

async def tts_synthesize(text) -> bytes:
    """Synthesize speech using Azure TTS"""
    try:
        log_call_event("TTS_START", f"TTS starting for text: '{text[:50]}...'")
        
        # Enhanced SSML for natural Turkish speech
        ssml = f"""<speak version='1.0' xml:lang='tr-TR'>
            <voice name='tr-TR-EmelNeural'>
                <prosody rate="-5%">{text}</prosody>
            </voice>
        </speak>"""
        
        url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "raw-8khz-8bit-mono-pcm"
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, content=ssml)
            r.raise_for_status()
            
            audio_bytes = r.content
            log_call_event("TTS_SUCCESS", f"TTS successful, received {len(audio_bytes)} bytes of audio")
            
            return audio_bytes
            
    except Exception as e:
        log_call_event("TTS_ERROR", f"TTS synthesis failed: {str(e)}")
        logger.error(f"TTS synthesis failed: {e}")
        raise

def pcm8_to_mulaw8k(pcm8_bytes) -> bytes:
    """Convert PCM8 to μ-law 8kHz for Twilio compatibility"""
    try:
        # Simple conversion: PCM8 to μ-law
        # This is a basic implementation - for production use a proper audio library
        mulaw_bytes = bytearray()
        for byte in pcm8_bytes:
            # Convert 8-bit unsigned to μ-law (simplified)
            if byte < 128:
                mulaw_bytes.append(0x7F)  # Silence for low values
            else:
                mulaw_bytes.append(0x7F + (byte - 128) // 2)
        return bytes(mulaw_bytes)
    except Exception as e:
        log_call_event("AUDIO_CONVERSION_ERROR", f"PCM8 to μ-law conversion failed: {str(e)}")
        # Return silence if conversion fails
        return b"\x7F" * len(pcm8_bytes)

async def twilio_send_audio(ws_twilio, mulaw_bytes, stream_sid):
    """Send audio back to Twilio"""
    try:
        payload = base64.b64encode(mulaw_bytes).decode()
        await ws_twilio.send_text(json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload}
        }))
        log_call_event("TWILIO_AUDIO_SENT", f"Audio sent to Twilio: {len(mulaw_bytes)} bytes")
    except Exception as e:
        log_call_event("TWILIO_SEND_ERROR", f"Failed to send audio to Twilio: {str(e)}")
        logger.error(f"Failed to send audio to Twilio: {e}")

@app.websocket("/stream")
async def stream_socket(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams"""
    call_start_time = time.time()
    log_call_event("WEBSOCKET_CONNECT", "WebSocket connection request received")
    
    await websocket.accept()
    log_call_event("WEBSOCKET_ACCEPTED", "WebSocket connection accepted")
    
    # Extract and verify token from query parameters
    token = websocket.query_params.get("token")
    log_call_event("WEBSOCKET_TOKEN_DEBUG", f"Token from query params: {token}")
    
    if not token:
        log_call_event("WEBSOCKET_ERROR", "No token provided in WebSocket connection")
        await websocket.close(code=4003, reason="No token provided")
        return
    
    try:
        # Ensure token is string for JWT decode
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            log_call_event("WEBSOCKET_TOKEN_CONVERT", "Token converted from bytes to string")
        
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        log_call_event("WEBSOCKET_TOKEN_VERIFIED", f"Token verified for user: {decoded.get('iss', 'unknown')}")
    except Exception as e:
        log_call_event("WEBSOCKET_TOKEN_ERROR", f"Token verification failed: {str(e)}")
        await websocket.close(code=4003, reason="Invalid token")
        return
    
    # Initialize variables
    ws_stt = None
    stream_sid = None
    last_audio_time = time.time()
    media_timeout = 30  # 30 seconds timeout for media events
    
    try:
        # Connect to STT service
        ws_stt = await stt_connect()
        log_call_event("STT_READY", "STT service connected and ready")
        
        # Main message loop
        while True:
            try:
                # Check for media timeout
                if time.time() - last_audio_time > media_timeout:
                    log_call_event("MEDIA_TIMEOUT", f"No media events for {media_timeout} seconds, closing connection")
                    break
                
                # Receive message from Twilio
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                data = json.loads(msg)
                event_type = data.get("event")
                
                log_call_event("TWILIO_EVENT", f"Received event: {event_type}")
                
                if event_type == "connected":
                    log_call_event("STREAM_CONNECTED", "Stream connected successfully")
                    continue
                
                elif event_type == "start":
                    stream_sid = data["start"]["streamSid"]
                    log_call_event("STREAM_STARTED", f"Stream started with SID: {stream_sid}")
                    
                    # Send initial greeting via TTS
                    try:
                        initial_greeting = "Merhaba, ben su arıtma cihazınızın bakım asistanıyım. Size nasıl yardımcı olabilirim?"
                        pcm_greeting = await tts_synthesize(initial_greeting)
                        
                        if stream_sid:
                            mulaw_greeting = pcm8_to_mulaw8k(pcm_greeting)
                            await twilio_send_audio(websocket, mulaw_greeting, stream_sid)
                            log_call_event("INITIAL_GREETING_SENT", "Initial TTS greeting sent successfully")
                        else:
                            log_call_event("GREETING_ERROR", "Cannot send greeting: stream_sid is None")
                    except Exception as e:
                        log_call_event("GREETING_ERROR", f"Failed to send initial greeting: {str(e)}")
                    
                    continue
                
                elif event_type == "media":
                    # Update audio timeout
                    last_audio_time = time.time()
                    
                    audio_b64 = data["media"]["payload"]
                    audio = base64.b64decode(audio_b64)
                    
                    log_call_event("MEDIA_RECEIVED", f"Media event received - Audio length: {len(audio)} bytes")
                    
                    # Send μ-law audio directly to STT (AssemblyAI supports μ-law)
                    await stt_send_audio(ws_stt, audio)
                    
                    # Check for STT responses
                    try:
                        while True:
                            stt_msg = await asyncio.wait_for(stt_recv(ws_stt), timeout=0.1)
                            if stt_msg and stt_msg.get("message_type") in ("FinalTranscript", "final"):
                                user_text = stt_msg.get("text", "").strip()
                                if user_text:
                                    log_call_event("STT_FINAL", f"STT final transcript: '{user_text}'")
                                    
                                    # Get LLM response
                                    bot_response = await llm_respond(user_text)
                                    
                                    # Synthesize speech
                                    pcm_bot = await tts_synthesize(bot_response)
                                    
                                    # Convert to μ-law and send back
                                    if stream_sid:
                                        mulaw = pcm8_to_mulaw8k(pcm_bot)
                                        await twilio_send_audio(websocket, mulaw, stream_sid)
                                        log_call_event("BOT_RESPONSE_SENT", f"Bot response sent: '{bot_response[:50]}...'")
                                    else:
                                        log_call_event("STREAM_SID_MISSING", "Cannot send audio: stream_sid is None")
                                break
                    except asyncio.TimeoutError:
                        pass  # No STT response within timeout
                
                elif event_type == "stop":
                    log_call_event("STREAM_STOPPED", "Stream stopped by Twilio")
                    break
                
                else:
                    log_call_event("UNKNOWN_EVENT", f"Unknown event type: {event_type}")
                    
            except asyncio.TimeoutError:
                continue  # No message received, continue loop
            except Exception as e:
                log_call_event("MESSAGE_ERROR", f"Error processing message: {str(e)}")
                logger.error(f"Error processing message: {e}")
                continue
    
    except Exception as e:
        log_call_event("WEBSOCKET_ERROR", f"WebSocket error: {str(e)}")
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # Cleanup
        if ws_stt:
            try:
                await ws_stt.close()
                log_call_event("STT_CLOSED", "STT connection closed")
            except:
                pass
        
        call_duration = time.time() - call_start_time
        log_call_event("WEBSOCKET_CLOSED", f"WebSocket connection closed after {call_duration:.2f} seconds")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 