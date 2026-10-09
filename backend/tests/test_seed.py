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


def test_demo_library_restores_missing_session_without_overwriting_edits(client):
    seed_data()
    with app.app_context():
        samples = Session.query.filter(Session.title.like('[Demo]%')).all()
        assert len(samples) == 4
        new_samples = [s for s in samples if s.title != '[Demo] Northstar payroll discovery']
        for sample in new_samples:
            assert 'not real customer audio or model outputs' in sample.summary.lower()
            assert len([e for e in sample.events if e.source == 'deepgram']) >= 12
            assert len([e for e in sample.events if e.source == 'faceapi']) >= 30
            assert {e.speaker for e in sample.events if e.source == 'deepgram'} == {'seller', 'client'}
            assert all(e.timestamp_ms <= (sample.ended_at - sample.started_at).total_seconds() * 1000 for e in sample.events)
        preserved = samples[0]
        preserved.summary = 'My interview notes'
        deleted_title = new_samples[-1].title
        db.session.delete(new_samples[-1])
        db.session.commit()
        preserved_id = preserved.id
    seed_data()
    with app.app_context():
        assert Session.query.count() == 4
        assert Session.query.filter_by(title=deleted_title).one().events
        assert db.session.get(Session, preserved_id).summary == 'My interview notes'
