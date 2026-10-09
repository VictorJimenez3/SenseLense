"""Add one labelled, synthetic walkthrough without changing existing records."""
from datetime import datetime, timedelta
from app import app
from models import db, Client, Session, Event

DEMO_EMAIL = 'alex@northstar.example'
DEMO_TITLE = '[Demo] Northstar payroll discovery'


def seed_data():
    with app.app_context():
        client = Client.query.filter_by(email=DEMO_EMAIL).first()
        if client is None:
            client = Client(name='Alex Morgan [Demo]', company='Northstar Bikes [Demo]',
                            email=DEMO_EMAIL, notes='Fictional prospect for a synthetic demonstration.')
            db.session.add(client)
            db.session.flush()
        if Session.query.filter_by(client_id=client.id, title=DEMO_TITLE).first():
            print('Synthetic demo already available; existing records preserved.')
            return
        start = datetime.utcnow() - timedelta(minutes=6)
        session = Session(
            client_id=client.id, title=DEMO_TITLE, started_at=start,
            ended_at=start + timedelta(minutes=5), overall_sentiment=0.25,
            engagement_score=72,
            summary=('**Synthetic demonstration data — not real customer audio or model outputs.**\n\n'
                     '**Conversation**\nNorthstar Bikes wants to reduce manual payroll work for 45 employees. '
                     'The prospect raised migration cost and scheduling concerns, then agreed to a limited pilot.\n\n'
                     '**Key moments**\n- 01:15: Concern about migration cost.\n'
                     '- 02:30: Seller proposes a staged rollout.\n- 04:15: Prospect agrees to evaluate a pilot.\n\n'
                     '**Next steps**\n- Send a pricing breakdown.\n- Schedule a pilot with the payroll manager.\n\n'
                     'Facial signals are illustrative estimates; they do not establish a person’s intentions.')
        )
        db.session.add(session)
        db.session.flush()
        dialogue = [
            (5000, 'seller', 'Thanks for joining. What is taking the most time in your payroll process?'),
            (30000, 'client', 'We have 45 employees. Our manager spends every Friday correcting spreadsheet entries.'),
            (60000, 'seller', 'A payroll integration could remove that duplicate entry and provide an audit trail.'),
            (75000, 'client', 'I am concerned about migration cost. We cannot interrupt payroll during our busy season.'),
            (120000, 'seller', 'That makes sense. We can test with a small group while your existing system stays in place.'),
            (150000, 'client', 'A staged rollout sounds better. Can our payroll manager review the export first?'),
            (195000, 'seller', 'Yes. I will send the pricing breakdown and arrange a pilot with your manager.'),
            (255000, 'client', 'Great. If the export checks out, we can start the pilot next month.'),
            (280000, 'seller', 'I will follow up tomorrow with those details. Thanks for your time.'),
        ]
        # Keep the existing event-source schema so the real timeline and insights run unchanged.
        for timestamp, speaker, text in dialogue:
            db.session.add(Event(session_id=session.id, timestamp_ms=timestamp,
                                 source='elevenlabs', speaker=speaker, text=text))
        for timestamp in range(0, 300000, 10000):
            emotion, valence = ('neutral', 0.0)
            if 70000 <= timestamp < 120000:
                emotion, valence = 'negative', -0.5
            elif 150000 <= timestamp < 240000:
                emotion, valence = 'engaged', 0.3
            elif timestamp >= 240000:
                emotion, valence = 'happy', 0.9
            db.session.add(Event(session_id=session.id, timestamp_ms=timestamp,
                                 source='deepface', emotion=emotion, valence=valence))
        db.session.commit()
        print(f'Synthetic demo session #{session.id} added; existing records preserved.')


if __name__ == '__main__':
    seed_data()
