
class YouTubeRAGAPI {
    constructor() {
        this.baseURL = 'http://localhost:8000';
        this.apiKey = '';
    }

    async makeRequest(endpoint, data) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async extractTranscript(videoUrl, apiKey) {
        const response = await this.makeRequest('/extract-transcript', {
            video_url: videoUrl,
            api_key: apiKey
        });

        if (!response.success) {
            throw new Error(response.message);
        }

        return response.transcript;
    }

    async generateSummary(videoUrl, apiKey) {
        const response = await this.makeRequest('/generate-summary', {
            video_url: videoUrl,
            api_key: apiKey
        });

        if (!response.success) {
            throw new Error(response.message);
        }

        return response.summary;
    }

    async generateBlog(videoUrl, apiKey) {
        const response = await this.makeRequest('/generate-blog', {
            video_url: videoUrl,
            api_key: apiKey
        });

        if (!response.success) {
            throw new Error(response.message);
        }

        return response.blog_content;
    }

    async processComplete(videoUrl, apiKey) {
        const response = await this.makeRequest('/process-complete', {
            video_url: videoUrl,
            api_key: apiKey
        });

        if (!response.success) {
            throw new Error(response.message);
        }

        return {
            transcript: response.transcript,
            summary: response.summary,
            blog: response.blog_content,
            videoId: response.video_id
        };
    }

    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    extractVideoId(url) {
        const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/;
        const match = url.match(regex);
        return match ? match[1] : null;
    }
}

// Initialize API
const api = new YouTubeRAGAPI();

// DOM elements
const generateBtn = document.getElementById('generate-btn');
const youtubeUrl = document.getElementById('youtube-url');
const resultsSection = document.getElementById('results-section');
const blogSection = document.getElementById('blog-section');
const transcriptContent = document.getElementById('transcript-content');
const summaryContent = document.getElementById('summary-content');
const blogContent = document.getElementById('blog-content');
const serverStatus = document.getElementById('server-status');
const serverStatusText = document.getElementById('server-status-text');

// Check server status on page load
async function checkServerStatus() {
    try {
        const isHealthy = await api.checkHealth();
        updateServerStatus(isHealthy);
    } catch (error) {
        updateServerStatus(false);
    }
}

function updateServerStatus(isOnline) {
    if (isOnline) {
        serverStatus.className = 'server-status online';
        serverStatusText.textContent = 'FastAPI Server: Online';
        generateBtn.disabled = false;
    } else {
        serverStatus.className = 'server-status offline';
        serverStatusText.textContent = 'FastAPI Server: Offline - Please start the server';
        generateBtn.disabled = true;
    }
}

// Check server status every 30 seconds
setInterval(checkServerStatus, 30000);
checkServerStatus(); // Initial check

// Event listeners
generateBtn.addEventListener('click', handleGenerate);

async function handleGenerate() {
    const url = youtubeUrl.value.trim();
    const apiKey = ""; // Replace with your OpenAI API key

    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }

    if (!apiKey) {
        showError('Please enter your OpenAI API key');
        return;
    }

    if (!api.extractVideoId(url)) {
        showError('Please enter a valid YouTube URL');
        return;
    }

    try {
        // Check if FastAPI server is running
        showStep('Checking server connection...');
        const isHealthy = await api.checkHealth();
        if (!isHealthy) {
            showError('FastAPI server is not running. Please start the server with: uvicorn main:app --reload');
            setLoadingState(false);
            return;
        }

        // Set loading state
        setLoadingState(true);
        hideResults();

        // Use complete processing endpoint for efficiency
        showStep('Processing video with RAG pipeline...');
        const result = await api.processComplete(url, apiKey);

        // Display results
        transcriptContent.textContent = result.transcript;
        summaryContent.textContent = result.summary;
        blogContent.innerHTML = result.blog;

        // Show results
        resultsSection.style.display = 'grid';
        blogSection.style.display = 'block';

        // Reset loading state
        setLoadingState(false);

        // Smooth scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Processing error:', error);
        showError('An error occurred: ' + error.message);
        setLoadingState(false);
    }
}

function setLoadingState(loading) {
    generateBtn.disabled = loading;
    generateBtn.textContent = loading ? 'Processing...' : 'Generate Blog Post';
}

function showStep(message) {
    generateBtn.textContent = message;
}

function showError(message) {
    // Remove existing error messages
    const existingErrors = document.querySelectorAll('.error');
    existingErrors.forEach(error => error.remove());

    // Create new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;

    // Insert after input section
    const inputSection = document.querySelector('.input-section');
    inputSection.insertAdjacentElement('afterend', errorDiv);
}

function hideResults() {
    resultsSection.style.display = 'none';
    blogSection.style.display = 'none';
}

// Add some sample URLs for testing
const sampleUrls = [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/watch?v=J---aiyznGQ',
    'https://www.youtube.com/watch?v=kJQP7kiw5Fk'
];

// Add sample URL functionality
youtubeUrl.addEventListener('focus', function () {
    if (!this.value) {
        this.placeholder = 'Try: ' + sampleUrls[Math.floor(Math.random() * sampleUrls.length)];
    }
});