# Sports Media Asset Protection - SHIELD_MEDIA

A high-fidelity web application featuring a Neo-Brutalist "SHIELD_MEDIA" authentication portal and a FastAPI backend.

## Project Structure

- **/frontend**: Angular 19 application using a Neo-Brutalist design system (Space Grotesk typography, high-contrast accents, bold borders, and faint watermark decorations).
- **/backend**: FastAPI application with CORS support for secure frontend-backend communication.

## Tech Stack

- **Frontend**: Angular 19, TypeScript, Vanilla CSS (Neo-Brutalist UI/UX).
- **Backend**: Python 3.12+, FastAPI, Uvicorn.
- **Styling**: Neo-Brutalist design tokens (hard shadows, 2.5px borders, Space Grotesk font).

## Getting Started

### Prerequisites

- Node.js (v22.19.0 recommended)
- Python (3.12 or higher)
- Angular CLI (`npm install -g @angular/cli`)

### Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Sports-Media-Asset-Protection
   ```

2. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   ```

3. **Backend Setup:**
   ```bash
   cd ../backend
   # It is recommended to use a virtual environment
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   pip install fastapi uvicorn
   ```

### Running the Application

To run the full stack, you need to start both the backend and the frontend servers.

1. **Start FastAPI Backend:**
   ```bash
   cd backend
   uvicorn core.app:app --reload
   ```
   *The backend will be available at http://localhost:8000*

2. **Start Angular Frontend:**
   ```bash
   cd frontend
   npm start
   ```
   *The frontend will be available at http://localhost:4200*

## UI/UX Features

- **Neo-Brutalist Aesthetic**: High-contrast colors, bold black borders, and hard drop shadows.
- **Dynamic Auth Tabs**: Interactive "Sign In" and "Create Account" toggle with reactive state.
- **Decorative Watermarks**: Faint, professional background SVGs (Bow & Arrow / Soccer Ball).
- **Mobile Responsive**: Fully optimized for various screen sizes, from mobile to desktop.
