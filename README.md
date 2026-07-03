# AI-Based Smart Study Buddy

## Overview
The **AI-Based Smart Study Buddy** is a web application built using Python and Streamlit, powered by the free Google Gemini API. It acts as a specialized virtual tutor to help students with academic subjects.

## Features
- **Concept Explanation & Doubt Solving:** Chat interface to ask questions. Remembers conversation history context.
- **Quiz Generator:** Generate MCQs and viva questions based on topics and difficulty.
- **Study Planner:** Generate daily and weekly study schedules.
- **Exam Preparation:** Provide concise revision notes and important questions based on the exam syllabus.

## Architecture and Data Flow
1. **Interactive UI (Streamlit)**: Serves as the user interface to capture input. The sidebar handles high-level application variables like API Keys, Academic Subject to focus on, and desired mode/feature.
2. **Backend Logic & Data Formulation**: Once the user taps a button or sends a chat message, the system stitches together the user's query, their previous chat history (for concept solving), and a specialized **System Prompt**. 
3. **The System Prompt Constraint Engine**: The code explicitly tells the AI to behave as a professional tutor, providing structured academic answers and declining non-academic queries.
4. **AI Generation**: A configured API call invokes the `gemini-1.5-flash` model, locked to `Temperature: 0.5` and `Top-p: 0.9`. 
5. **Render to User Interface**: The retrieved response string from the Google Gemini API is rendered out clearly on the Streamlit dashboard using built-in Markdown elements.

---

## 🛠️ Setup & Run Instructions

Follow these steps to run the application on your computer:

### 1. Prerequisites
- **Python 3.9+** installed on your system.
- A free **Google Gemini API Key**. You can grab one by visiting [Google AI Studio here](https://aistudio.google.com/app/apikey).

### 2. Open Terminal / Command Prompt
Navigate to the directory where you have saved the project files (`app.py` and `requirements.txt`).


### 3. Create a Virtual Environment (Optional but Recommended)
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
Install the required packages (`streamlit` and `google-generativeai`):
```bash
pip install -r requirements.txt
```

### 5. Run the Application
Start the Streamlit development server:
```bash
streamlit run app.py
```

### 6. Use the App
A local server will start, opening your browser at `http://localhost:8501`. 
Enter your **Gemini API Key** into the sidebar's box. You are ready to start studying!
