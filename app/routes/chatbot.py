import os
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from openai import OpenAI
import httpx
from datetime import datetime, date
from app.models.task import Task
from app.models.user import User

chatbot_bp = Blueprint('chatbot', __name__)

# Matikan proxy supaya tidak bentrok di Windows
os.environ["NO_PROXY"] = "*"

# Inisialisasi OpenAI client tanpa proxy
http_client_no_proxy = httpx.Client()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), http_client=http_client_no_proxy)

# In-memory conversation storage (untuk production, gunakan Redis atau database)
conversation_memory = {}

def clean_markdown_response(text):
    """Membersihkan markdown formatting dari response AI"""
    if not text:
        return text
    
    # Remove bold markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Remove italic markdown
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Remove headers
    text = re.sub(r'#{1,6}\s*(.*)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove links
    text = re.sub(r'\[([^\]]+)\]$$[^)]+$$', r'\1', text)
    
    # Remove strikethrough
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def manage_conversation_memory():
    """Clean up old conversations to prevent memory bloat"""
    current_time = datetime.now()
    # Remove conversations older than 1 hour
    expired_conversations = []
    
    for conv_id, conv_data in conversation_memory.items():
        if 'last_activity' in conv_data:
            time_diff = current_time - conv_data['last_activity']
            if time_diff.total_seconds() > 3600:  # 1 hour
                expired_conversations.append(conv_id)
    
    for conv_id in expired_conversations:
        del conversation_memory[conv_id]

@chatbot_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat_with_ai():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        conversation_id = data.get('conversation_id', '')
        tasks_data = data.get('tasks', [])

        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        # Clean up old conversations
        manage_conversation_memory()

        # Ambil user saat ini
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        # Jika tidak ada tasks dari frontend, ambil dari database
        if not tasks_data:
            tasks = Task.query.all()
            tasks_data = [task.to_dict() for task in tasks]

        # Hitung statistik task
        today = date.today()
        task_summary = {
            'total_tasks': len(tasks_data),
            'completed_tasks': len([t for t in tasks_data if t['status'] == 'Done']),
            'in_progress_tasks': len([t for t in tasks_data if t['status'] == 'In Progress']),
            'todo_tasks': len([t for t in tasks_data if t['status'] == 'Todo']),
            'overdue_tasks': len([
                t for t in tasks_data
                if datetime.strptime(t['deadline'], '%Y-%m-%d').date() < today and t['status'] != 'Done'
            ]),
            'due_today': len([
                t for t in tasks_data
                if datetime.strptime(t['deadline'], '%Y-%m-%d').date() == today
            ])
        }

        # Format task data untuk context yang lebih readable
        formatted_tasks = []
        for task in tasks_data:
            deadline_date = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
            is_overdue = deadline_date < today and task['status'] != 'Done'
            is_due_today = deadline_date == today
            
            task_info = f"- {task['title']} (Status: {task['status']}, Assignee: {task['assignee_name']}, Deadline: {task['deadline']}"
            if is_overdue:
                task_info += " - OVERDUE"
            elif is_due_today:
                task_info += " - DUE TODAY"
            task_info += ")"
            formatted_tasks.append(task_info)

        # Store/update conversation context
        if conversation_id:
            if conversation_id not in conversation_memory:
                conversation_memory[conversation_id] = {
                    'user_id': current_user_id,
                    'messages': [],
                    'created_at': datetime.now(),
                    'last_activity': datetime.now()
                }
            
            # Update last activity
            conversation_memory[conversation_id]['last_activity'] = datetime.now()
            
            # Add current message to memory
            conversation_memory[conversation_id]['messages'].append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })

        # Prompt sistem untuk AI - DENGAN CONTEXT AWARENESS
        system_prompt = f"""You are an AI Task Management Assistant for {current_user.name}. You have access to comprehensive task data and can provide insights, analysis, and answers about tasks.

IMPORTANT FORMATTING RULES:
- Use PLAIN TEXT only, no markdown formatting
- Do not use asterisks (*), underscores (_), hashtags (#), or backticks (`)
- Use simple dashes (-) for bullet points if needed
- Use line breaks for structure
- Be conversational and friendly
- Keep responses concise but helpful
- Remember previous conversation context and refer to it when relevant

CURRENT TASK STATISTICS:
- Total Tasks: {task_summary['total_tasks']}
- Completed: {task_summary['completed_tasks']}
- In Progress: {task_summary['in_progress_tasks']}
- Todo: {task_summary['todo_tasks']}
- Overdue: {task_summary['overdue_tasks']}
- Due Today: {task_summary['due_today']}

TASK LIST:
{chr(10).join(formatted_tasks) if formatted_tasks else "No tasks available"}

CAPABILITIES:
- Task analysis and statistics
- Finding specific tasks by status, assignee, or deadline
- Identifying overdue or upcoming tasks
- Providing productivity insights
- Task prioritization suggestions
- Team workload analysis
- Remember and reference previous conversation context

CURRENT DATE: {today.strftime('%Y-%m-%d')}

CONVERSATION CONTEXT: You can reference previous messages in this conversation. Be helpful and maintain context awareness.

Please provide helpful, accurate, and actionable responses in plain text format. Be supportive and professional."""

        # Prepare messages for OpenAI API
        messages_for_api = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to prevent token overflow)
        if conversation_history:
            # Limit to last 8 messages to manage token usage
            recent_history = conversation_history[-8:]
            messages_for_api.extend(recent_history)
        
        # Add current user message
        messages_for_api.append({"role": "user", "content": user_message})

        # Panggil OpenAI API dengan conversation history
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_api,
            max_tokens=600,  # Increased slightly for context-aware responses
            temperature=0.7
        )

        ai_response = response.choices[0].message.content.strip()
        
        # Clean markdown dari response (double protection)
        cleaned_response = clean_markdown_response(ai_response)

        # Store AI response in conversation memory
        if conversation_id and conversation_id in conversation_memory:
            conversation_memory[conversation_id]['messages'].append({
                'role': 'assistant',
                'content': cleaned_response,
                'timestamp': datetime.now().isoformat()
            })

        return jsonify({
            'response': cleaned_response,
            'status': 'success',
            'task_count': task_summary['total_tasks'],
            'conversation_id': conversation_id,
            'context_enabled': True
        }), 200

    except Exception as e:
        print(f"Chatbot error: {str(e)}")  # Log error untuk debugging
        return jsonify({
            'error': 'Failed to process chat request',
            'details': str(e)
        }), 500

@chatbot_bp.route('/chat/history/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation_history(conversation_id):
    """Get conversation history for a specific conversation"""
    try:
        current_user_id = get_jwt_identity()
        
        if conversation_id in conversation_memory:
            conv_data = conversation_memory[conversation_id]
            
            # Check if user owns this conversation
            if conv_data['user_id'] == current_user_id:
                return jsonify({
                    'conversation_id': conversation_id,
                    'messages': conv_data['messages'],
                    'created_at': conv_data['created_at'].isoformat(),
                    'last_activity': conv_data['last_activity'].isoformat()
                }), 200
            else:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Conversation not found'}), 404
            
    except Exception as e:
        return jsonify({'error': 'Failed to get conversation history', 'details': str(e)}), 500

@chatbot_bp.route('/chat/clear/<conversation_id>', methods=['DELETE'])
@jwt_required()
def clear_conversation(conversation_id):
    """Clear a specific conversation"""
    try:
        current_user_id = get_jwt_identity()
        
        if conversation_id in conversation_memory:
            conv_data = conversation_memory[conversation_id]
            
            # Check if user owns this conversation
            if conv_data['user_id'] == current_user_id:
                del conversation_memory[conversation_id]
                return jsonify({'message': 'Conversation cleared successfully'}), 200
            else:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Conversation not found'}), 404
            
    except Exception as e:
        return jsonify({'error': 'Failed to clear conversation', 'details': str(e)}), 500

@chatbot_bp.route('/chat/health', methods=['GET'])
@jwt_required()
def chat_health():
    """Cek apakah OpenAI API siap dipakai"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'status': 'error', 'message': 'OpenAI API key not configured'}), 500

        if not api_key.startswith('sk-'):
            return jsonify({'status': 'error', 'message': 'Invalid OpenAI API key format'}), 500

        return jsonify({
            'status': 'healthy', 
            'message': 'OpenAI API is working properly',
            'model': 'gpt-4o-mini',
            'context_enabled': True,
            'active_conversations': len(conversation_memory)
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': 'Health check failed', 
            'details': str(e)
        }), 500

@chatbot_bp.route('/chat/test', methods=['POST'])
@jwt_required()
def test_chat():
    """Endpoint untuk test chatbot tanpa OpenAI"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Simple test response with context awareness
        context_info = f" (I can see {len(conversation_history)} previous messages)" if conversation_history else ""
        test_response = f"Hello {current_user.name}! I received your message: '{user_message}'{context_info}. This is a test response without OpenAI."
        
        return jsonify({
            'response': test_response,
            'status': 'success',
            'mode': 'test',
            'context_enabled': True
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Test failed',
            'details': str(e)
        }), 500
