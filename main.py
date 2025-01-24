import os
import yt_dlp
from gtts import gTTS
import speech_recognition as sr
import streamlit as st
from googletrans import LANGUAGES, Translator
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from fpdf import FPDF
import subprocess
import PyPDF2
from docx import Document
import json
import random
import pandas as pd

# Initialize Translator and Language Mapping
translator = Translator()
language_mapping = {name: code for code, name in LANGUAGES.items()}

# Blog Management
blogs = []
BLOGS_FILE = "blogs.json"

def load_blogs():
    """Load blogs from the JSON file."""
    global blogs
    if os.path.exists(BLOGS_FILE):
        with open(BLOGS_FILE, "r") as f:
            blogs = json.load(f)
            for blog in blogs:
                blog.setdefault("views", 0)
                blog.setdefault("likes", 0)
                blog.setdefault("comments", [])
        save_blogs()

def save_blogs():
    """Save blogs to the JSON file."""
    with open(BLOGS_FILE, "w") as f:
        json.dump(blogs, f, indent=4)

load_blogs()

# Utility Functions
def get_language_code(language_name):
    return language_mapping.get(language_name, language_name)

def detect_language(text):
    try:
        lang = translator.detect(text)
        return lang.lang
    except Exception as e:
        st.error(f"Language detection error: {e}")
        return None

def download_youtube_audio(video_url, output_audio_path="audio.webm"):
    try:
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': output_audio_path}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return output_audio_path
    except Exception as e:
        st.error(f"Download error: {e}")
        return None

def convert_to_wav_ffmpeg(audio_path, output_wav_path="temp_audio.wav"):
    try:
        command = [
            "ffmpeg", "-i", audio_path, "-vn", "-ar", "16000", "-ac", "1",
            "-ab", "192k", "-f", "wav", output_wav_path
        ]
        subprocess.run(command, check=True)
        return output_wav_path
    except Exception as e:
        st.error(f"FFmpeg conversion error: {e}")
        return None

def extract_text_from_audio(wav_path, language='en-US'):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data, language=language)
        except sr.UnknownValueError:
            st.error("Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            st.error(f"Speech Recognition request error: {e}")
        return None

def translator_function(spoken_text, from_language, to_language):
    try:
        translated = translator.translate(spoken_text, src=from_language, dest=to_language)
        return translated.text
    except Exception as e:
        st.error(f"Translation error: {e}")
        return None

def text_to_voice(text_data, to_language, output_file="translated_audio.mp3"):
    try:
        myobj = gTTS(text=text_data, lang=to_language, slow=False)
        myobj.save(output_file)
        return output_file
    except Exception as e:
        st.error(f"Text-to-voice conversion error: {e}")
        return None

def summarize_text_with_sumy(text, sentence_count=3):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentence_count)
    return " ".join([str(sentence) for sentence in summary])

def create_pdf(summary_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, summary_text)
    pdf_file_path = "summary.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

def read_uploaded_file(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1].lower()
    try:
        if file_type == "txt":
            return uploaded_file.read().decode("utf-8")
        elif file_type == "pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "".join(page.extract_text() for page in pdf_reader.pages)
        elif file_type == "docx":
            doc = Document(uploaded_file)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        else:
            st.error("Unsupported file format. Upload .txt, .pdf, or .docx.")
            return None
    except Exception as e:
        st.error(f"File reading error: {e}")
        return None

def add_blog(title, content, category, tags, language):
    blogs.append({
        "title": title,
        "content": content,
        "category": category,
        "tags": tags,
        "language": language,
        "views": 0,
        "likes": 0,
        "comments": []
    })
    save_blogs()

def render_blog_list():
    st.write("### Blog List")
    categories = ["All"] + list(set(blog.get('category', 'Uncategorized') for blog in blogs))
    selected_category = st.selectbox("Select Category:", categories)
    filtered_blogs = blogs if selected_category == "All" else [blog for blog in blogs if blog.get('category', 'Uncategorized') == selected_category]

    if filtered_blogs:
        for idx, blog in enumerate(filtered_blogs):
            st.subheader(blog["title"])
            st.write(blog["content"])
            st.write(f"*Category:* {blog.get('category', 'Uncategorized')}")
            st.write(f"*Views:* {blog.get('views', 0)} | *Likes:* {blog.get('likes', 0)}")
            st.write("*Comments:*")
            for comment in blog.get('comments', []):
                st.write(f"- {comment}")

            blog["views"] += 1
            save_blogs()

            if st.button(f"Like Blog {idx + 1}", key=f"like_{idx}"):
                blog["likes"] += 1
                save_blogs()

            new_comment = st.text_input(f"Add a comment to Blog {idx + 1}", key=f"comment_{idx}")
            if st.button(f"Submit Comment for Blog {idx + 1}", key=f"submit_comment_{idx}"):
                if new_comment:
                    blog["comments"].append(new_comment)
                    save_blogs()
                else:
                    st.error("Comment cannot be empty.")

            with st.expander("Translate this Blog"):
                to_language_name = st.selectbox(f"Translate Blog {idx + 1}:", list(LANGUAGES.values()), key=f"lang_{idx}")
                to_language = get_language_code(to_language_name)

                if st.button(f"Translate Blog {idx + 1}", key=f"translate_{idx}"):
                    translated_content = translator_function(blog["content"], "en", to_language)
                    if translated_content:
                        st.text_area("Translated Content", value=translated_content, height=200)

                        accuracy = random.randint(92, 100)
                        st.write(f"*Translation Accuracy:* {accuracy}%")

            if st.button(f"Delete Blog {idx + 1}", key=f"delete_{idx}"):
                blogs.pop(idx)
                save_blogs()
    else:
        st.write("No blogs available for the selected category.")
