import random
from datetime import datetime, timedelta
from app import app
from models import db, Client, Session, Event

def seed_data():
    with app.app_context():
        # Clear existing
        print("Cleaning database...")
        Event.query.delete()
        Session.query.delete()
        Client.query.delete()
        db.session.commit()

        # 1. Create Clients
        print("Seeding clients...")
        clients = [
            Client(name="Sarah Jenkins", company="TechFlow Solutions", email="sarah.j@techflow.io", notes="Highly interested in ADP integration."),
            Client(name="Michael Chen", company="Zenith Logistics", email="m.chen@zenith.com", notes="Current payroll provider is too expensive."),
            Client(name="David Rodriguez", company="Rodriguez & Co", email="david@rodriguez-co.com", notes="Small business owner, needs simple UI."),
            Client(name="Elena Petrova", company="Global Insights Group", email="elena@globalinsights.org", notes="International team, complex compliance needs.")
        ]
        db.session.add_all(clients)
        db.session.commit()

        # 2. Create Sessions
        print("Seeding sessions...")
        sessions = []
        meeting_topics = [
            "ADP Workforce Now Demo",
            "Payroll Migration Roadmap",
            "Benefits Administration Setup",
            "Annual Compliance Review",
            "Initial Discovery Call"
        ]

        now = datetime.utcnow()
        for i, client in enumerate(clients):
            for j in range(random.randint(2, 4)):
                start_time = now - timedelta(days=random.randint(1, 10), hours=random.randint(1, 23))
                duration_mins = random.randint(15, 45)
                end_time = start_time + timedelta(minutes=duration_mins)
                
                sentiment = random.uniform(-0.4, 0.8)
                engagement = random.uniform(40, 95)
                
                session = Session(
                    client_id=client.id,
                    title=f"{random.choice(meeting_topics)} - {client.company}",
                    started_at=start_time,
                    ended_at=end_time,
                    summary="This conversation covered the main pain points of the current system. The client was particularly impressed with the real-time reporting capabilities and the seamless integration with existing HR tools.",
                    overall_sentiment=sentiment,
                    engagement_score=engagement
                )
                sessions.append(session)
        
        db.session.add_all(sessions)
        db.session.commit()

        # 3. Create Events (Timeline)
        print("Seeding events...")
        emotions = ["happy", "neutral", "engaged", "confused", "negative"]
        
        script_parts = [
            ("seller", "Hi, thanks for joining today. I'd love to show you how SenseLense integrates with your ADP workflow."),
            ("client", "Yes, we've been looking for something that can help us track client engagement during these long demo calls."),
            ("seller", "Exactly. Our AI analysis picks up on subtle cues that might be missed otherwise."),
            ("client", "That sounds very promising. How does it handle multi-speaker environments?"),
            ("seller", "It uses advanced diarization from ElevenLabs to distinguish between you and the customer automatically."),
            ("client", "I see. And the emotion tracking? How accurate is that?"),
            ("seller", "We use DeepFace for high-precision facial analysis, mapped directly to valence and specific emotion categories."),
            ("client", "Interesting. Let's dive into the pricing and implementation timeline.")
        ]

        for session in sessions:
            # Add some emotion samples (Presage)
            current_ms = 0
            while current_ms < 300000: # 5 minutes of data
                emo = random.choice(emotions)
                valence = 0.5 if emo in ["happy", "engaged"] else (-0.5 if emo == "negative" else 0.0)
                valence += random.uniform(-0.2, 0.2)
                
                event = Event(
                    session_id=session.id,
                    timestamp_ms=current_ms,
                    source="presage",
                    emotion=emo,
                    valence=max(-1.0, min(1.0, valence))
                )
                db.session.add(event)
                current_ms += 2400 # 2.4s sample rate as per README
            
            # Add some transcript segments (ElevenLabs)
            current_ms = 5000
            for speaker, text in script_parts:
                event = Event(
                    session_id=session.id,
                    timestamp_ms=current_ms,
                    source="elevenlabs",
                    speaker=speaker,
                    text=text
                )
                db.session.add(event)
                current_ms += 10000 + random.randint(2000, 8000)

        db.session.commit()
        print("✅ Database seeding complete.")

if __name__ == "__main__":
    seed_data()
