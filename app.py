import os
from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ Add this line
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import json

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

@app.route('/chart/issues', methods=['GET'])
def get_common_issues():
    try:
        # Fetch all comments from Supabase
        response = supabase.table('comments').select('comment').execute()
        comments = [row['comment'] for row in response.data if row['comment']]

        # If no comments, return empty result
        if not comments:
            return jsonify({
                'status': 'success', 
                'issues': {}
            }), 200

        # Prepare prompt for Groq
        prompt = f"""Analyze the following user comments and extract the top 5 most frequently mentioned issues or themes. 
        Return a JSON object where keys are issue names and values are their occurrence counts. 
        Be concise and focus on substantive themes.

        Comments:
{chr(10).join(comments[:100])}

JSON Response:"""

        # Call Groq to analyze comments
        chat_completion = groq_client.chat.completions.create(
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            model='llama3-70b-8192',
            response_format={'type': 'json_object'}
        )

        # Parse and return results
        result_text = chat_completion.choices[0].message.content
        issues = json.loads(result_text)

        return jsonify({
            'status': 'success', 
            'issues': issues
        }), 200

    except Exception as e:
        print(f"Error in get_common_issues: {e}")
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

@app.route('/generate_comments', methods=['POST'])
def generate_comments():
    try:
        data = request.json
        prompt = data.get('prompt', '').strip()
        count = min(max(int(data.get('count', 5)), 1), 20)  # Ensure count is between 1-20

        if not prompt:
            return jsonify({"status": "error", "error": "Prompt is required"}), 400

        # Extract company name from prompt (simple implementation - last word)
        company = prompt.split()[-1] if prompt.split() else 'Company'
        
        # Generate comments using Groq
        system_prompt = """You are a helpful assistant that generates realistic user comments about companies. 
        Generate {count} unique, varied comments based on the following prompt. 
        Return ONLY a JSON array of comment strings, nothing else."""
        
        user_prompt = f"""Generate {count} realistic user comments about {prompt}. 
        Make each comment unique and varied in length and style. 
        Some should be positive, some negative, and some neutral.
        
        Example format:
        [
            "This is a positive comment about the company.",
            "I had a negative experience with their service.",
            "The product quality is average, nothing special."
        ]"""
        
        # Call Groq API
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            # Try to parse the response as JSON
            response_text = response.choices[0].message.content
            comments = json.loads(response_text)
            
            # If the response is a dictionary with a 'comments' key, use that
            if isinstance(comments, dict) and 'comments' in comments:
                comments = comments['comments']
            # If the response is a dictionary with array values, use the first array found
            elif isinstance(comments, dict):
                for value in comments.values():
                    if isinstance(value, list):
                        comments = value
                        break
            
            # Ensure we have a list of strings
            if not isinstance(comments, list):
                comments = [str(comments)]
                
            # Insert comments into the database
            inserted_count = 0
            for comment_text in comments:
                if not isinstance(comment_text, str) or not comment_text.strip():
                    continue
                    
                try:
                    supabase.table('comments').insert({
                        'company': company,
                        'comment': comment_text.strip(),
                        'name': 'Sample User',
                        'email': 'sample@example.com',
                        'is_sample': True
                    }).execute()
                    inserted_count += 1
                except Exception as e:
                    print(f"Error inserting comment: {e}")
            
            return jsonify({
                "status": "success",
                "count": inserted_count,
                "message": f"Successfully generated {inserted_count} sample comments"
            })
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract comments from plain text
            print("Failed to parse JSON response, falling back to text parsing")
            return jsonify({
                "status": "error",
                "error": "Failed to parse the generated comments. Please try again."
            }), 500
            
    except Exception as e:
        print(f"Error in generate_comments: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/chart/sentiment', methods=['GET'])
def get_sentiment_over_time():
    try:
        # Fetch comments with timestamp from Supabase
        response = supabase.table('comments').select('created_at, comment').execute()
        comments = response.data

        # If no comments, return empty result
        if not comments:
            return jsonify({
                'status': 'success', 
                'sentiment_trends': {}
            }), 200

        # Prepare prompt for Groq to analyze sentiment
        comments_text = "\n".join([f"{comment['created_at']}: {comment['comment']}" for comment in comments[:100]])
        
        prompt = """Analyze the sentiment of the following comments and group them by day. 
        Provide a VALID JSON object with days as keys (YYYY-MM-DD) and average sentiment scores (-1 to 1) as values.
        IMPORTANT: Ensure the JSON is PERFECTLY FORMATTED with no trailing commas or syntax errors.
        IMPORTANT: Do NOT respond with just a string or a single key. Always return a full JSON object with at least one day as the key and a numeric sentiment score as the value.
        Example valid format: {"2025-05-08": 0.25, "2025-05-09": 0.13}

        Guidelines for sentiment:
        - Negative sentiment: -1 to -0.3
        - Neutral sentiment: -0.3 to 0.3
        - Positive sentiment: 0.3 to 1

        Comments:
{}

JSON Response (MUST be valid JSON):""".format(comments_text)

        # Call Groq to analyze sentiment
        chat_completion = groq_client.chat.completions.create(
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            model='llama3-70b-8192',
            response_format={'type': 'json_object'}
        )

        # Parse and return results
        result_text = chat_completion.choices[0].message.content
        
        # Attempt to clean and parse the JSON
        try:
            # Remove any leading/trailing whitespace
            result_text = result_text.strip()

            # Attempt to extract the largest JSON object (from first { to last })
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = result_text  # fallback to the original

            print("Extracted JSON string:", json_str)
            print("Full LLM response:", result_text)

            # Parse the JSON
            sentiment_trends = json.loads(json_str)

            # Defensive: Check if we got a dict
            if not isinstance(sentiment_trends, dict):
                raise ValueError(f"Expected a JSON object, got {type(sentiment_trends)}: {sentiment_trends}")

            return jsonify({
                'status': 'success',
                'sentiment_trends': sentiment_trends
            }), 200

        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON Parsing Error: {e}")
            print(f"Problematic JSON text: {result_text}")
            return jsonify({
                'status': 'error',
                'message': f'Failed to parse sentiment data: {str(e)}'
            }), 500

    except Exception as e:
        print(f"Error in get_sentiment_over_time: {e}")
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
