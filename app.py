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

    try:
        supabase.table('comments').insert({
            'company': company,
            'comment': comment
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
                    {"role": "system", "content": "You are a helpful assistant that summarizes user comments about a company."},
                    {"role": "user", "content": f"Summarize the following comments, highlighting key themes and sentiments:\n{comments_text}"}
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
