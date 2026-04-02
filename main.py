import yaml
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)


def load_llm():
    provider = config["llm"]["provider"]
    model = config["llm"]["model"]
    temperature = config["llm"]["temperature"]
    max_tokens = config["llm"]["max_tokens"]
    if provider == "gemini":
        from providers.llm.gemini_adapter import GeminiAdapter
        return GeminiAdapter(model, temperature, max_tokens)
    raise ValueError(f"Unknown LLM provider: {provider}")


def load_stt():
    provider = config["stt"]["provider"]
    if provider == "whisper":
        from providers.stt.whisper_adapter import WhisperAdapter
        return WhisperAdapter(
            model=config["stt"]["model"],
            language=config["stt"]["language"]
        )
    raise ValueError(f"Unknown STT provider: {provider}")


def load_tts():
    provider = config["tts"]["provider"]
    if provider == "polly":
        from providers.tts.polly_adapter import PollyAdapter
        return PollyAdapter(
            voice_id=config["tts"]["voice_id"],
            engine=config["tts"]["engine"],
            language_code=config["tts"]["language_code"]
        )
    raise ValueError(f"Unknown TTS provider: {provider}")


# Initialize providers
llm = load_llm()
stt = load_stt()
tts = load_tts()

# Initialize orchestrator
from orchestrator.orchestrator import Orchestrator
orchestrator = Orchestrator(llm=llm, stt=stt, tts=tts, config=config)

# Initialize routes
from api.routes import router, init_routes
from api.interview_ws import interview_websocket, init_ws
from api.anticheat_ws import anticheat_websocket, init_anticheat_ws

init_routes(orchestrator)
init_ws(orchestrator)
init_anticheat_ws(orchestrator)

# Create app
app = FastAPI(title="VLSI Interview Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")


@app.websocket("/ws/{session_id}/interview")
async def ws_interview(websocket: WebSocket, session_id: str):
    await interview_websocket(websocket, session_id)


@app.websocket("/ws/{session_id}/anticheat")
async def ws_anticheat(websocket: WebSocket, session_id: str):
    await anticheat_websocket(websocket, session_id)


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm": config["llm"]["provider"],
        "stt": config["stt"]["provider"],
        "tts": config["tts"]["provider"]
    }


print(f"? VLSI Agent starting...")
print(f"   LLM : {config['llm']['provider']} / {config['llm']['model']}")
print(f"   STT : {config['stt']['provider']}")
print(f"   TTS : {config['tts']['provider']}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=config["server"]["reload"]
    )