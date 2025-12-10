import sqlite3
import json
from datetime import datetime, timedelta

DB_NAME = 'fitness_bot.db'

def _execute(query, params=(), fetchone=False, fetchall=False, commit=False):
    """Универсальная функция для выполнения запросов к БД."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()

def init_db():
    """Инициализирует базу данных, создает таблицы и загружает упражнения из JSON."""
    # Создание таблиц
    _execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            weight REAL,
            height INTEGER,
            age INTEGER,
            gender TEXT,
            target TEXT,
            activity_level TEXT
        )
    ''')
    _execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            muscle_group TEXT NOT NULL,
            default_sets INTEGER,
            default_reps TEXT
        )
    ''')
    _execute('''
        CREATE TABLE IF NOT EXISTS workout_plans (
            plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    _execute('''
        CREATE TABLE IF NOT EXISTS workout_plan_exercises (
            plan_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            sets INTEGER,
            reps TEXT,
            FOREIGN KEY (plan_id) REFERENCES workout_plans (plan_id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (exercise_id) ON DELETE CASCADE
        )
    ''')
    _execute('''
        CREATE TABLE IF NOT EXISTS progress_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            weight REAL,
            sets INTEGER,
            reps TEXT,
            log_date DATE DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (exercise_id) ON DELETE CASCADE
        )
    ''')
    # Загрузка упражнений из JSON
    _load_exercises_from_json()

def _load_exercises_from_json():
    """Очищает таблицу упражнений и загружает в нее данные из exercises.json."""
    try:
        with open('exercises.json', 'r', encoding='utf-8') as f:
            exercises = json.load(f)

        # Очищаем таблицу перед загрузкой
        _execute("DELETE FROM exercises", commit=True)
        
        # Сбрасываем автоинкрементный счетчик для sqlite
        _execute("DELETE FROM sqlite_sequence WHERE name='exercises'", commit=True)

        insert_query = "INSERT INTO exercises (name, muscle_group, default_sets, default_reps) VALUES (?, ?, ?, ?)"
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            for ex in exercises:
                cursor.execute(insert_query, (ex['name'], ex['muscle_group'], ex.get('default_sets'), ex.get('default_reps')))
            conn.commit()

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка при загрузке упражнений из exercises.json: {e}")

# --- Функции для работы с пользователями ---

def get_user(user_id):
    return _execute("SELECT user_id, weight, height, age, gender, target, activity_level FROM users WHERE user_id = ?", (user_id,), fetchone=True)

def add_user(user_id, weight, height, age, gender, target, activity_level):
    _execute(
        "INSERT OR REPLACE INTO users (user_id, weight, height, age, gender, target, activity_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, weight, height, age, gender, target, activity_level),
        commit=True
    )

def delete_user(user_id):
    # Каскадное удаление само удалит связанные планы и логи
    _execute("DELETE FROM users WHERE user_id = ?", (user_id,), commit=True)

def update_user_profile(user_id, fields_to_update):
    if not fields_to_update:
        return
    set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
    params = list(fields_to_update.values()) + [user_id]
    _execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", tuple(params), commit=True)

# --- Функции для работы с упражнениями ---

def get_exercises_by_muscle_group(muscle_group):
    """Возвращает список кортежей (id, name) для указанной группы мышц."""
    return _execute("SELECT exercise_id, name FROM exercises WHERE muscle_group = ?", (muscle_group,), fetchall=True)

def get_all_exercises():
    """Возвращает список всех упражнений в виде кортежей (id, name)."""
    return _execute("SELECT exercise_id, name FROM exercises", fetchall=True)

def get_exercise_defaults(exercise_id):
    """Возвращает (default_sets, default_reps) для упражнения."""
    return _execute("SELECT default_sets, default_reps FROM exercises WHERE exercise_id = ?", (exercise_id,), fetchone=True)

# --- Функции для работы с планами тренировок ---

def get_user_workout_plans(user_id):
    """Возвращает список планов пользователя (plan_id, name)."""
    return _execute("SELECT plan_id, name FROM workout_plans WHERE user_id = ?", (user_id,), fetchall=True)

def workout_plan_exists(user_id, plan_name):
    """Проверяет, существует ли у пользователя план с таким названием."""
    return _execute("SELECT 1 FROM workout_plans WHERE user_id = ? AND name = ?", (user_id, plan_name), fetchone=True) is not None

def create_workout_plan(user_id, plan_name):
    """Создает новый план тренировок и возвращает его ID."""
    return _execute("INSERT INTO workout_plans (user_id, name) VALUES (?, ?)", (user_id, plan_name), commit=True)

def add_exercise_to_plan(plan_id, exercise_id, sets, reps):
    """Добавляет упражнение в план."""
    _execute(
        "INSERT INTO workout_plan_exercises (plan_id, exercise_id, sets, reps) VALUES (?, ?, ?, ?)",
        (plan_id, exercise_id, sets, reps),
        commit=True
    )

def get_workout_plan_details(plan_id):
    """Возвращает детали плана: (exercise_name, sets, reps)."""
    query = """
        SELECT e.name, wpe.sets, wpe.reps
        FROM workout_plan_exercises wpe
        JOIN exercises e ON wpe.exercise_id = e.exercise_id
        WHERE wpe.plan_id = ?
    """
    return _execute(query, (plan_id,), fetchall=True)

def delete_workout_plan(plan_id):
    # Каскадное удаление удалит связанные упражнения из workout_plan_exercises
    _execute("DELETE FROM workout_plans WHERE plan_id = ?", (plan_id,), commit=True)

def update_plan_name(plan_id, new_name):
    _execute("UPDATE workout_plans SET name = ? WHERE plan_id = ?", (new_name, plan_id), commit=True)

def remove_exercise_from_plan(plan_id, exercise_id):
    _execute(
        "DELETE FROM workout_plan_exercises WHERE plan_id = ? AND exercise_id = ?",
        (plan_id, exercise_id),
        commit=True
    )

# --- Функции для работы с прогрессом ---

def add_progress_log(user_id, exercise_id, weight, sets, reps):
    """Добавляет запись о прогрессе."""
    _execute(
        "INSERT INTO progress_logs (user_id, exercise_id, weight, sets, reps) VALUES (?, ?, ?, ?, ?)",
        (user_id, exercise_id, weight, sets, reps),
        commit=True
    )

def get_progress_logs(user_id, exercise_id, period='all'):
    """Получает логи прогресса за определенный период ('week', 'month', 'all')."""
    base_query = "SELECT weight, sets, reps, date(log_date) FROM progress_logs WHERE user_id = ? AND exercise_id = ?"
    params = [user_id, exercise_id]

    if period == 'week':
        base_query += " AND log_date >= date('now', '-7 days')"
    elif period == 'month':
        base_query += " AND log_date >= date('now', '-30 days')"
    
    base_query += " ORDER BY log_date DESC"
    
    return _execute(base_query, tuple(params), fetchall=True)