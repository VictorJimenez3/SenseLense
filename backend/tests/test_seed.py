from seed import seed_data
from app import app
from models import db, Client, Session


def test_seed_preserves_records_and_is_repeatable(client):
    real = client.post('/api/clients', json={'name': 'Keep me'}).get_json()
    seed_data()
    with app.app_context():
        assert db.session.get(Client, real['id']).name == 'Keep me'
        samples = Session.query.filter(Session.title.like('[Demo]%')).all()
        assert samples
        sample = samples[0]
        assert 'synthetic' in sample.summary.lower()
        assert sample.events
        assert max(e.timestamp_ms for e in sample.events) <= (sample.ended_at - sample.started_at).total_seconds() * 1000
        counts = (Client.query.count(), Session.query.count())
    seed_data()
    with app.app_context():
        assert (Client.query.count(), Session.query.count()) == counts
