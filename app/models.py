# app/models.py
from datetime import datetime, date, time
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# ---------- Core auth/user ----------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))                            # keep as string (can include +, 0s)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)             # 'admin' | 'doctor' | 'patient'

    # convenience helpers (hash/verify implemented in auth code)
    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} ({self.role})>"


# ---------- Domain entities ----------

class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    overview = db.Column(db.Text)

    doctors = db.relationship("Doctor", back_populates="department", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Department {self.id} {self.name}>"


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    First_name = db.Column(db.Text, nullable=False)
    Middle_name = db.Column(db.Text)
    Last_name = db.Column(db.Text)
    # profile/user
    user_id = db.Column(db.Text, db.ForeignKey("users.email", ondelete="CASCADE"), nullable=False, unique=True)
    user = db.relationship("User", backref=db.backref("doctor", uselist=False, cascade="all,delete"))
    
    Mobile = db.Column(db.Integer, nullable=False)
    # professional info
    specialization = db.Column(db.String(120))
    Spec_date = db.Column(db.Date)
    bio = db.Column(db.Text)

    # department link
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id",ondelete="CASCADE"), nullable=True)
    department = db.relationship("Department", back_populates="doctors")

    # relationships
    availabilities = db.relationship("DoctorAvailability", back_populates="doctor", cascade="all,delete-orphan")
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Doctor {self.id} user={self.user_id}>"


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    user = db.relationship("User", backref=db.backref("patient", uselist=False, cascade="all,delete"))

    dob = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.String(200))

    appointments = db.relationship("Appointment", back_populates="patient", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Patient {self.id} user={self.user_id}>"


class DoctorAvailability(db.Model):
    """
    Discrete 1:1 bookable slots for a doctor.
    Unique per (doctor_id, date, slot_start) to avoid duplicates.
    """
    __tablename__ = "doctor_availabilities"
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    doctor = db.relationship("Doctor", back_populates="availabilities")

    date = db.Column(db.Date, nullable=False)
    slot_start = db.Column(db.Time, nullable=False)
    slot_end = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("doctor_id", "date", "slot_start", name="uq_doctor_slot"),
        CheckConstraint("slot_end > slot_start", name="ck_slot_time_order"),
    )

    def __repr__(self) -> str:
        return f"<Avail d={self.doctor_id} {self.date} {self.slot_start}-{self.slot_end}>"


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    reference_no = db.Column(db.String(32), unique=True, nullable=False)

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)

    # tie appointment to a specific availability slot
    slot_id = db.Column(db.Integer, db.ForeignKey("doctor_availabilities.id", ondelete="RESTRICT"), nullable=False, unique=True)

    status = db.Column(db.String(20), default="booked", nullable=False)  # 'booked' | 'cancelled' | 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    slot = db.relationship("DoctorAvailability")
    department = db.relationship("Department")

    # optional: one-to-one visit record (created upon completion)
    visit = db.relationship("PatientVisit", back_populates="appointment", uselist=False, cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Appt {self.id} ref={self.reference_no} d={self.doctor_id} p={self.patient_id}>"


class PatientVisit(db.Model):
    """
    Clinical record linked 1:1 with an appointment (created when doctor completes visit).
    If you want multiple notes per appointment, switch to one-to-many with its own PK and drop the unique constraint.
    """
    __tablename__ = "patient_visits"
    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True)
    appointment = db.relationship("Appointment", back_populates="visit")

    visit_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    visit_type = db.Column(db.String(50))      # e.g., 'in-person', 'tele-consult'
    tests_done = db.Column(db.Text)            # JSON string or CSV; normalize later if needed
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)

    def __repr__(self) -> str:
        return f"<Visit appt={self.appointment_id} {self.visit_date:%Y-%m-%d}>"
class Que(db.Model):
    __tablename__ = 'que'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # store hashed passwords
    phone = db.Column(db.String(15))
    specialty = db.Column(db.String(120))
    specialisation = db.Column(db.String(150))
    mbbs_date = db.Column(db.Date)
    spec_date = db.Column(db.Date)
    bio = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Que id={self.id} name={self.first_name} {self.surname} email={self.email} status={self.status}>"
