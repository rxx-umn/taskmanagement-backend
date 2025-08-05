### Instruksi Cara Menjalankan App

Pastikan Anda sudah menginstall:

- **Node.js** (v18 atau lebih baru)
- **Python** (v3.8 atau lebih baru)
- **PostgreSQL** (optional, bisa pakai SQLite)
- **OpenAI API Key** (untuk chatbot)

### 1. Clone Repository Frontend

git clone <repository-url>
cd task-management-frontend

### 2. Clone Repository Backend

git clone <repository-url>
cd task-management-backend 

### 3. Backend Setup (Flask)

#### 3.1 Create Virtual Environment

- Buka Terminal
# Windows
python -m venv venv
venv\Scripts\activate (untuk mengaktifkan environment)

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

#### 3.2 Install Dependencies
pip install -r requirements.txt

#### 3.3 Environment Variables
Buat file .env di root directory backend

# Database Configuration
DATABASE_URL= postgresql://username:password@localhost:5432/task_management

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-this-in-production

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Flask Configuration
FLASK_ENV=development
FLASK_APP=run.py

#### 3.4 Setup PostgreSQL
Buka Terminal

# Login ke PostgresSQL
psql -U postgres

# Buat database
CREATE DATABASE task_management;

# Keluar dari psql
\q

### 4. Menjalankan App (Backend)
cd task-management-backend

# Aktifkan virtual environment
Windows: venv\Scripts\activate
macOS/Linux: source venv/bin/activate

# Jalankan file kode setup_db.py di Terminal
python setup_db.py

**Note: Setelah menjalankan kode ini, maka akan mendapatkan info username dan password untuk digunakan login**

# Jalankan Server
python run.py


#### 4.1 Menjalankan App (Frontend)
cd task-management-frontend

# Install dependencies jika belum
npm install

# Jalankan development server
npm run dev

### 5. Cara Kerja Chatbot
Chatbot dapat menjawab pertanyaan seperti:
- "Show me all overdue tasks"
- "How many tasks are completed this week?"
- "Which tasks are assigned to John?"
- "What tasks are due today?"
- "Give me a summary of project progress"




