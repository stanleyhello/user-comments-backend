import os
from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ Add this line
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["https://user-comments-frontend.vercel.app"])  # ✅ Enable CORS for your frontend

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
    data = request.json
    company = data.get('company')
    comment = data.get('comment')
    name = data.get('name')
    email = data.get('email')

    try:
        supabase.table('comments').insert({
            'company': company,
            'comment': comment,
            'name': name,
            'email': email
        }).execute()
        return jsonify({"status": "success", "message": "Comment submitted successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_summary', methods=['GET'])
def get_summary():
    try:
        response = supabase.table('comments').select('*').execute()
        comments = response.data

        if comments:
            comments_text = "\n".join([c['comment'] for c in comments])
            summary_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes user comments about a company. Always provide a concise summary in 4 sentences or less."},
                    {"role": "user", "content": f"Summarize the following comments, highlighting key themes and sentiments in 4 sentences maximum. Summarize overall sentiment, don't just restate each comment:\n{comments_text}"}
                ]
            )

            summary = summary_response.choices[0].message.content
            return jsonify({"status": "success", "summary": summary}), 200
        else:
            return jsonify({"status": "success", "summary": "No comments available."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/query_comments', methods=['POST'])
def query_comments():
    try:
        # Get the user's query from the request
        user_query = request.json.get('query')
        
        # Fetch all comments from Supabase
        response = supabase.table('comments').select('*').execute()
        comments = response.data
        
        if comments:
            # Combine all comments into a single text block
            comments_text = "\n".join([f"Comment about {c['company']}: {c['comment']}" for c in comments])
            
            # Use Groq to generate a response based on the query and comments
            query_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes user comments about companies. Provide concise, relevant answers based on the available comments."},
                    {"role": "user", "content": f"Context of comments:\n{comments_text}\n\nUser Query: {user_query}\n\nPlease provide a helpful response based on the available comments. Keep your answer concise and to the point."}
                ]
            )
            
            # Extract and return the response
            answer = query_response.choices[0].message.content
            return jsonify({"status": "success", "answer": answer}), 200
        else:
            return jsonify({"status": "success", "answer": "No comments are available to query."}), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_all_comments', methods=['GET'])
def get_all_comments():
    try:
        response = supabase.table('comments').select('*').execute()
        comments = response.data

        return jsonify({
            "status": "success", 
            "comments": comments
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
