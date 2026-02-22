from app import app
from models import db, Client, Session, Event

with app.app_context():
    print(f'Clients: {Client.query.count()}')
    print(f'Sessions: {Session.query.count()}')
    print(f'Events: {Event.query.count()}')
