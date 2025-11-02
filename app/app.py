from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import *
from sqlalchemy import inspect
from models import *
import sqlite3
from flask import request, redirect, url_for, flash


app = Flask(__name__)
login_manager = LoginManager()
# basic config
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
        return redirect(url_for('patient'))
    elif role=="doctor":
        return redirect(url_for('doctor'))
    elif role=="admin":
        return redirect(url_for('admin'))

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
    c.execute("SELECT id,First_name, Middle_name,Last_name, user_id, dob,gender,Mobile, address FROM patients")
    allPatients = c.fetchall()
    print(allPatients)
    conn.close()
    return render_template('SignedIn/patients.html', allPatients=allPatients,)


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


@app.route('/SignedIn/admin/Departments/delete/<dept_name>')
def departments_delete(dept_name):
    conn = sqlite3.connect('./instance/dev.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("DELETE FROM departments WHERE name= ?", (dept_name,))
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
    conn.execute("PRAGMA foreign_keys = ON;")
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
    print(spec_date, dept_id[0],id)
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
        print("Que done")
    return render_template('Doctor_Register.html')

@app.route('/patient_register', methods=['GET','POST'])
def patient_register():
    if request.method=='POST':
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
        user=User(name=Name,email=email,phone=ph,password=passw,role='patient')
        print(user)
        db.session.add(user)
        db.session.commit()
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with that email already exists. Please log in or use another email.", "warning")
            return render_template('patient_register.html')
        try:
            dob = datetime.strptime(DOB, "%Y-%m-%d").date()
        except ValueError:
            dob = None
        patient = Patient(user_id=user.id, dob=dob, gender=Gender, address=Address)
        db.session.add(patient)
        db.session.commit()
        print(user, patient)
    return render_template('patient_register.html')

if __name__=="__main__":
    app.run(debug=True)