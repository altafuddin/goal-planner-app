
# 🎯 Goal Planner App

A smart, goal-oriented task planning application powered by AI (Gemini) where users can chat with an assistant to create personalized learning plans and sync them with Google Calendar.

---

## 🚀 Features

- 💬 Chat with AI to discuss learning goals
- 📅 Generate structured daily plans (e.g., "Learn Python in 7 days")
- 🔁 Integrate plans directly into Google Calendar
- 🧠 AI-guided experience: from goal setting to scheduling
- ⚙️ Built with FastAPI + Next.js (TypeScript)

---

## 📁 Project Structure

```
goal-planner-app/
├── backend/             # FastAPI + Gemini + Calendar integration
├── frontend/            # Next.js (React 18 + TypeScript)
├── README.md
└── .gitignore
```

---

## 🛠️ Getting Started (Local Development)

### 1. Clone the Repo

```bash
git clone https://github.com/altafuddin/goal-planner-app.git
cd goal-planner-app
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env      # Add your Google Gemini API key
uvicorn main_api:app --reload
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install

cp .env.local.example .env.local  # Set backend URL
npm run dev
```

Open your browser at: `http://localhost:3000`

---

## 🔐 Environment Variables

### `backend/.env`

```env
GOOGLE_API_KEY=your_google_api_key
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🧠 How It Works

1. User chats naturally with AI in the app (e.g. "I want to learn FastAPI in 3 days").
2. AI gathers any missing details (duration, time of day, hours/day).
3. When ready, AI proposes plan generation (`/generate-plan` is called).
4. Plan is shown; user can regenerate or ask to integrate it.
5. Integration with Google Calendar is one click away.

---

## 🧪 Technologies Used

- **Frontend**: Next.js 15, React 18, TypeScript, Vercel v0
- **Backend**: FastAPI, Gemini API, Google Calendar API
- **Auth**: Google OAuth (for calendar)
- **State**: AI-driven memory (in-memory plan/session tracking)

---

## 📦 Future Plans

- Add user authentication
- Store multiple goals per user
- Add progress tracking and reminders
- Enhance feedback system for learning

---

## 👤 Author

Made by [@altafuddin](https://github.com/altafuddin)  
Powered by curiosity and coffee ☕

---

## 📄 License

MIT — Free to use, fork, or improve.
