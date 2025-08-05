from app import create_app, db
from app.models.user import User
from app.models.task import Task
from datetime import datetime, date

app = create_app()

with app.app_context():
    # Drop all tables and recreate
    db.drop_all()
    db.create_all()
    
    # Create default users
    users_data = [
        {'name': 'Admin User', 'username': 'admin', 'password': 'admin123'},
        {'name': 'John Doe', 'username': 'john', 'password': 'john123'},
        {'name': 'Jane Smith', 'username': 'jane', 'password': 'jane123'},
        {'name': 'Alice Johnson', 'username': 'alice', 'password': 'alice123'},
        {'name': 'Bob Wilson', 'username': 'bob', 'password': 'bob123'}
    ]
    
    created_users = []
    for user_data in users_data:
        user = User(
            name=user_data['name'],
            username=user_data['username']
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()
    
    # Create sample tasks
    sample_tasks = [
        {
            'title': 'Setup Development Environment',
            'description': 'Install and configure all necessary development tools',
            'status': 'Done',
            'deadline': date(2024, 8, 1),
            'assignee_id': 1,
            'created_by': 1
        },
        {
            'title': 'Design Database Schema',
            'description': 'Create ERD and design database tables for the application',
            'status': 'In Progress',
            'deadline': date(2024, 8, 10),
            'assignee_id': 2,
            'created_by': 1
        },
        {
            'title': 'Implement User Authentication',
            'description': 'Build login/logout functionality with JWT tokens',
            'status': 'Todo',
            'deadline': date(2024, 8, 15),
            'assignee_id': 3,
            'created_by': 1
        },
        {
            'title': 'Create Task Management UI',
            'description': 'Build responsive frontend for task management',
            'status': 'Todo',
            'deadline': date(2024, 8, 20),
            'assignee_id': 4,
            'created_by': 1
        },
        {
            'title': 'Write API Documentation',
            'description': 'Document all API endpoints and usage examples',
            'status': 'Todo',
            'deadline': date(2024, 8, 25),
            'assignee_id': 5,
            'created_by': 1
        }
    ]
    
    for task_data in sample_tasks:
        task = Task(**task_data)
        db.session.add(task)
    
    db.session.commit()
    
    print("✅ Database setup completed!")
    print("✅ Default users created!")
    print("✅ Sample tasks created!")
    print("\n🔑 Default login credentials:")
    for user_data in users_data:
        print(f"Username: {user_data['username']} | Password: {user_data['password']}")
    
    print(f"\n📊 Created {len(sample_tasks)} sample tasks")