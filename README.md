# Origami AI Studio

A Streamlit web application that uses AI to generate images with user authentication and admin features.

## Features

- 🎨 AI-powered image generation using OpenAI
- 🔐 User authentication with Auth0
- 👤 User management and admin portal
- 💾 Image storage and management
- ✉️ Email verification system

## Setup

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd OrigamiAI
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables in Streamlit secrets:
   - OpenAI API key
   - Auth0 configuration
   - Image model settings

4. Run the application:
   ```bash
   streamlit run streamlit_app.py
   ```

## Usage

1. Visit the application URL
2. Sign up or log in with Auth0
3. Verify your email address
4. Start generating images with AI prompts
5. Access admin features by adding `?admin=true` to the URL (if authorized)

## Project Structure

- `streamlit_app.py` - Main application entry point
- `app/` - Core application modules
  - `landing.py` - Landing page and authentication
  - `app.py` - Main application interface
  - `admin.py` - Admin portal functionality
- `image_generation.py` - OpenAI image generation logic
- `db.py` - Database operations
- `static/` - Static assets (icons, fonts)