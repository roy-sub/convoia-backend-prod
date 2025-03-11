import sys
import signal
import uvicorn
import asyncio
from pydantic import BaseModel, EmailStr
from fastapi import FastAPI, HTTPException
from ai_assistant import FeatureMatcher
from generator import UserInitializationManager
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from scheduler_manager_daywise import DaywiseSchedulerManager
from scheduler_manager_hourwise import HourwiseSchedulerManager
from aws.utils import get_all_email_ids

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from deepgram import (
    DeepgramClient,
    PrerecordedOptions
)

import aiohttp
import os

from constants import FUNCTION_MAP

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Initialize Deepgram client
deepgram = DeepgramClient(DEEPGRAM_API_KEY)

# Import all the services
from handlers import (
    send_email,
    send_reply_follow_up,
    summarize_emails,
    email_conversational_agent,
    enable_follow_up_reminders,
    disable_follow_up_reminders,
    add_email_label,
    create_email_label,
    enable_important_email_highlighting,
    disable_important_email_highlighting,
    add_important_contacts,
    remove_important_contacts,
    enable_automated_responses,
    disable_automated_responses,
    add_automated_response_categories,
    remove_automated_response_categories
)

# Minute Scheduler
MINUTE_SCHEDULER = 3

# Initialize FastAPI

app = FastAPI()
init_manager = UserInitializationManager()

# Initialize Schedulers
hourwise_scheduler = HourwiseSchedulerManager()
daywise_scheduler = DaywiseSchedulerManager()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add your React app's URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Input Models
class UserInit(BaseModel):
    email_id: EmailStr
    mode: str = "oauth"

class UserInput(BaseModel):
    user_input: str
    user_email: str

class TextToSpeechRequest(BaseModel):
    text: str

# Graceful Shutdown the Handler
def signal_handler(sig, frame):
    print("Shutting down schedulers...")
    hourwise_scheduler.shutdown()
    daywise_scheduler.shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

@app.get("/")  # Root endpoint
async def root():
    return {"status": "healthy", "message": "FastAPI application is running"}

@app.post("/api/convoia-initialize-user")
async def initialize_user(user_data: UserInit):
    try:
        print("in convoia initialize-user")
        new_user_email = user_data.email_id

        # Start background task without awaiting it
        asyncio.create_task(perform_initialization(new_user_email, user_data.mode))

        # Return success immediately
        return {
            "status": "success",
            "message": "User initialization started",
            "email": user_data.email_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def perform_initialization(email_id: str, mode: str):
    try:
        print("in perform initialzation")
        # Your existing long-running initialization code
        existing_users_email_ids = get_all_email_ids()

        if email_id in existing_users_email_ids:
            print(f"\nModified New User Data Initialization {email_id}\n")
        else:
            print(f"\nNew User Data Initialization {email_id}\n")

        success = init_manager.new_user_initialization(
            email_id=email_id,
            mode=mode
        )
    except Exception as e:
        print(f"Error during initialization for {email_id}: {str(e)}")
    
@app.post("/api")
async def process_user_input(request: UserInput):
    
    try:
        print(f"Received input text: {request.user_input}")
        print(f"Received user email: {request.user_email}")
        
        message = f"This is a Health Check Response from the API Endpoint for user: {request.user_email}"
        return {"response": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/convoia-user-input")
async def process_user_input(request: UserInput):
    try:
        print(f"Received input text: {request.user_input}")
        print(f"Received user email: {request.user_email}")
        error_message = "Something Went Wrong Please Try Again"

        featureMatcher = FeatureMatcher()
        feature = featureMatcher.get_feature(request.user_input)

        print(f"\nIdentified feature: {feature}")
        print(f"Available functions: {list(FUNCTION_MAP.keys())}")

        if feature not in FUNCTION_MAP:
            print(f"Feature '{feature}' not found in FUNCTION_MAP")
            return {"response": error_message}
        
        handler_function = FUNCTION_MAP[feature]
        
        # Verify the handler is callable
        if not callable(handler_function):
            print(f"Handler for feature '{feature}' is not callable: {type(handler_function)}")
            return {"response": error_message}
        
        print(f"Calling handler function: {handler_function._name_}")
        
        result = await handler_function(
            text=request.user_input,
            email=request.user_email
        )

        print(f"\nHandler result: {result}")
        
        return {"response": result["message"]}
        
    except Exception as e:
        print(f"Exception: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {"response": error_message}

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        print("Received audio file for transcription")

        # Ensure the file is received
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        print(f"Received file: {file.filename}")
        print(f"File type: {file.content_type}")

        # Read the file content
        content = await file.read()
        print("Passed content = await file.read()")

        # Configure transcription options
        options = PrerecordedOptions(
            smart_format=True,
            model="nova-2",
            language="en-US"
        )
        print("Passed options")

        # Check if the mimetype is provided or default to "audio/wav"
        mimetype = file.content_type or "audio/wav"

        # Use a dict for the source (instead of instantiating FileSource)
        source = {"buffer": content, "mimetype": mimetype}
        print(f"source: {source}")

        # Offload the synchronous transcribe_file call to a thread
        response = await asyncio.to_thread(
            deepgram.listen.rest.v("1").transcribe_file,
            source,
            options
        )

        # Extract transcript from response
        if not response or not response.results or not response.results.channels:
            raise Exception("Invalid response format from Deepgram")

        transcript = response.results.channels[0].alternatives[0].transcript

        if not transcript:
            raise Exception("No transcript received from Deepgram")

        return {"transcript": transcript}

    except Exception as e:
        print(f"Transcription error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {str(e)}")
    
@app.post("/api/speak")
async def text_to_speech(request: TextToSpeechRequest):
    async def stream_speech():
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepgram.com/v1/speak",
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"text": request.text}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Deepgram API error: {error_text}")
                
                async for chunk in response.content.iter_any():
                    yield chunk

    return StreamingResponse(
        stream_speech(),
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'attachment; filename="speech.wav"'
        }
    )

# Set up the Schedules
hourwise_scheduler.schedule_task(interval_minutes=MINUTE_SCHEDULER)  
daywise_scheduler.schedule_task(hour=0, minute=0)

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8080)
