# SANCTUARY - A Secure Learning Material Platform

SANCTUARY is a Django-based web platform designed to be a safe space for sharing and storing learning materials, particularly for software engineering students. The platform provides organized access to course materials through a role-based permission system.

## 🌟 Features

### User Roles
- **Super Admin:** Platform-wide management, approves study groups, monitors all activities
- **Admin (Group Leader):** Creates study groups, manages members, creates courses
- **User (Group Member):** Accesses learning materials, creates topics, uploads files

### Core Functionality
- **Study Groups:** Create and join private groups for collaborative learning
- **Courses & Topics:** Organize learning content by courses and specific topics
- **File Management:** Upload and access various types of learning materials
- **Activity Tracking:** Monitor user actions and file uploads

### Security & Access Control
- Role-based permissions
- Private group access
- Content moderation by admins

## 💻 Technical Stack

- **Framework:** Django (MVC architecture)
- **Database:** SQLite (default)
- **Authentication:** Django's built-in authentication with custom User model
- **Frontend:** Bootstrap 5 with Django templates
- **File Storage:** Local media storage

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository or download the source code

2. Create and activate a virtual environment:
```
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install required dependencies:
```
pip install django django-widget-tweaks
```

4. Apply database migrations:
```
python manage.py migrate
```

5. Create a superuser:
```
python manage.py createsuperuser
```

6. Run the development server:
```
python manage.py runserver
```

7. Access the platform at http://127.0.0.1:8000

## 👥 User Guide

### Super Admin
- Log in with your superuser credentials
- Approve or reject study group requests
- Monitor system-wide activity

### Group Admin
- Create a new study group (requires Super Admin approval)
- Add members to your approved groups
- Create and organize courses
- Monitor group activity

### Regular User
- View courses in your study groups
- Create topics for specific courses
- Upload and access learning materials

## 📁 Project Structure

```
sanctuary/
├── core/                   # Main application
│   ├── models.py           # Database models
│   ├── views.py            # View functions
│   ├── decorators.py       # Role-based access decorators
│   ├── admin.py            # Admin interface configuration
│   └── templates/          # HTML templates
├── media/                  # Uploaded files storage
│   └── learning_files/     # Learning materials
├── sanctuary/              # Project configuration
└── manage.py               # Django management script
```

## 🔄 Workflow

1. Super Admin sets up the platform and approves study groups
2. Group Admins create courses and invite members
3. Users join groups and share learning materials
4. Everyone accesses organized content securely

## ⚙️ Configuration

- Media files are stored in the `media/` directory
- Default database is SQLite (can be changed in settings.py)
- File upload size limitations can be configured in settings.py

## 🙏 Acknowledgments

- Django framework
- Bootstrap for responsive UI
- All contributors to the project
