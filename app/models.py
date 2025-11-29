from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# User model
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# Department model
class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    overview = db.Column(db.Text)

    doctors = db.relationship("Doctor", back_populates="department", cascade="all,delete-orphan")

# Doctor model
class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    First_name = db.Column(db.Text, nullable=False)
    Middle_name = db.Column(db.Text)
    Last_name = db.Column(db.Text)

    user_id = db.Column(db.Text, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = db.relationship("User", backref=db.backref("doctor", uselist=False, cascade="all,delete"))

    Mobile = db.Column(db.Integer, nullable=False)
    specialization = db.Column(db.String(120))
    Spec_date = db.Column(db.Date)
    bio = db.Column(db.Text)

    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="CASCADE"))
    department = db.relationship("Department", back_populates="doctors")

    availabilities = db.relationship("DoctorAvailability", back_populates="doctor", cascade="all,delete-orphan")
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all,delete-orphan")

# Patient model
class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    user_id = db.Column(db.Text, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    First_name = db.Column(db.Text, nullable=False)
    Middle_name = db.Column(db.Text)
    Last_name = db.Column(db.Text)

    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.Text, nullable=False)
    Mobile = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text)

    user = db.relationship("User", backref=db.backref("patient", uselist=False, cascade="all,delete"))

    appointments = db.relationship("Appointment", back_populates="patient", cascade="all,delete-orphan")

# Doctor availability
class DoctorAvailability(db.Model):
    __tablename__ = "doctor_availabilities"
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    doctor = db.relationship("Doctor", back_populates="availabilities")

    date = db.Column(db.Date, nullable=False)
    slot_start = db.Column(db.Integer, nullable=False)
    slot_end = db.Column(db.Integer, nullable=False)

    status = db.Column(db.Text, default='closed', nullable=False)
    booking_count = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("doctor_id", "date", "slot_start", name="uq_doctor_slot"),
        CheckConstraint("slot_end > slot_start", name="ck_slot_time_order"),
    )

# Appointment model
class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    reference_no = db.Column(db.String(32), unique=True, nullable=False)

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))

    slot_id = db.Column(db.Integer, nullable=False, unique=True)

    status = db.Column(db.String(20), default="booked", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    slot = db.relationship("DoctorAvailability")
    department = db.relationship("Department")

    visit = db.relationship("PatientVisit", back_populates="appointment", uselist=False, cascade="all,delete-orphan")

# Patient visit
class PatientVisit(db.Model):
    __tablename__ = "patient_visits"
    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    appointment = db.relationship("Appointment", back_populates="visit")

    visit_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    visit_type = db.Column(db.String(50))
    tests_done = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)

# Queue
class Que(db.Model):
    __tablename__ = 'que'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.Text)
    specialty = db.Column(db.Text)
    specialisation = db.Column(db.Text)
    mbbs_date = db.Column(db.Date)
    spec_date = db.Column(db.Date)
    bio = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
