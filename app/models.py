from app.app import db

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<Thread {self.phone}>'
