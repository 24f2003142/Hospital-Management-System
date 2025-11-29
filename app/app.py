from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import *
from sqlalchemy import inspect
from models import *
import sqlite3
from flask import request, redirect, url_for, flash
from flask import jsonify
import random


app = Flask(__name__)
login_manager = LoginManager()
app.config["SECRET_KEY"] = "Lifeline_admin"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dev.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



db.init_app(app)
def fetch_queue():
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    stat='pending'
    c.execute("SELECT first_name,middle_name,surname, email, FROM que where status= ?", (stat,))
    rows = c.fetchall()
    conn.close()


def authenticate(usernm, passwd):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT name, email, password,role FROM users WHERE email = ?", (usernm,))
    row = c.fetchone()
    conn.close()

    if not row:
        return render_template('login.html', message="⚠️ User not found.")
    
    name, email, stored_pass, role = row
    if passwd != stored_pass:
        return render_template('login.html', message="❌ Invalid password.")

    if role=="patient":    
        return redirect(url_for('patient',user_name=usernm))
    elif role=="doctor":
        return redirect(url_for('doctor',user_name=usernm))
    elif role=="admin":
        return redirect(url_for('admin'))


@app.route('/doctor/<user_name>')
def doctor(user_name):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT id,First_name, Middle_name,Last_name, user_id, department_id FROM doctors WHERE user_id=?" , (user_name,))
    Doctor = c.fetchone()
    name=Doctor[1]+" "+Doctor[2]+" "+Doctor[3]
    c.execute("SELECT a.id,a.reference_no, a.patient_id,p.First_Name, p.Middle_Name, p.Last_Name, a.doctor_id, a.slot_id, a.status FROM appointments a,patients p where a.patient_id=p.id and a.status='Booked'")
    queueappointments = c.fetchall()
    return render_template('doctor/Dashboard.html',name=name, allappointments=queueappointments, user_name=user_name)

def ensure_slot_exists(doctor_user, slot_date, slot_start):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    doctorid=(c.execute("SELECT id FROM doctors where user_id=?", (doctor_user,))).fetchone()[0]
    c.execute("""
        SELECT id FROM doctor_availabilities
        WHERE doctor_id=? AND date=? AND slot_start=?
    """, (doctorid, slot_date, slot_start))
    row = c.fetchone()
    if not row:
        c.execute("""
            INSERT INTO doctor_availabilities 
            (doctor_id, date, slot_start, slot_end, status, booking_count)
            VALUES (?, ?, ?, ?, 'closed', 0)
        """, (doctorid, slot_date, slot_start, slot_start+1))
        conn.commit()

@app.route('/doctor/slot/<user_name>')
def doctor_slot_filling(user_name):
    today = datetime.now().date()
    time = datetime.now().hour
    print(time)
    days = [today + timedelta(days=i) for i in range(7)]
    HOURS = [h for h in range(9, 21) if h not in (14, 18)]

    for d in days:
        ds = d.strftime("%Y-%m-%d")
        for h in HOURS:
            ensure_slot_exists(user_name, ds, h)
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("DELETE FROM doctor_availabilities WHERE date<?",(today,))
    c.execute("DELETE FROM doctor_availabilities WHERE date=? AND slot_start<=?",(today,time))
    conn.commit()
    doctorid=(c.execute("SELECT id FROM doctors where user_id=?", (user_name,))).fetchone()[0]
    date_strings = [d.strftime("%Y-%m-%d") for d in days]
    placeholders = ",".join("?" * len(date_strings))
    c.execute(f"""
        SELECT id, doctor_id, date, slot_start, status, booking_count
        FROM doctor_availabilities
        WHERE doctor_id=? AND date IN ({placeholders})
        ORDER BY date, slot_start
    """, (doctorid, *date_strings))
    rows = c.fetchall()
    conn.close()
    slots_by_date = {}
    for sid, doc, sdate, shour, status, bcount in rows:
        slots_by_date.setdefault(sdate, []).append({"id": sid, "hour": int(shour),"status": status, "bookings": int(bcount)})
    

    return render_template('doctor/slots.html',user_name=user_name,dates=days,slots_by_date=slots_by_date)


@app.route('/doctor/<user_name>/slots/toggle', methods=['POST'])
def doctor_toggle_slot(user_name):
    """Open or close a slot."""
    data = request.get_json()
    sid = data.get("slot_id")
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    doctorid=(c.execute("SELECT id FROM doctors where user_id=?", (user_name,))).fetchone()[0]
    c.execute("SELECT status, booking_count FROM doctor_availabilities WHERE id=? AND doctor_id=?", (sid, doctorid))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "slot not found"}), 404

    status, count = row
    if count >= 5:
        conn.close()
        return jsonify({"error": "slot full"}), 400

    new_status = "open" if status == "closed" else "closed"
    c.execute("UPDATE doctor_availabilities SET status=? WHERE id=?", (new_status, sid))
    conn.commit()
    conn.close()
    return jsonify({"slot_id": sid, "new_status": new_status})


@app.route('/doctor/<user_name>/slots/book', methods=['POST'])
def doctor_book_slot(user_name):
    """Simulate patient booking (for testing UI)."""
    data = request.get_json()
    sid = data.get("slot_id")
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    doctorid=(c.execute("SELECT id FROM doctors where user_id=?", (user_name,))).fetchone()[0]
    c.execute("SELECT status, booking_count FROM doctor_availabilities WHERE id=? AND doctor_id=?", (sid, doctorid))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "slot not found"}), 404

    status, count = row
    if status != "open":
        conn.close()
        return jsonify({"error": "slot closed"}), 400
    if count >= 5:
        conn.close()
        return jsonify({"error": "slot full"}), 400

    count += 1
    c.execute("UPDATE doctor_availabilities SET booking_count=? WHERE id=?", (count, sid))
    conn.commit()
    conn.close()
    return jsonify({"slot_id": sid, "bookings_count": count})

@app.route('/doctor/patient_visit/<user_name>', methods=['GET','POST'])
def patient_history(user_name):
    patient_id=request.form.get('patient_id')
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT * FROM patient_visits pv,patients p WHERE pv.patient_id=p.id and patient_id=?" , (patient_id,))
    patient_history_list = c.fetchall()
    c.execute("SELECT * FROM doctors d, departments dp WHERE d.department_id=dp.id and d.user_id=?" , (user_name,))
    doctor_info = c.fetchall()
    return render_template('doctor/patient_visit.html',doctor_info=doctor_info, patient_info=patient_history_list, user_name=user_name)

@app.route('/doctor/<user_name>/visit_update/<option>', methods=['GET','POST'])
def doctor_patient_visit_update(user_name, option):
    print("visit_update called, option =", option)

    if option == 'Edit':
        patient_id = request.form.get('patient_id')
        appointment_id = request.form.get('appointment_id')
        visit_type = request.form.get('input_visit_type')
        tests_done = request.form.get('input_tests_done')
        diagnosis = request.form.get('input_diagnosis')
        notes = request.form.get('notes')
        medicine_names = request.form.getlist('medicine_name[]')
        dosages = request.form.getlist('dosage[]')

        if not appointment_id or not patient_id:
            flash("Missing appointment or patient id", "warning")
            return redirect(url_for('doctor', user_name=user_name))

        meds = []
        for name, dose in zip(medicine_names, dosages):
            if name:
                n = name.strip()
                d = (dose or '').strip()
                if n:
                    meds.append(f"{n} {d}".strip())
        medicines_csv = ', '.join(meds)
        visit_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

       
        conn = sqlite3.connect('./instance/dev.db')
        conn.execute("PRAGMA foreign_keys = ON;")
        c = conn.cursor()

        c.execute("""
                INSERT INTO patient_visits
                    (appointment_id, patient_id, visit_date, visit_type, tests_done, diagnosis, notes, prescription)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (appointment_id, patient_id, visit_date, visit_type, tests_done, diagnosis, notes, medicines_csv))

        conn.commit()
        print("Saved patient visit for appointment:", appointment_id)
        
        
        conn.close()

        return redirect(url_for('doctor', user_name=user_name))

    elif option in ('Completed', 'Cancelled'):
        
        appointment_id = request.form.get('appointment_id')
        patient_id = request.form.get('patient_id')

        if not appointment_id or not patient_id:
            flash("Missing appointment or patient id", "warning")
            return redirect(url_for('doctor', user_name=user_name))

        new_status = "Completed" if option == 'Completed' else "Cancelled"

        try:
            conn = sqlite3.connect('./instance/dev.db')
            conn.execute("PRAGMA foreign_keys = ON;")
            c = conn.cursor()

            
            c.execute("UPDATE appointments SET status = ? WHERE patient_id = ?", (new_status, patient_id))
            

            
            if c.rowcount == 0:
                
                print("Warning: no appointment row updated (id/patient mismatch?)", appointment_id, patient_id)

            conn.commit()
            print(f"Marked appointment {appointment_id} as {new_status}")
            flash(f"Appointment marked {new_status}.", "success")
        except Exception as e:
            conn.rollback()
            print("Error updating appointment status:", e)
            flash("Failed to update appointment. Check server logs.", "danger")
        finally:
            conn.close()

        return redirect(url_for('doctor', user_name=user_name))

    else:
        flash("Invalid action", "warning")
        return redirect(url_for('doctor', user_name=user_name))

@app.route('/doctor/change_password//<user_name>', methods=['POST'])
def doctor_change_password(user_name):
    current = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    if new != confirm:
        flash("New password and confirm password do not match.", "warning")
        return redirect(url_for('doctor', user_name=user_name))

    try:
        conn = sqlite3.connect('./instance/dev.db')
        c = conn.cursor()

        
        c.execute("SELECT password FROM users WHERE email=?", (user_name,))
        row = c.fetchone()

        if not row:
            flash("Doctor not found.", "danger")
            conn.close()
            return redirect(url_for('doctor', user_name=user_name))

        stored = row[0]

        
        if stored != current:
            flash("Current password is incorrect.", "warning")
            conn.close()
            return redirect(url_for('doctor', user_name=user_name))

        
        c.execute("UPDATE users SET password=? WHERE email=?", (new, user_name))
        conn.commit()
        conn.close()

        flash("Password changed successfully.", "success")
        return redirect(url_for('doctor', user_name=user_name))

    except Exception as e:
        print("Password update error:", e)
        flash("Server error.", "danger")
        return redirect(url_for('doctor', user_name=user_name))


@app.route('/SignedIn/admin/Doctors')
def admin():
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT id,First_name, Middle_name,Last_name, user_id, department_id FROM doctors")
    allDoctors = c.fetchall()
    c.execute("SELECT id,first_name, middle_name,surname, email FROM que")
    queueDoctors = c.fetchall()
    all=(c.execute("SELECT d.id, d.First_name, d.Middle_name,d.Last_name, d.user_id, d.department_id,u.phone,d.specialization, d.Spec_date, d.bio FROM doctors d,users u WHERE u.email=d.user_id")).fetchall()
    conn.close()
    return render_template('SignedIn/admin.html', allDoctors=all, queueDoctors=queueDoctors)

@app.route('/SignedIn/admin/Departments')
def departments():
    message = request.args.get('message')
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT * FROM departments")
    allDepartments = c.fetchall()
    print(allDepartments)
    conn.close()
    return render_template('SignedIn/departments.html', allDepartments=allDepartments,message=message)

@app.route('/SignedIn/admin/patients')
def patients():
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT * FROM patients")
    allpatients = c.fetchall()
    print(allpatients)
    conn.close()
    return render_template('SignedIn/patients.html', allpatients=allpatients)


@app.route('/patient/<user_name>')
def patient(user_name):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()

    
    c.execute("SELECT id, First_name, Middle_name, Last_name, user_id, dob, gender, Mobile, address FROM patients WHERE user_id = ?", (user_name,))
    patient_info = c.fetchone()

    
    if not patient_info:
        conn.close()
        flash("Patient record not found.", "warning")
        return redirect(url_for('login'))  

    pid, fname, mname, lname, temp_userid, dob, gender, mobile, address = patient_info

    
    name_components = [x for x in (fname, mname, lname) if x and str(x).strip()]
    Name = " ".join(name_components)

 
    c.execute("SELECT id, name FROM departments")
    alldepartments = c.fetchall()

    
    c.execute("""
                SELECT a.id, a.reference_no, a.patient_id, a.doctor_id,
                d.First_name, d.Middle_name, d.Last_name, d.department_id,
                dep.name, pv.date, pv.slot_start, pv.slot_end, a.slot_id
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                JOIN departments dep ON d.department_id = dep.id
                JOIN doctor_availabilities pv ON a.slot_id = pv.id
                WHERE a.patient_id = ? AND a.status = 'Booked'""", (pid,))
    allappointments = c.fetchall()

   
    c.execute("SELECT phone FROM users WHERE email = ?", (user_name,))
    user_row = c.fetchone()
    phone = user_row[0] if user_row and user_row[0] else mobile  

    conn.close()

    
    patient_dob = dob if dob else ''

    return render_template(
        'patient/Dashboard.html',
        user_name=user_name,
        name=Name,
        alldepartments=alldepartments,
        allappointments=allappointments,
        
        patient_first=fname or '',
        patient_middle=mname or '',
        patient_last=lname or '',
        patient_phone=phone or '',
        patient_dob=patient_dob,
        patient_gender=gender or '',
        patient_address=address or ''
    )

@app.route('/patient/patient-histoy/<user_name>')
def patient_history_summary(user_name):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT id,First_name, Middle_name,Last_name, user_id, dob,gender,Mobile, address FROM patients WHERE user_id=?",(user_name,))
    patient_info = c.fetchone()
    id,fname,mname,lname,temp,dob,gender,mobile,address=patient_info
    Name=fname+" "+mname+" "+lname
    #print(patient_info)
    c.execute("SELECT id,name FROM departments")
    alldepartments=c.fetchall()
    pid=(c.execute("SELECT id from patients WHERE user_id=?",(user_name,))).fetchone()[0]
    c.execute("""SELECT * FROM patient_visits WHERE patient_id=? ORDER BY visit_date""",
              (pid,))
    allvisits=c.fetchall()
    print(pid,allvisits)
    conn.close()
    return render_template('patient/patient_history.html', user_name=user_name, allvisits=allvisits)

@app.route('/patient/department-details/<user_name>', methods=['POST','GET'])
def department_details(user_name):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT id,First_name, Middle_name,Last_name, user_id, dob,gender,Mobile, address FROM patients WHERE user_id=?",(user_name,))
    patient_info = c.fetchone()
    id,fname,mname,lname,temp,dob,gender,mobile,address=patient_info
    Name=fname+" "+mname+" "+lname
    #print(patient_info)
    d_id=request.form.get('department_id')
    d_name=request.form.get('department_name')
    c.execute("SELECT * FROM doctors where department_id=?",(d_id,))
    alldoctors=c.fetchall()
    overview=c.execute("SELECT overview FROM departments where id=?",(d_id,)).fetchone()[0]
    conn.close()
    return render_template('patient/department_details.html', user_name=user_name, name=d_name, alldoctors=alldoctors, overview=overview )

@app.route('/patient/booking_details/<user_name>', methods=['POST', 'GET'])
def booking_details(user_name):
    doctor_id = request.form.get('doctor_id') or request.args.get('doctor_id')
    if not doctor_id:
        flash("No doctor selected.", "warning")
        return redirect(url_for('patient', user_name=user_name))

    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()

    
    c.execute("SELECT id, First_name, Middle_name, Last_name, user_id FROM patients WHERE user_id=?", (user_name,))
    patient = c.fetchone()
    if not patient:
        conn.close()
        flash("Patient profile not found. Please register or login.", "warning")
        return redirect(url_for('patient', user_name=user_name))
    patient_id = patient[0]
    patient_name = f"{patient[1]} {patient[2]} {patient[3]}".strip()

    
    c.execute("SELECT id, First_name, Middle_name, Last_name, specialization, department_id FROM doctors WHERE id=?", (doctor_id,))
    doctor = c.fetchone()
    if not doctor:
        conn.close()
        flash("Doctor not found.", "warning")
        return redirect(url_for('patient', user_name=user_name))
    doctor_name = f"{doctor[1]} {doctor[2]} {doctor[3]}".strip()

    today = datetime.now().date().strftime("%Y-%m-%d")
    c.execute("""
        SELECT id, date, slot_start, slot_end, status, booking_count
        FROM doctor_availabilities
        WHERE doctor_id=? AND date>=?
        ORDER BY date, slot_start
        LIMIT 100
    """, (doctor_id, today))
    slots = c.fetchall()
    conn.close()


    slot_list = []
    for s in slots:
        sid, sdate, sstart, send, status, bcount = s
        available = (bcount < 5 and status == 'open')
        slot_list.append({
            "id": sid,
            "date": sdate,
            "start": int(sstart),
            "end": int(send),
            "status": status,
            "bookings": int(bcount),
            "available": available
        })

    return render_template('patient/book_appointment.html',
                           user_name=user_name,
                           patient_id=patient_id,
                           patient_name=patient_name,
                           doctor_id=doctor_id,
                           doctor_name=doctor_name,
                           doctor_info=doctor,
                           slots=slot_list)


@app.route('/patient/appointments/confirm/<user_name>', methods=['POST'])
def confirm_booking(user_name):
    """
    Confirm a booking chosen by patient.
    Expects doctor_id, patient_id, slot_id in POST form.
    """
    doctor_id = request.form.get('doctor_id')
    slot_id = request.form.get('slot_id')
    patient_id = request.form.get('patient_id')

    if not (doctor_id and slot_id and patient_id):
        flash("Missing booking information.", "warning")
        return redirect(url_for('patient', user_name=user_name))

    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    try:
    
        deptid=(c.execute("SELECT department_id FROM doctors WHERE id=?",(doctor_id))).fetchone()[0]
        c.execute("SELECT status, booking_count, date, slot_start FROM doctor_availabilities WHERE id=? AND doctor_id=?", (slot_id, doctor_id))
        row = c.fetchone()
        if not row:
            flash("Slot not found.", "danger")
            return redirect(url_for('booking_details', user_name=user_name))

        status, booking_count, slot_date, slot_start = row
        if status != 'open' or booking_count >= 5:
            flash("Selected slot is not available.", "danger")
            return redirect(url_for('booking_details', user_name=user_name))

        # generate a reference number: date + random
        ref_no = f"APP{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"

        c.execute("""
            INSERT INTO appointments (reference_no, patient_id, doctor_id,department_id, slot_id, status,created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ref_no, patient_id, doctor_id, deptid, slot_id, 'Booked',datetime.now()))

        c.execute("UPDATE doctor_availabilities SET booking_count = booking_count + 1 WHERE id=?", (slot_id,))

        conn.commit()
        flash("Appointment booked successfully. Reference: " + ref_no, "success")
    except Exception as e:
        conn.rollback()
        print("Error while booking appointment:", e)
        flash("Failed to book appointment. Try again.", "danger")

    finally:
        conn.close()

    return redirect(url_for('patient', user_name=user_name))

@app.route('/patient/doctor-details/<user_name>', methods=['POST','GET'])
def doctor_details(user_name):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    d_id=request.form.get('doctor_id')
    dname=request.form.get('department_name')
    c.execute("SELECT * FROM doctors where id=?",(d_id,))
    doctorinfo=c.fetchone()
    print(doctorinfo)
    conn.close()
    return render_template('patient/doctor_detail.html', user_name=user_name, doctorinfo=doctorinfo, dname=dname )

@app.route('/patient/cancel/<user_name>', methods=['GET', 'POST'])
def cancel_appointment(user_name):
    appointment_id = request.form.get('appointment_id')
    slot_id = request.form.get('slot_id')

    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    try:
        c.execute("UPDATE appointments SET status = ? WHERE id = ?", ("Cancelled", appointment_id))
        c.execute("UPDATE doctor_availabilities SET booking_count=booking_count-1 WHERE id = ?", ( slot_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Error cancelling appointment:", e)
    finally:
        conn.close()
    return redirect(url_for('patient', user_name=user_name))

@app.route('/patient/<user_name>/update_profile', methods=['POST'])
def patient_update_profile(user_name):
    
    fname = request.form.get('first_name', '').strip()
    mname = request.form.get('middle_name', '').strip()
    lname = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    dob = request.form.get('dob', None)
    gender = request.form.get('gender', None)
    address = request.form.get('address', '').strip()

    
    if mname:
        display_name = f"{fname} {mname} {lname}".strip()
    else:
        display_name = f"{fname} {lname}".strip()

    
    try:
        dob_date = datetime.strptime(dob, "%Y-%m-%d").date() if dob else None
    except Exception:
        dob_date = None

    try:
        conn = sqlite3.connect('./instance/dev.db')
        conn.execute("PRAGMA foreign_keys = ON;")
        c = conn.cursor()

        c.execute("""
            UPDATE patients
            SET First_name = ?, Middle_name = ?, Last_name = ?, dob = ?, gender = ?, address = ?
            WHERE user_id = ?
        """, (fname, mname, lname, dob_date, gender, address, user_name))

        c.execute("""
            UPDATE users
            SET name = ?, phone = ?
            WHERE email = ?
        """, (display_name, phone, user_name))

        conn.commit()
        flash("Profile updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        print("Error updating profile:", e)
        flash("Failed to update profile. Check server logs.", "danger")
    finally:
        conn.close()

    return redirect(url_for('doctor', user_name=user_name) if 'doctor' in user_name else url_for('patient', user_name=user_name))

@app.route('/patient/<user_name>/change_password', methods=['POST'])
def patient_change_password(user_name):
    current = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    if not new or new != confirm:
        flash("New password and confirm password do not match.", "warning")
        return redirect(request.referrer or url_for('patient', user_name=user_name))

    try:
        conn = sqlite3.connect('./instance/dev.db')
        c = conn.cursor()

        
        c.execute("SELECT password FROM users WHERE email = ?", (user_name,))
        row = c.fetchone()
        if not row:
            flash("User not found.", "danger")
            conn.close()
            return redirect(request.referrer or url_for('login'))

        stored = row[0] or ""

        try:
            c.execute("UPDATE users SET password = ? WHERE email = ?", (new, user_name))
            conn.commit()
            flash("Password changed successfully.", "success")
        except Exception as e:
            conn.rollback()
            print("Password change error:", e)
            flash("Failed to change password. Check server logs.", "danger")
        finally:
            conn.close()

    except Exception as e:
        print("Unexpected error:", e)
        flash("Unexpected error. Check server logs.", "danger")

    return redirect(request.referrer or url_for('patient', user_name=user_name))


@app.route('/SignedIn/admin/appointments')
def appointments():
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("""SELECT
               a.id, a.reference_no, a.patient_id, p.First_Name, p.Middle_Name, p.Last_Name, a.doctor_id, doc.First_name, doc.Middle_Name, doc.Last_name, a.department_id,d.name from appointments a, departments d, patients p, doctors doc WHERE a.patient_id=p.id AND a.department_id=d.id AND a.doctor_id=doc.id AND a.status='Booked'""")
    allappointments = c.fetchall()
    print(allappointments)
    conn.close()
    return render_template('SignedIn/appointments.html', allappointments=allappointments)

@app.route('/SignedIn/admin/patient_history', methods=['GET'])
def admin_patient_history():
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify([]), 400

    try:
        conn = sqlite3.connect('./instance/dev.db')
        c = conn.cursor()
        c.execute("""
            SELECT pv.visit_date, pv.visit_type, pv.tests_done, pv.diagnosis, pv.notes, pv.prescription, a.reference_no
            FROM patient_visits pv
            LEFT JOIN appointments a ON pv.appointment_id = a.id
            WHERE pv.patient_id = ?
            ORDER BY pv.visit_date DESC
        """, (patient_id,))
        rows = c.fetchall()
        conn.close()

        # map rows to dicts
        history = []
        for r in rows:
            history.append({
                'visit_date': r[0],
                'visit_type': r[1],
                'tests_done': r[2],
                'diagnosis': r[3],
                'notes': r[4],
                'prescription': r[5],
                'reference_no': r[6]
            })

        return jsonify(history)
    except Exception as e:
        print("Error fetching patient history:", e)
        return jsonify([]), 500

@app.route('/SignedIn/admin/patients/update', methods=['POST'])
def patients_update():
    id = request.form.get('patient_id')
    fname = request.form.get('patient_fname')
    mname = request.form.get('patient_mname')
    lname = request.form.get('patient_lname')
    u_id = request.form.get('u_id')
    mobile = request.form.get('patient_mobile')
    gender = request.form.get('patient_gender')
    DOB = request.form.get('patient_dob')
    
    try:
            dob = datetime.strptime(DOB, "%Y-%m-%d").date()
    except ValueError:
            dob = None
    address = request.form.get('patient_address')
    
    name=fname+" "+mname+" "+lname
    print(fname, mname, lname, dob, mobile, gender, address, u_id)
    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    c.execute("""
      UPDATE patients
      SET First_name = ?, Middle_name = ?, Last_name = ?, dob = ? , Mobile=?, gender=?, address=?
      WHERE user_id = ?
    """, (fname, mname, lname, dob, mobile, gender, address, u_id))
    
    c.execute("""
      UPDATE users
      SET name = ?, phone=? WHERE email=?
    """, (name,mobile,u_id))
    conn.commit()
    conn.close()

    return redirect(url_for('patients'))

@app.route('/SignedIn/admin/Departments/add', methods=['GET', 'POST'])
def departments_add():
    if request.method == 'POST':
        conn = sqlite3.connect('./instance/dev.db')
        c = conn.cursor()
        deptid = request.form['department_id']
        name = request.form['department_name']
        overview = request.form['department_overview']

        try:
            c.execute("INSERT INTO departments (id, name, overview) VALUES (?, ?, ?)", (deptid, name, overview))
            conn.commit()
            conn.close()
            print("✅ Department added successfully.")
            return redirect(url_for('departments', message="✅ Department added successfully."))

        except Exception as e:
            print("❌ Error:", e)
            conn.rollback()
            conn.close()
            return redirect(url_for('departments', message="⚠️ Department ID already exists or invalid input."))


@app.route('/SignedIn/admin/Departments/delete/<dept_id>')
def departments_delete(dept_id):
    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    alldoc=(c.execute(" SELECT user_id from doctors where department_id=?", (dept_id,))).fetchall()
    for id in alldoc:
        c.execute("DELETE FROM users where email=?",(id[0],))
    c.execute("DELETE FROM departments WHERE id= ?", (dept_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('departments')) 


@app.route('/SignedIn/admin/Departments/update', methods=['POST'])
def departments_update():
    dept_id = request.form.get('department_id')
    name = request.form.get('department_name')
    overview = request.form.get('department_overview')

    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("""
      UPDATE departments
      SET name = ?, overview = ?
      WHERE id = ?
    """, (name, overview, dept_id))
    conn.commit()
    conn.close()

    return redirect(url_for('departments')) 
   

@app.route('/SignedIn/admin/Doctors/Delete/<user_id>')
def user_delete(user_id):
    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE email = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/SignedIn/admin/Doctors/update', methods=['POST'])
def doctors_update():
    doc_id = request.form.get('doctor_id')
    fname = request.form.get('doctor_fname')
    mname = request.form.get('doctor_mname')
    lname = request.form.get('doctor_lname')
    u_id = request.form.get('u_id')
    dept_id = request.form.get('doctor_dept')
    mobile = request.form.get('doctor_mobile')
    specialization = request.form.get('doctor_specialization')
    spec_date = request.form.get('doctor_specd')
    try:
            Spec_date = datetime.strptime(spec_date, "%Y-%m-%d").date()
    except ValueError:
            Spec_date = None
    bio = request.form.get('doctor_bio')
    print("Received doctor_id:", u_id)
    print("Received:", fname,lname,u_id,dept_id, mobile, specialization,Spec_date,bio)
    name=fname+" "+mname+" "+lname

    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("""
      UPDATE doctors
      SET First_name = ?, Middle_name = ?, Last_name = ?, department_id = ? ,Mobile=?, specialization=?, Spec_date=?, bio=?
      WHERE id = ?
    """, (fname, mname, lname, dept_id, mobile, specialization,Spec_date, bio, doc_id))
    c.execute("""
      UPDATE users
      SET name = ?, phone=? WHERE email=?
    """, (name,mobile,u_id))
    conn.commit()
    conn.close()

    return redirect(url_for('admin'))


@app.route('/SignedIn/admin/Doctors/reject/<user_id>')
def user_reject(user_id):
    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("DELETE FROM que WHERE email = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/SignedIn/admin/Doctors/Approve/<user_id>')
def user_approve(user_id):
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT * FROM que WHERE email = ?", (user_id,))
    data=c.fetchone()
    print(data)
    id=(c.execute("SELECT MAX(id) FROM doctors").fetchone())[0]+1
    uid=(c.execute("SELECT MAX(id) FROM users").fetchone())[0]+1
    fname=data[1]
    mname=data[2]
    lname=data[3]
    name= fname+" "+mname+" "+lname
    email=data[4]
    passwd=data[5]
    mobile=int(data[6])
    specialisation=data[7]+","+data[8]
    print(data[10])
    try:
        spec_date = datetime.strptime(data[10], "%Y-%m-%d").date()
    except ValueError:
        spec_date = None
    bio=data[11]
    dept_id=(c.execute("SELECT id FROM departments WHERE name = ?", (data[8],))).fetchone()
    c.execute("INSERT INTO users (id, name, email, phone,password,role) VALUES (?, ?, ?, ?, ?, ?)",(uid, name, email, mobile, passwd,"doctor"))
    c.execute("INSERT INTO doctors (id, First_name, Middle_name, Last_name,user_id,Mobile, specialization,Spec_date,bio, department_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,? )",(id, fname, mname, lname, email, mobile, specialisation, spec_date,bio,dept_id[0]))
    c.execute("DELETE FROM que WHERE email=?",(email,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usernm = request.form['input_username']
        passwd = request.form['input_password']
        return authenticate(usernm, passwd)
    return render_template('login.html')


@app.route('/Doctor_Register', methods=['GET', 'POST'])
def Doctor_Register():
    print("doctor register")
    if request.method=='POST':
        firstname=request.form['doctor_first_name']
        middle_name=request.form['doctor_middle_name']
        Surname=request.form['doctor_surname']
        email=request.form['inputEmail4']
        passw=request.form['inputPassword4']
        ph=request.form['inputmobile4']
        Speciality=request.form['inputSpeciality']
        Specialisation=request.form['inputSpecialisation']
        MBBS=request.form['inputMBBSdate']
        Spec_date=request.form['inputSpecialisationdate']
        bio=request.form['inputbio']
        try:
            mbbs = datetime.strptime(MBBS, "%Y-%m-%d").date()
        except ValueError:
            mbbs = None
        try:
            spec_date = datetime.strptime(Spec_date, "%Y-%m-%d").date()
        except ValueError:
            spec_date = None
        queue=Que(first_name = firstname ,middle_name = middle_name,surname = Surname ,email = email, password =passw ,phone = ph,specialty =Speciality ,specialisation = Specialisation,mbbs_date = mbbs,spec_date =spec_date ,bio = bio ,status ='pending' )
        db.session.add(queue)
        db.session.commit()
    conn = sqlite3.connect('./instance/dev.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM departments")
    alldepartments = c.fetchall()
    conn.close()
    print (alldepartments)


    return render_template('Doctor_Register.html', alldepartments=alldepartments)

@app.route('/patient_register', methods=['GET','POST'])
def patient_register():
    if request.method=='POST':
        conn = sqlite3.connect('./instance/dev.db')
        c = conn.cursor()
        firstname=request.form['patient_first_name']
        middle_name=request.form['patient_middle_name']
        Surname=request.form['patient_surname']
        email=request.form['inputEmail4']
        passw=request.form['inputPassword4']
        DOB=request.form['DOB']
        Gender=request.form['Gender']
        ph=request.form['inputmobile4']
        Address=request.form['inputaddress']
        if middle_name=='':
            Name=firstname+' '+Surname
        else:
            Name=firstname+' '+middle_name+' '+Surname
        existing = User.query.filter_by(email=email).first()
        if existing:
            print("An account with that email already exists. Please log in or use another email.", "warning")
            return render_template('patient_register.html')
        c.execute("""INSERT INTO users 
            (name,email, phone, password, role)
            VALUES (?, ?, ?, ?, 'patient')
        """, (Name, email, ph, passw))
        conn.commit()
        print("User Addition Done")
        
        try:
            dob = datetime.strptime(DOB, "%Y-%m-%d").date()
        except ValueError:
            dob = None
        c.execute("""INSERT INTO patients 
            (user_id, FIrst_name, Middle_name, Last_name, dob, gender, Mobile, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, firstname,middle_name,Surname,dob,Gender,ph, Address))
        conn.commit()
        conn.close()
        print(" patient Done")
    return render_template('patient_register.html')

if __name__=="__main__":
    app.run(debug=True)

    