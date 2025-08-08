# Sistema de Controle de Pacientes Neuropsicológicos

## Overview

This is a complete web-based patient management system designed specifically for neuropsychology practices. The system manages patient records, therapy sessions, insurance passwords/codes, and final reports through a role-based interface. It features two user types: administrators with full system access including dashboards and financial reporting, and medical professionals who can manage their assigned patients and sessions.

The application handles the complete patient journey from initial registration through up to 8 therapy sessions, insurance code management, and final report uploads. It includes automated alerts for approaching deadlines and comprehensive reporting capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.
- Requested patient login functionality using CPF (January 2025)
- Requested unique CPF validation to prevent duplicates (January 2025)
- Requested location field in patient registration: Belo Horizonte, Contagem, Divinópolis (January 2025)

## System Architecture

### Backend Framework
- **Flask Application**: Monolithic web application using Flask as the primary framework
- **SQLite Database**: Lightweight file-based database for data persistence without requiring external database servers
- **Session-based Authentication**: Server-side session management for user authentication and authorization
- **Role-based Access Control**: Two-tier system (admin/medico) with different permission levels

### Database Design
- **Core Tables**: medicos (doctors), pacientes (patients), sessoes (sessions), senhas (insurance codes), laudos (reports)
- **Relational Structure**: Foreign key relationships linking patients to doctors, sessions to patients, and insurance codes to patients
- **Direct SQLite**: Raw SQL queries using sqlite3 module for all database operations - user specifically requested NO SQLAlchemy
- **Unique Constraints**: CPF field in pacientes table has unique constraint to prevent duplicate registrations (Added January 2025)
- **Location Tracking**: Added localizacao field to track patient service location (Belo Horizonte, Contagem, Divinópolis) - Added January 2025

### Patient Portal (Added January 2025)
- **Patient Authentication**: CPF-based login system for patients to access their personal area
- **Document Access**: Secure download system allowing patients to access only their own laudos (reports)
- **Session Separation**: Separate session management for patients vs medical staff
- **Security**: Patients can only access their own data, with proper validation and access controls
- **Finalized Access**: Patients with "finalizado" status can still login to access their completed laudos (January 2025)

### Frontend Architecture
- **Template Engine**: Jinja2 for server-side rendering with template inheritance
- **CSS Framework**: Bootstrap 5 for responsive UI components and styling
- **JavaScript Libraries**: Chart.js for dashboard visualizations and analytics
- **Static Asset Management**: Organized into /static directory with separate CSS and JS files

### File Management
- **Upload System**: Secure file upload handling for PDF reports with filename sanitization
- **File Storage**: Local filesystem storage in /uploads directory for patient documents
- **File Validation**: Restricted to PDF files only with proper extension checking

### Security Implementation
- **Password Hashing**: Werkzeug's secure password hashing for user authentication
- **Session Security**: Flask's built-in session management with configurable secret keys
- **Input Validation**: Form validation and secure filename handling for file uploads
- **Access Control**: Route-level authorization checks based on user roles

### Business Logic
- **Session Limits**: Maximum 8 sessions per patient with progress tracking
- **Insurance Management**: Specialized handling for consultation and test codes with predefined values
- **Date Management**: Automatic calculation of treatment deadlines and progress alerts
- **Status Tracking**: Patient lifecycle management from active to completed status

## External Dependencies

### Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive design and UI components
- **Font Awesome**: Icon library for consistent visual elements
- **Chart.js**: JavaScript charting library for dashboard analytics and reporting

### Python Packages
- **Flask**: Web framework for application routing and request handling
- **Werkzeug**: Security utilities for password hashing and file handling
- **sqlite3**: Built-in Python module for database operations

### Development Environment
- **Python Runtime**: Python 3.x environment for application execution
- **File System**: Local storage for SQLite database and uploaded documents
- **Environment Variables**: Configuration management for session secrets and deployment settings

### Infrastructure Requirements
- **Static File Serving**: Flask's built-in static file serving for CSS, JavaScript, and uploaded documents
- **Template Processing**: Jinja2 template engine integrated with Flask
- **Session Storage**: Server-side session management using Flask's session handling