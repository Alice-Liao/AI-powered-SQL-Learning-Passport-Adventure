# AI-powered SQL Learning Passport Adventure

Welcome to the AI-powered SQL Learning Passport Adventure project! This is a Django-based web application designed to support interactive SQL learning experiences.

---

## 🌐 Live Deployment
The project is deployed on Google App Engine:

**URL:** https://db-group8-451523.uc.r.appspot.com

---

## 🗂 Project Structure
```
├── group8project/          # Django project settings
├── your_app/               # Your Django app(s)
├── manage.py               # Django entry point
├── app.yaml                # App Engine deployment config
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── README.md               # Project documentation
```

---

## 🚀 Getting Started (Local Setup)

### 1. Clone the Repository
```bash
git clone https://github.com/Alice-Liao/AI-powered-SQL-Learning-Passport-Adventure.git
cd AI-powered-SQL-Learning-Passport-Adventure
```

### 2. Create and Configure `.env` File
Create a `.env` file based on `.env.example` and fill in the actual secrets:

```bash
cp .env.example .env
```

Example:
```env
DJANGO_SECRET_KEY=your-secret-key
DATABASE_NAME=sql_training
DATABASE_USER=admin
DATABASE_PASSWORD=database_group8
DATABASE_HOST=34.72.11.31
DATABASE_PORT=5432
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Migrations
```bash
python manage.py migrate
```

### 5. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` to view the app locally.

---

## ☁️ Deployment to GCP App Engine
Make sure the Google Cloud CLI is installed and authenticated:

### 1. Deploy
```bash
gcloud app deploy
```

### 2. View Logs
```bash
gcloud app logs tail -s default
```

---

## 🛠 Tech Stack
- Python 3.10+
- Django 5.1.6
- PostgreSQL (hosted on GCP VM)
- Google App Engine (Standard Environment)

---

## 🤝 Collaboration Guidelines
1. Clone the project.
2. Create your own branch: `git checkout -b your-feature-branch`
3. Commit regularly.
4. Push and create a PR for review.

---

## 📄 License
This project is for educational purposes.

---

Feel free to contribute and make learning SQL more fun and interactive! 🚀

