# 🚀 Find me a job AI

An intelligent job search assistant that analyzes your CV, suggests career paths, and generates AI-powered cover letters.

## 🛠️ Setup

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   - `GROQ_API_KEY`
   - `FRANCE_TRAVAIL_CLIENT_ID` (Optional)
   - `FRANCE_TRAVAIL_CLIENT_SECRET` (Optional)

## 🌍 Deployment (Streamlit Cloud)

1. Initialize and push this code to a **GitHub** repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin git@github.com:YaYouLeKyou/FindMyJobAI.git
   git pull origin main --allow-unrelated-histories
   git push -u origin main
   ```
2. Go to share.streamlit.io.
3. Connect your GitHub account and select this repository.
4. **Important**: Go to "Settings" -> "Secrets" and paste the content of your `.env` file there.

## 📄 License
MIT