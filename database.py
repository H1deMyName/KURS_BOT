import sqlite3

def init_db():
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()

    # Таблица для пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY,
            weight REAL,
            height INTEGER,
            age INTEGER,
            gender TEXT,
            target TEXT,
            activity_level TEXT 
        )
    ''')

    # Таблица для упражнений
    cur.execute("DROP TABLE IF EXISTS Exercises") # Удалить для обновления схемы во время разработки
    cur.execute('''
        CREATE TABLE IF NOT EXISTS Exercises (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            muscle_group TEXT NOT NULL,
            default_sets INTEGER,
            default_reps TEXT
        )
    ''')

    # Таблица для планов тренировок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS WorkoutPlans (
            plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    ''')

    # Таблица для связи упражнений в плане тренировок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS WorkoutPlanExercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            exercise_id INTEGER,
            sets INTEGER,
            reps TEXT,
            FOREIGN KEY (plan_id) REFERENCES WorkoutPlans(plan_id),
            FOREIGN KEY (exercise_id) REFERENCES Exercises(exercise_id)
        )
    ''')
    
    # Таблица для журналов прогресса
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ProgressLogs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exercise_id INTEGER,
            weight REAL,
            sets INTEGER,
            reps TEXT,
            log_date DATETIME,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (exercise_id) REFERENCES Exercises(exercise_id)
        )
    ''')

    conn.commit()
    conn.close()

def populate_exercises():
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM Exercises")
        if cur.fetchone()[0] > 0:
            return # Не заполнять, если уже заполнено

        exercises = [
            # Грудь
            ('Жим лежа', 'Грудь', 3, '8-12'),
            ('Жим гантелей лежа', 'Грудь', 3, '10-15'),
            ('Отжимания на брусьях', 'Грудь', 3, '10-15'),
            ('Сведение рук в кроссовере', 'Грудь', 3, '12-15'),
            # Спина
            ('Подтягивания', 'Спина', 4, '6-10'),
            ('Тяга штанги в наклоне', 'Спина', 3, '8-12'),
            ('Тяга вертикального блока', 'Спина', 3, '10-15'),
            ('Горизонтальная тяга', 'Спина', 3, '10-15'),
            # Ноги
            ('Приседания со штангой', 'Ноги', 4, '8-12'),
            ('Жим ногами', 'Ноги', 3, '10-15'),
            ('Становая тяга', 'Ноги', 3, '6-8'),
            ('Выпады с гантелями', 'Ноги', 3, '10-12'),
            # Плечи
            ('Армейский жим', 'Плечи', 4, '8-12'),
            ('Махи гантелями в стороны', 'Плечи', 3, '12-15'),
            ('Тяга штанги к подбородку', 'Плечи', 3, '10-12'),
            # Руки
            ('Сгибания рук со штангой', 'Руки', 3, '8-12'),
            ('Французский жим', 'Руки', 3, '10-15'),
            ('Молотковые сгибания', 'Руки', 3, '10-12')
        ]
        
        cur.executemany("INSERT INTO Exercises (name, muscle_group, default_sets, default_reps) VALUES (?, ?, ?, ?)", exercises)
        conn.commit()
    finally:
        conn.close()


def add_user(user_id, **kwargs):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO Users (user_id, weight, height, age, gender, target, activity_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, kwargs['weight'], kwargs['height'], kwargs['age'], kwargs['gender'], kwargs['target'], kwargs['activity_level']))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def update_user_profile(user_id, data_to_update):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    
    fields = ', '.join([f"{key} = ?" for key in data_to_update.keys()])
    values = list(data_to_update.values())
    values.append(user_id)
    
    cur.execute(f"UPDATE Users SET {fields} WHERE user_id = ?", values)
    
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    try:
        # 1. Найти все планы тренировок пользователя
        cur.execute("SELECT plan_id FROM WorkoutPlans WHERE user_id = ?", (user_id,))
        plan_ids = [row[0] for row in cur.fetchall()]

        # 2. Удалить записи о прогрессе
        cur.execute("DELETE FROM ProgressLogs WHERE user_id = ?", (user_id,))

        # 3. Если у пользователя были планы, удалить связанные с ними упражнения
        if plan_ids:
            # Создаем плейсхолдеры для IN-клаузы
            placeholders = ','.join('?' for _ in plan_ids)
            cur.execute(f"DELETE FROM WorkoutPlanExercises WHERE plan_id IN ({placeholders})", plan_ids)

        # 4. Удалить сами планы тренировок
        cur.execute("DELETE FROM WorkoutPlans WHERE user_id = ?", (user_id,))

        # 5. Удалить пользователя
        cur.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))

        conn.commit()
    finally:
        conn.close()

# --- Функции для планов тренировок ---

def get_exercises_by_muscle_group(muscle_group):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT exercise_id, name FROM Exercises WHERE muscle_group = ?", (muscle_group,))
    exercises = cur.fetchall()
    conn.close()
    return exercises

def get_exercise_defaults(exercise_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT default_sets, default_reps FROM Exercises WHERE exercise_id = ?", (exercise_id,))
    defaults = cur.fetchone()
    conn.close()
    return defaults

def create_workout_plan(user_id, plan_name):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO WorkoutPlans (user_id, name) VALUES (?, ?)", (user_id, plan_name))
    plan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def workout_plan_exists(user_id, plan_name):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM WorkoutPlans WHERE user_id = ? AND name = ?", (user_id, plan_name))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def add_exercise_to_plan(plan_id, exercise_id, sets, reps):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO WorkoutPlanExercises (plan_id, exercise_id, sets, reps) VALUES (?, ?, ?, ?)",
                (plan_id, exercise_id, sets, reps))
    conn.commit()
    conn.close()

def get_user_workout_plans(user_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT plan_id, name FROM WorkoutPlans WHERE user_id = ?", (user_id,))
    plans = cur.fetchall()
    conn.close()
    return plans

def get_workout_plan_details(plan_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT E.name, WPE.sets, WPE.reps
        FROM WorkoutPlanExercises WPE
        JOIN Exercises E ON WPE.exercise_id = E.exercise_id
        WHERE WPE.plan_id = ?
    """, (plan_id,))
    details = cur.fetchall()
    conn.close()
    return details

def get_all_exercises():
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT exercise_id, name FROM Exercises ORDER BY muscle_group, name")
    exercises = cur.fetchall()
    conn.close()
    return exercises

def update_plan_name(plan_id, new_name):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE WorkoutPlans SET name = ? WHERE plan_id = ?", (new_name, plan_id))
    conn.commit()
    conn.close()

def remove_exercise_from_plan(plan_id, exercise_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    # Используйте LIMIT 1, чтобы убедиться, что удаляется только один экземпляр, если существуют дубликаты
    cur.execute("DELETE FROM WorkoutPlanExercises WHERE plan_id = ? AND exercise_id = ? LIMIT 1", (plan_id, exercise_id))
    conn.commit()
    conn.close()

def delete_workout_plan(plan_id):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM WorkoutPlanExercises WHERE plan_id = ?", (plan_id,))
    cur.execute("DELETE FROM WorkoutPlans WHERE plan_id = ?", (plan_id,))
    conn.commit()
    conn.close()

# --- Функции для журнала прогресса ---

def add_progress_log(user_id, exercise_id, weight, sets, reps):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ProgressLogs (user_id, exercise_id, weight, sets, reps, log_date)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (user_id, exercise_id, weight, sets, reps))
    conn.commit()
    conn.close()

def get_progress_logs(user_id, exercise_id, period='all'):
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    
    query = """
        SELECT weight, sets, reps, strftime('%Y-%m-%d', log_date)
        FROM ProgressLogs
        WHERE user_id = ? AND exercise_id = ?
    """
    params = [user_id, exercise_id]

    if period == 'week':
        query += " AND log_date >= date('now', '-7 days')"
    elif period == 'month':
        query += " AND log_date >= date('now', '-30 days')"

    query += " ORDER BY log_date DESC"
    
    cur.execute(query, params)
    logs = cur.fetchall()
    conn.close()
    return logs
