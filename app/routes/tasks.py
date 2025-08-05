from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.task import Task
from app.models.user import User
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('', methods=['GET'])
@jwt_required()
def get_tasks():
    try:
        tasks = Task.query.all()
        return jsonify([task.to_dict() for task in tasks]), 200
    
    except Exception as e:
        return jsonify({'message': 'Failed to fetch tasks', 'error': str(e)}), 500

@tasks_bp.route('', methods=['POST'])
@jwt_required()
def create_task():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['title', 'description', 'deadline', 'assignee_id']
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Missing required fields'}), 400
        
        # Validate assignee exists
        assignee = User.query.get(data['assignee_id'])
        if not assignee:
            return jsonify({'message': 'Assignee not found'}), 404
        
        task = Task(
            title=data['title'],
            description=data['description'],
            status=data.get('status', 'Todo'),
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date(),
            assignee_id=data['assignee_id'],
            created_by=current_user_id
        )
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify(task.to_dict()), 201
    
    except ValueError as e:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'message': 'Failed to create task', 'error': str(e)}), 500

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        return jsonify(task.to_dict()), 200
    
    except Exception as e:
        return jsonify({'message': 'Task not found', 'error': str(e)}), 404

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        data = request.get_json()
        
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'status' in data:
            if data['status'] in ['Todo', 'In Progress', 'Done']:
                task.status = data['status']
            else:
                return jsonify({'message': 'Invalid status'}), 400
        if 'deadline' in data:
            task.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
        if 'assignee_id' in data:
            assignee = User.query.get(data['assignee_id'])
            if not assignee:
                return jsonify({'message': 'Assignee not found'}), 404
            task.assignee_id = data['assignee_id']
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(task.to_dict()), 200
    
    except ValueError as e:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'message': 'Failed to update task', 'error': str(e)}), 500

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({'message': 'Task deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': 'Failed to delete task', 'error': str(e)}), 500

@tasks_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_task_stats():
    try:
        total_tasks = Task.query.count()
        completed_tasks = Task.query.filter_by(status='Done').count()
        in_progress_tasks = Task.query.filter_by(status='In Progress').count()
        todo_tasks = Task.query.filter_by(status='Todo').count()
        
        # Overdue tasks
        today = datetime.now().date()
        overdue_tasks = Task.query.filter(
            Task.deadline < today,
            Task.status != 'Done'
        ).count()
        
        return jsonify({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'todo_tasks': todo_tasks,
            'overdue_tasks': overdue_tasks
        }), 200
    
    except Exception as e:
        return jsonify({'message': 'Failed to get task stats', 'error': str(e)}), 500