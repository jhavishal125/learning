
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
import uuid

# Initialize the Flask app and configure SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ats_user:password@localhost/enterprise_ats'
db = SQLAlchemy(app)

# User model (Admin, Recruiter, Hiring Manager)
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.String(50), nullable=False)  # Roles: Admin, Recruiter, Hiring Manager
    password_hash = db.Column(db.String(128))

# Job model
class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Open')  # Status: Open, Closed
    created_by = db.Column(db.String(36), db.ForeignKey('user.id'))  # Job created by admin/recruiter

# Candidate model
class Candidate(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    position_applied = db.Column(db.String(100), db.ForeignKey('job.id'))
    resume = db.Column(db.String(200))  # Path to resume stored in S3
    status = db.Column(db.String(50), default='Applied')  # Status: Applied, Screening, Interview, Offer, Hired, Rejected
    interview_score = db.Column(db.Integer, default=0)
    notes = db.Column(JSON)  # To store internal comments and feedback

# API to add a new job
@app.route('/jobs', methods=['POST'])
def create_job():
    data = request.json
    job = Job(
        title=data['title'],
        department=data['department'],
        location=data.get('location'),
        description=data['description'],
        created_by=data['created_by']
    )
    db.session.add(job)
    db.session.commit()
    return jsonify({"message": "Job created successfully"}), 201

# API to add a candidate
@app.route('/candidates', methods=['POST'])
def add_candidate():
    data = request.json
    candidate = Candidate(
        name=data['name'],
        email=data['email'],
        phone=data['phone'],
        position_applied=data['position_applied'],
        resume=data['resume']  # Assume resume is uploaded and path stored in S3
    )
    db.session.add(candidate)
    db.session.commit()
    return jsonify({"message": "Candidate added successfully"}), 201

# API to update candidate status
@app.route('/candidates/<candidate_id>/status', methods=['PUT'])
def update_candidate_status(candidate_id):
    data = request.json
    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        return jsonify({"message": "Candidate not found"}), 404
    candidate.status = data['status']
    db.session.commit()
    return jsonify({"message": f"Candidate status updated to {data['status']}"}), 200

# API to search candidates (by name, status, or job)
@app.route('/candidates/search', methods=['GET'])
def search_candidates():
    query = request.args.get('query')
    candidates = Candidate.query.filter(
        (Candidate.name.ilike(f"%{query}%")) | (Candidate.status.ilike(f"%{query}%"))
    ).all()
    return jsonify([{"name": candidate.name, "email": candidate.email, "status": candidate.status} for candidate in candidates])

# API to get all jobs
@app.route('/jobs', methods=['GET'])
def get_jobs():
    jobs = Job.query.all()
    return jsonify([{"title": job.title, "department": job.department, "status": job.status} for job in jobs])

# API to generate reports (example for time-to-hire)
@app.route('/reports/time_to_hire', methods=['GET'])
def time_to_hire_report():
    # Assume each candidate has a date_applied and date_hired field (not shown in this example)
    time_to_hire_data = db.session.query(
        Candidate.position_applied, 
        db.func.avg(Candidate.date_hired - Candidate.date_applied).label('average_time_to_hire')
    ).group_by(Candidate.position_applied).all()
    
    return jsonify([{"position": data.position_applied, "avg_time_to_hire": str(data.average_time_to_hire)} for data in time_to_hire_data])

if __name__ == '__main__':
    app.run(debug=True)
