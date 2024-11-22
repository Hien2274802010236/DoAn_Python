from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2 import Error
from math import ceil

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Cấu hình database
DB_CONFIG = {
    'dbname': 'students',
    'user': 'postgres', 
    'password': '123456',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Số lượng sinh viên trên mỗi trang
STUDENTS_PER_PAGE = 10

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    filter_gender = request.args.get('gender', '')
    filter_major = request.args.get('major', '')
    
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        
        # Base query
        query = "SELECT * FROM students WHERE 1=1"
        params = []
        
        # Thêm điều kiện tìm kiếm
        if search:
            query += " AND (LOWER(name) LIKE LOWER(%s) OR LOWER(major) LIKE LOWER(%s))"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])
            
        # Thêm điều kiện lọc
        if filter_gender:
            query += " AND LOWER(gender) = LOWER(%s)"
            params.append(filter_gender)
            
        if filter_major:
            query += " AND LOWER(major) = LOWER(%s)"
            params.append(filter_major)
            
        # Đếm tổng số sinh viên thỏa mãn điều kiện
        count_query = f"SELECT COUNT(*) FROM ({query}) as count_query"
        cur.execute(count_query, params)
        total_students = cur.fetchone()[0]
        total_pages = ceil(total_students / STUDENTS_PER_PAGE)
        
# Kiểm tra giá trị page
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        # Thêm LIMIT và OFFSET cho phân trang
        query += " ORDER BY id LIMIT %s OFFSET %s"
        offset = (page - 1) * STUDENTS_PER_PAGE
        params.extend([STUDENTS_PER_PAGE, offset])
        
        # Thực thi truy vấn chính
        cur.execute(query, params)
        students = cur.fetchall()
        
        # Lấy danh sách các giới tính và ngành học để tạo bộ lọc
        cur.execute("SELECT DISTINCT gender FROM students")
        genders = [row[0] for row in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT major FROM students")
        majors = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return render_template('index.html',
                             students=students,
                             page=page,
                             total_pages=total_pages,
                             search=search,
                             filter_gender=filter_gender,
                             filter_major=filter_major,
                             genders=genders,
                             majors=majors)
    return "Database connection error"

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        major = request.form['major']

        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                # Kiểm tra sinh viên đã tồn tại
                cur.execute("SELECT COUNT(*) FROM students WHERE name = %s AND age = %s AND gender = %s AND major = %s",
                          (name, age, gender, major))
                if cur.fetchone()[0] > 0:
                    flash('Sinh viên với thông tin này đã tồn tại')
                else:
                    cur.execute("INSERT INTO students (name, age, gender, major) VALUES (%s, %s, %s, %s)",
                              (name, age, gender, major))
                    conn.commit()
                    flash('Thêm sinh viên thành công')
                cur.close()
                conn.close()
            except Error as e:
                flash(f'Lỗi: {e}')
        return redirect(url_for('index'))
    return render_template('add_student.html')

@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = get_db_connection()
    if conn:
        if request.method == 'POST':
            name = request.form['name']
            age = request.form['age']
            gender = request.form['gender']
            major = request.form['major']
            
            cur = conn.cursor()
            cur.execute("""UPDATE students 
                          SET name = %s, age = %s, gender = %s, major = %s 
                          WHERE id = %s""",
                       (name, age, gender, major, id))
            conn.commit()
            cur.close()
            conn.close()
            flash('Cập nhật sinh viên thành công')
            return redirect(url_for('index'))
        
        cur = conn.cursor()
        cur.execute('SELECT * FROM students WHERE id = %s', (id,))
        student = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('edit_student.html', student=student)
    return "Database connection error"

@app.route('/delete_student/<int:id>')
def delete_student(id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM students WHERE id = %s', (id,))
        conn.commit()
        cur.close()
        conn.close()
        flash('Xóa sinh viên thành công')
    return redirect(url_for('index'))

@app.route('/statistics')
def statistics():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        
        # Tổng số sinh viên
        cur.execute("SELECT COUNT(*) FROM students")
        total_students = cur.fetchone()[0]
        
        # Thống kê theo giới tính
        cur.execute("SELECT gender, COUNT(*) FROM students GROUP BY gender")
        gender_stats = cur.fetchall()
        
        # Thống kê theo ngành học
        cur.execute("SELECT major, COUNT(*) FROM students GROUP BY major")
        major_stats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('statistics.html', 
                             total_students=total_students,
                             gender_stats=gender_stats,
                             major_stats=major_stats)
    return "Database connection error"

    # Chuẩn bị dữ liệu cho biểu đồ giới tính
    gender_labels = [gender for gender, _ in gender_stats]
    gender_counts = [count for _, count in gender_stats]

    return render_template('statistics.html',
                           total_students=total_students,
                           gender_stats=gender_stats,
                           major_stats=major_stats,
                           major_labels=major_labels,
                           major_counts=major_counts,
                           gender_labels=gender_labels,
                           gender_counts=gender_counts)
if __name__ == '__main__':
    app.run(debug=True)