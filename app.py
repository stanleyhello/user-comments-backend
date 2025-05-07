import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Supabase setup
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# Groq setup
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

@app.route('/')
def root():
    return jsonify({"message": "Backend running"}), 200

@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    try:
        # Log the incoming request data
        app.logger.info(f"Received data: {request.json}")
        
        data = request.json
        company = data.get('company')
        comment = data.get('comment')

        # Validate input
        if not company or not comment:
            app.logger.warning("Invalid input: Missing company or comment")
            return jsonify({"status": "error", "message": "Company and comment are required"}), 400

        # Insert comment into Supabase
        response = supabase.table('comments').insert({
            'company': company,
            'comment': comment
        }).execute()
        
        app.logger.info(f"Supabase insert response: {response}")
        return jsonify({"status": "success", "message": "Comment submitted successfully"}), 200
    
    except Exception as e:
        # Log the full error
        app.logger.error(f"Error submitting comment: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_summary', methods=['GET'])
def get_summary():
    try:
        response = supabase.table('comments').select('*').execute()
        comments = response.data

        if comments:
            comments_text = "\n".join([c['comment'] for c in comments])
            summary_response = groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes user comments about a company."},
                    {"role": "user", "content": f"Summarize the following comments:\n{comments_text}"}
                ]
            )
            summary = summary_response.choices[0].message.content
            return jsonify({"status": "success", "summary": summary}), 200
        else:
            return jsonify({"status": "success", "summary": "No comments available."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
