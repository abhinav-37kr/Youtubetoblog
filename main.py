# FastAPI Backend for YouTube RAG Blog Generator
# pip install fastapi uvicorn youtube-transcript-api llama-index faiss-cpu openai python-multipart

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
import tempfile
import os
import re
import openai
from typing import Optional

# FastAPI app initialization
app = FastAPI(title="YouTube RAG Blog Generator API", version="1.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class YouTubeRequest(BaseModel):
    video_url: str
    api_key: str

class TranscriptResponse(BaseModel):
    transcript: str
    video_id: str
    success: bool
    message: str

class SummaryResponse(BaseModel):
    summary: str
    success: bool
    message: str

class BlogResponse(BaseModel):
    blog_content: str
    success: bool
    message: str

class ProcessResponse(BaseModel):
    transcript: str
    summary: str
    blog_content: str
    video_id: str
    success: bool
    message: str

# Utility functions
def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def setup_llama_index(api_key: str):
    """Setup LlamaIndex with OpenAI credentials"""
    openai.api_key = api_key
    Settings.llm = OpenAI(model="gpt-3.5-turbo", api_key=api_key)
    Settings.embed_model = OpenAIEmbedding(api_key=api_key)
    Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=200)

# API Endpoints
@app.get("/")
async def root():
    return {"message": "YouTube RAG Blog Generator API", "status": "running"}

@app.post("/extract-transcript", response_model=TranscriptResponse)
async def extract_transcript(request: YouTubeRequest):
    """Extract transcript from YouTube video"""
    try:
        # Extract video ID
        video_id = extract_video_id(request.video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        # Get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        
        return TranscriptResponse(
            transcript=transcript_text,
            video_id=video_id,
            success=True,
            message="Transcript extracted successfully"
        )
    
    except Exception as e:
        return TranscriptResponse(
            transcript="",
            video_id="",
            success=False,
            message=f"Error extracting transcript: {str(e)}"
        )

@app.post("/generate-summary", response_model=SummaryResponse)
async def generate_summary(request: YouTubeRequest):
    """Generate summary from transcript using RAG"""
    try:
        # Setup LlamaIndex
        setup_llama_index(request.api_key)
        
        # Extract transcript first
        video_id = extract_video_id(request.video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        
        # Create temporary file for transcript
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as f:
            f.write(transcript_text)
            temp_path = f.name
        
        try:
            # Load document and create index
            reader = SimpleDirectoryReader(input_files=[temp_path])
            documents = reader.load_data()
            
            # Build vector index
            index = VectorStoreIndex.from_documents(documents)
            query_engine = index.as_query_engine()
            
            # Generate summary
            response = query_engine.query(
                "Provide a comprehensive summary of this content in 3-4 paragraphs, "
                "highlighting the main topics, key insights, and important takeaways."
            )
            
            return SummaryResponse(
                summary=str(response),
                success=True,
                message="Summary generated successfully"
            )
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    
    except Exception as e:
        return SummaryResponse(
            summary="",
            success=False,
            message=f"Error generating summary: {str(e)}"
        )

@app.post("/generate-blog", response_model=BlogResponse)
async def generate_blog(request: YouTubeRequest):
    """Generate blog post from transcript using RAG"""
    try:
        # Setup LlamaIndex
        setup_llama_index(request.api_key)
        
        # Extract transcript
        video_id = extract_video_id(request.video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as f:
            f.write(transcript_text)
            temp_path = f.name
        
        try:
            # Load document and create index
            reader = SimpleDirectoryReader(input_files=[temp_path])
            documents = reader.load_data()
            
            # Build vector index
            index = VectorStoreIndex.from_documents(documents)
            query_engine = index.as_query_engine()
            
            # Generate blog post
            blog_prompt = """
            Write a comprehensive, engaging blog post based on this content. 
            Structure it with:
            1. An engaging title and introduction
            2. Main sections with clear headings
            3. Key insights and explanations
            4. Practical examples or applications
            5. A compelling conclusion
            
            Make it informative, well-structured, and engaging for readers.
            Use HTML formatting for headings (<h3>) and paragraphs (<p>).
            """
            
            response = query_engine.query(blog_prompt)
            
            return BlogResponse(
                blog_content=str(response),
                success=True,
                message="Blog post generated successfully"
            )
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    
    except Exception as e:
        return BlogResponse(
            blog_content="",
            success=False,
            message=f"Error generating blog: {str(e)}"
        )

@app.post("/process-complete", response_model=ProcessResponse)
async def process_complete(request: YouTubeRequest):
    """Complete processing pipeline: transcript -> summary -> blog"""
    try:
        # Setup LlamaIndex
        setup_llama_index(request.api_key)
        
        # Extract transcript
        video_id = extract_video_id(request.video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as f:
            f.write(transcript_text)
            temp_path = f.name
        
        try:
            # Load document and create index
            reader = SimpleDirectoryReader(input_files=[temp_path])
            documents = reader.load_data()
            
            # Build vector index
            index = VectorStoreIndex.from_documents(documents)
            query_engine = index.as_query_engine()
            
            # Generate summary
            summary_response = query_engine.query(
                "Provide a comprehensive summary of this content in 3-4 paragraphs, "
                "highlighting the main topics, key insights, and important takeaways."
            )
            
            # Generate blog post
            blog_prompt = """
            Write a comprehensive, engaging blog post based on this content. 
            Structure it with:
            1. An engaging title and introduction
            2. Main sections with clear headings
            3. Key insights and explanations
            4. Practical examples or applications
            5. A compelling conclusion
            
            Make it informative, well-structured, and engaging for readers.
            Use HTML formatting for headings (<h3>) and paragraphs (<p>).
            """
            
            blog_response = query_engine.query(blog_prompt)
            
            return ProcessResponse(
                transcript=transcript_text,
                summary=str(summary_response),
                blog_content=str(blog_response),
                video_id=video_id,
                success=True,
                message="Complete processing successful"
            )
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    
    except Exception as e:
        return ProcessResponse(
            transcript="",
            summary="",
            blog_content="",
            video_id="",
            success=False,
            message=f"Error in complete processing: {str(e)}"
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "FastAPI server is running"}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)