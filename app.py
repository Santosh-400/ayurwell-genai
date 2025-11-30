import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from pinecone import Pinecone
import google.generativeai as genai
from tavily import TavilyClient
from langchain_huggingface import HuggingFaceEmbeddings
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
INDEX_NAME = "ayurwell-index"

# Initialize Clients
if PINECONE_API_KEY:
    pc = Pinecone(api_key=PINECONE_API_KEY)
    pinecone_index = pc.Index(INDEX_NAME)
else:
    print("Warning: PINECONE_API_KEY not set")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    print("Warning: GOOGLE_API_KEY not set")

if TAVILY_API_KEY:
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
else:
    print("Warning: TAVILY_API_KEY not set")

# Initialize Embeddings (Local)
print("Loading local embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

@app.route('/')
def index():
    return render_template('index.html')

def query_pinecone(query_text):
    try:
        # Generate embedding locally
        embedding = embeddings.embed_query(query_text)
        results = pinecone_index.query(
            vector=embedding,
            top_k=3,
            include_metadata=True
        )
        print(f"DEBUG: Pinecone Results: {results}") # Debug print
        return results
    except Exception as e:
        print(f"Pinecone Error: {e}")
        return None

def query_tavily(query_text):
    try:
        response = tavily.search(query=query_text, search_depth="basic")
        context = "\n".join([r['content'] for r in response['results']])
        return context
    except Exception as e:
        print(f"Tavily Error: {e}")
        return None

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    image_data = data.get('image') # Base64 encoded image

    if not user_message and not image_data:
        return jsonify({"error": "No message or image provided"}), 400

    context = ""
    source = "Direct Knowledge"

    # Image Handling
    image_context = ""
    if image_data:
        try:
            # Remove header if present (e.g., "data:image/jpeg;base64,")
            if "," in image_data:
                image_data = image_data.split(",")[1]
            
            image_bytes = base64.b64decode(image_data)
            
            # Step 1: Extract context from image
            description_prompt = [
                {"mime_type": "image/jpeg", "data": image_bytes},
                """
                Analyze this image and provide a detailed medical/botanical description.
                Identify any visible symptoms, skin conditions, herbs, or plants.
                Do not provide advice yet, just describe what is seen.
                """
            ]
            
            image_response = model.generate_content(description_prompt)
            image_context = f"Image Analysis: {image_response.text}"
            source = "Gemini Vision + RAG"
            
        except Exception as e:
            return jsonify({"error": f"Image processing failed: {str(e)}"}), 500

    # Text Handling (RAG + Fallback)
    if user_message or image_context:
        # 0. Handle Greetings (only if no image)
        if not image_context:
            greetings = ["hi", "hello", "hey", "namaste", "greetings", "good morning", "good afternoon", "good evening"]
            if user_message and user_message.lower().strip() in greetings:
                return jsonify({
                    "response": "Namaste! 🙏 I am AyurWell, your Ayurvedic health assistant. How may I help you balance your Doshas today?",
                    "source": "Greeting"
                })

        # 0.5 Optimize Query for Retrieval (combining text and image context)
        try:
            optimization_prompt = f"""
            You are an expert at refining search queries for an Ayurvedic knowledge base.
            Rewrite the following user input (text and/or image description) into a specific, keyword-rich search query.
            
            User Question: {user_message}
            Image Context: {image_context}
            
            Goal: Create a search query to find Ayurvedic treatments for the condition or herb identified.
            
            Optimized Query (just the text):
            """
            optimized_query = model.generate_content(optimization_prompt).text.strip()
            print(f"DEBUG: Original Query: {user_message}")
            print(f"DEBUG: Image Context: {image_context[:100]}...")
            print(f"DEBUG: Optimized Query: {optimized_query}")
        except Exception as e:
            print(f"Query Optimization Error: {e}")
            optimized_query = f"{user_message} {image_context}"

        # 1. Try Pinecone with Optimized Query
        pinecone_results = query_pinecone(optimized_query)
        
        # Check if we have good matches
        is_relevant = False
        if pinecone_results and pinecone_results['matches']:
            best_match = pinecone_results['matches'][0]
            best_score = best_match['score']
            print(f"DEBUG: Best Score: {best_score}")
            print(f"DEBUG: Best Match Text: {best_match['metadata']['text'][:100]}...") # Print first 100 chars
            
            if best_score > 0.15: # Extremely low threshold for debugging
                is_relevant = True
                context = "\n\n".join([m['metadata']['text'] for m in pinecone_results['matches']])
                source = "AyurWell Knowledge Base"
        
        # 2. Fallback to Tavily if not relevant
        if not is_relevant:
            print("Low relevance in Pinecone, falling back to Tavily...")
            tavily_context = query_tavily(optimized_query)
            if tavily_context:
                context = tavily_context
                source = "Web Search (Tavily)"
        
        # 3. Generate Answer
        
        # Maintain a simple in-memory history (global for demo purposes, or passed from client)
        global chat_history
        if 'chat_history' not in globals():
            chat_history = []
        
        # Append user message
        chat_history.append(f"User: {user_message}")
        if image_context:
             chat_history.append(f"User Image Context: {image_context}")
        
        # Keep only last 10 exchanges to fit in context
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
            
        history_text = "\n".join(chat_history)

        prompt = f"""
        You are AyurWell, a compassionate and knowledgeable Ayurvedic health companion. Your goal is to guide users towards holistic wellness using the ancient wisdom of Ayurveda.

        CORE PRINCIPLES:
        1. **Ayurveda First**: Always prioritize Ayurvedic solutions (Herbs, Diet, Lifestyle, Yoga).
        2. **Holistic Approach**: Address the root cause, not just symptoms. Consider the user's Dosha (Vata, Pitta, Kapha) in your analysis.
        3. **Empathy & Warmth**: Speak with kindness and understanding. Use phrases like "I understand," "It sounds like," and "Let's bring balance."
        4. **Safety**: While you focus on Ayurveda, if a condition sounds critical or life-threatening, gently advise consulting a medical professional alongside Ayurvedic care.
        5. **No Allopathy**: Do not recommend modern pharmaceutical drugs (aspirin, antibiotics, etc.). If asked about them, gently steer the conversation back to natural Ayurvedic alternatives.
        6. **Scope Enforcement**: If the user asks about topics UNRELATED to health, wellness, or Ayurveda (e.g., coding, politics, movies, general knowledge), politely refuse. Say: "I am AyurWell, dedicated exclusively to Ayurvedic health and home remedies. I cannot assist with other topics."

        RESPONSE STRUCTURE:
        - **Dosha Insight**: Briefly explain the potential Dosha imbalance causing the issue (e.g., "This sounds like a Vata imbalance...").
        - **Herbal Remedies**: Suggest specific herbs (e.g., Ashwagandha, Tulsi, Triphala) and how to use them.
        - **Dietary Guidance (Ahara)**: Recommend foods to eat and foods to avoid.
        - **Lifestyle Tips (Vihara)**: Suggest daily routines (Dinacharya), sleep habits, or yoga poses.

        Chat History:
        {history_text}

        Context from Knowledge Base:
        {context}

        Image Context:
        {image_context}

        User Question:
        {user_message}

        Answer (in a warm, structured, and educational tone):
        """
        
        try:
            response = model.generate_content(prompt)
            bot_response = response.text
            
            # Append bot response to history
            chat_history.append(f"AyurWell: {bot_response}")
            
            return jsonify({"response": bot_response, "source": source})
        except Exception as e:
            return jsonify({"error": f"Generation failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
