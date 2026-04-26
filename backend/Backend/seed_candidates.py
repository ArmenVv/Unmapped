import chromadb
import random
import json


client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("candidates")

names = [
    ("Armen", "Vardanyan", "Yerevan"),
    ("Ani", "Hakobyan", "Gyumri"),
    ("David", "Petrosyan", "Yerevan"),
    ("Mariam", "Grigoryan", "Vanadzor"),
    ("Narek", "Sargsyan", "Yerevan"),
    ("Sona", "Melikyan", "Dilijan"),
    ("Gor", "Avagyan", "Yerevan"),
    ("Lilit", "Martirosyan", "Gyumri"),
    ("Alex", "Johnson", "London"),
    ("Emma", "Brown", "Los Angeles"),
]

jobs = [
    ("Frontend Developer", "React, JavaScript, CSS, Vite, responsive UI",
     "Builds clean interfaces, connects APIs, fixes UI bugs quickly, understands component-based design and frontend performance."),

    ("Backend Developer", "Python, FastAPI, REST APIs, SQL, ChromaDB",
     "Creates backend services, database logic, API endpoints, authentication flows, and reliable data handling for web applications."),

    ("UI/UX Designer", "Figma, wireframes, prototyping, user research",
     "Designs modern user flows, landing pages, dashboards, and mobile-friendly layouts with strong attention to usability."),

    ("Bakery Chef", "Pastry, bread, cakes, kitchen safety, recipe planning",
     "Experienced in preparing cakes, croissants, breads, and desserts. Can manage daily bakery workflow and maintain consistent quality."),

    ("Video Editor", "Premiere Pro, DaVinci Resolve, color grading, storytelling",
     "Edits cinematic videos, social media reels, interviews, and short films with good pacing, sound cleanup, and visual style."),

    ("Fitness Trainer", "Strength training, hypertrophy, nutrition basics",
     "Creates workout plans, teaches technique, tracks client progress, and helps beginners build confidence in the gym."),

    ("Marketing Specialist", "Social media, ads, copywriting, campaign planning",
     "Plans campaigns, writes strong posts, understands audience targeting, and improves brand visibility through creative content."),

    ("Barista", "Coffee brewing, latte art, customer service, POS",
     "Prepares espresso drinks, handles rush hours, communicates well with customers, and keeps the workspace clean."),

    ("Photographer", "Portraits, events, Lightroom, composition",
     "Shoots portraits, product photos, and events. Strong eye for lighting, editing, and natural-looking visual storytelling."),

    ("HR Assistant", "Recruiting, screening, interviews, documentation",
     "Helps with candidate screening, interview scheduling, communication, and organizing hiring documents.")
]

soft_skills = [
    "Reliable, calm under pressure, and communicates clearly with team members.",
    "Creative, detail-oriented, and able to solve problems independently.",
    "Fast learner with strong discipline and good time management.",
    "Friendly, client-focused, and comfortable speaking with different people.",
    "Organized, responsible, and good at following structured processes.",
]

try:
    client.delete_collection("candidates")
except Exception:
    # If the collection doesn't exist yet, ignore the error
    pass

collection = client.get_or_create_collection("candidates")

for i in range(100):
    base = names[i % len(names)]
    job = jobs[i % len(jobs)]

    name, surname, city = base
    profession, skills, description = job
    age = random.randint(18, 45)
    score = random.randint(55, 99)
    soft = random.choice(soft_skills)

    data = {
        "candidate": {
            "name": f"{name}{i}" if i >= 10 else name,
            "surname": surname,
            "age": age,
            "city": city
        },
        "analysis": {
            "profession": profession,
            "suitability_score": score,
            "description": description,
            "soft_skill": soft,
            "skills": skills
        }
    }

    searchable_text = f"""
    Candidate: {data["candidate"]["name"]} {surname}
    City: {city}
    Age: {age}
    Profession: {profession}
    Skills: {skills}
    Description: {description}
    Soft skills: {soft}
    Suitability score: {score}
    """

    collection.add(
        ids=[f"candidate_{i + 1}"],
        documents=[searchable_text],
        metadatas=[{
            "name": data["candidate"]["name"],
            "surname": surname,
            "age": age,
            "city": city,
            "profession": profession,
            "rating": score,
            "email": f"{data['candidate']['name'].lower()}@example.com",
            "phone": f"+37499{100000 + i}",
            "data": json.dumps(data, ensure_ascii=False)
        }]
    )

print("100 candidates added to ChromaDB.")