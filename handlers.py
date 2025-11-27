from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import sqlite3

from database import (
    get_user, add_user, delete_user, update_user_profile,
    get_exercises_by_muscle_group, create_workout_plan, workout_plan_exists,
    add_exercise_to_plan, get_user_workout_plans,
    get_workout_plan_details, delete_workout_plan,
    get_all_exercises, add_progress_log, get_progress_logs,
    get_exercise_defaults, update_plan_name, remove_exercise_from_plan)
from states import (
    RegistrationStates, PlanCreationStates, LogProgressStates, 
    ProfileEditingStates, ViewProgressStates, PlanEditingStates)
from tools import calculate_bmi, calculate_calories

# --- Клавиатуры ---
main_menu_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📝 Планирование"), KeyboardButton(text="📊 Трекинг прогресса")],
    [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
    [KeyboardButton(text="⚖️ Расчет калорий")]
], resize_keyboard=True)

gender_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")]], resize_keyboard=True, one_time_keyboard=True)
target_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📈 Набор массы")], [KeyboardButton(text="📉 Сброс веса")], [KeyboardButton(text="⚖️ Поддержание")]], resize_keyboard=True, one_time_keyboard=True)
activity_level_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🛋️ Минимальная")],
    [KeyboardButton(text="🚶 Легкая")],
    [KeyboardButton(text="🏃 Средняя")],
    [KeyboardButton(text="🔥 Высокая")]
], resize_keyboard=True, one_time_keyboard=True)

profile_management_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Изменить профиль", callback_data="edit_profile")],
    [InlineKeyboardButton(text="🗑️ Сбросить профиль", callback_data="reset_profile")]
])

edit_profile_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚖️ Вес", callback_data="edit_field_weight"), InlineKeyboardButton(text="📏 Рост", callback_data="edit_field_height")],
    [InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_field_age"), InlineKeyboardButton(text="🚻 Пол", callback_data="edit_field_gender")],
    [InlineKeyboardButton(text="🏃‍♂️ Активность", callback_data="edit_field_activity"), InlineKeyboardButton(text="🎯 Цель", callback_data="edit_field_target")],
    [InlineKeyboardButton(text="↩️ Назад к профилю", callback_data="back_to_profile")]
])

registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Зарегистрироваться", callback_data="start_registration")]
])

muscle_group_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💪 Грудь", callback_data="mg_Грудь"), InlineKeyboardButton(text="💪 Спина", callback_data="mg_Спина")],
    [InlineKeyboardButton(text="🦵 Ноги", callback_data="mg_Ноги"), InlineKeyboardButton(text="💪 Плечи", callback_data="mg_Плечи")],
    [InlineKeyboardButton(text="💪 Руки", callback_data="mg_Руки")],
    [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_exercises")]
])

add_more_exercises_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_more_exercises")],
    [InlineKeyboardButton(text="✅ Завершить план", callback_data="finish_plan")]
])

progress_filter_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="7️⃣ Неделя", callback_data="progress_week"),
     InlineKeyboardButton(text="🗓️ Месяц", callback_data="progress_month"),
     InlineKeyboardButton(text="♾️ Все время", callback_data="progress_all")]
])

def get_edit_plan_menu_keyboard(plan_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename_plan_{plan_id}")],
        [InlineKeyboardButton(text="➕ Добавить упражнение", callback_data=f"add_ex_to_plan_{plan_id}")],
        [InlineKeyboardButton(text="➖ Удалить упражнение", callback_data=f"remove_ex_from_plan_{plan_id}")],
        [InlineKeyboardButton(text="↩️ Назад к планам", callback_data="back_to_plans")]
    ])

# --- Регистрация обработчиков ---
def register_handlers(dp: Dispatcher):
    # Обработчики команд и текста
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_plan, lambda message: message.text == "📝 Планирование" or message.text == "/plan")
    dp.message.register(cmd_log, lambda message: message.text == "📊 Трекинг прогресса" or message.text == "/log")
    dp.message.register(cmd_calories, lambda message: message.text == "⚖️ Расчет калорий" or message.text == "/calories")
    dp.message.register(cmd_profile, lambda message: message.text == "👤 Профиль" or message.text == "/profile")
    dp.message.register(cmd_help, lambda message: message.text == "❓ Помощь" or message.text == "/help")

    # Обработчики состояний (Регистрация)
    dp.message.register(process_weight, RegistrationStates.waiting_for_weight)
    dp.message.register(process_height, RegistrationStates.waiting_for_height)
    dp.message.register(process_age, RegistrationStates.waiting_for_age)
    dp.message.register(process_gender, RegistrationStates.waiting_for_gender)
    dp.message.register(process_activity_level, RegistrationStates.waiting_for_activity_level)
    dp.message.register(process_target, RegistrationStates.waiting_for_target)

    # Обработчики состояний (Создание и редактирование плана)
    dp.message.register(process_plan_name, PlanCreationStates.waiting_for_plan_name)
    dp.callback_query.register(process_muscle_group_selection, 
                               lambda c: c.data.startswith('mg_') or c.data == 'finish_exercises',
                               PlanCreationStates.waiting_for_muscle_group)
    dp.callback_query.register(process_exercise_selection, 
                               lambda c: c.data.startswith('ex_') or c.data == 'choose_another_mg',
                               PlanCreationStates.waiting_for_exercise_selection)
    dp.callback_query.register(process_add_more_exercises, 
                               lambda c: c.data in ['add_more_exercises', 'finish_plan'], 
                               PlanCreationStates.waiting_for_add_more_exercises)

    # Обработчики состояний (Запись прогресса)
    dp.callback_query.register(handle_plan_for_logging, lambda c: c.data.startswith('log_plan_'), LogProgressStates.waiting_for_plan_selection)
    dp.callback_query.register(handle_exercise_for_logging, lambda c: c.data.startswith('log_ex_'), LogProgressStates.waiting_for_exercise_selection)
    dp.message.register(process_log_details, LogProgressStates.waiting_for_log_details)
    
    # Обработчики состояний (Просмотр прогресса)
    dp.callback_query.register(handle_view_progress_button, lambda c: c.data == 'view_progress')
    dp.callback_query.register(handle_plan_for_viewing, lambda c: c.data.startswith('view_plan_progress_'), ViewProgressStates.waiting_for_plan_selection)
    dp.callback_query.register(handle_exercise_for_viewing, lambda c: c.data.startswith('view_ex_progress_'), ViewProgressStates.waiting_for_exercise_selection)
    dp.callback_query.register(handle_progress_filter, lambda c: c.data.startswith('progress_'))

    # Обработчики состояний (Редактирование профиля)
    dp.message.register(process_edited_weight, ProfileEditingStates.editing_weight)
    dp.message.register(process_edited_height, ProfileEditingStates.editing_height)
    dp.message.register(process_edited_age, ProfileEditingStates.editing_age)
    dp.message.register(process_edited_gender, ProfileEditingStates.editing_gender)
    dp.message.register(process_edited_activity, ProfileEditingStates.editing_activity)
    dp.message.register(process_edited_target, ProfileEditingStates.editing_target)

    # Обработчики состояний (Редактирование плана)
    dp.message.register(process_plan_rename, PlanEditingStates.renaming_plan)
    dp.callback_query.register(handle_remove_exercise_from_plan, lambda c: c.data.startswith('del_ex_from_plan_'), PlanEditingStates.removing_exercise)

    # Общие обработчики запросов обратного вызова
    dp.callback_query.register(handle_reset_profile, lambda c: c.data == 'reset_profile')
    dp.callback_query.register(handle_edit_profile, lambda c: c.data == 'edit_profile')
    dp.callback_query.register(handle_start_registration, lambda c: c.data == 'start_registration')
    dp.callback_query.register(handle_plan_action, lambda c: c.data.startswith(('view_plan_', 'delete_plan_', 'create_new_plan', 'edit_plan_', 'back_to_plans_from_view')))
    dp.callback_query.register(handle_edit_field_selection, lambda c: c.data.startswith('edit_field_') or c.data == 'back_to_profile')
    dp.callback_query.register(handle_edit_plan_action, lambda c: c.data.startswith(('rename_plan_', 'add_ex_to_plan_', 'remove_ex_from_plan_', 'back_to_plans')))


# --- Обработчики команд ---
async def cmd_start(message: types.Message, state: FSMContext):
    if not get_user(message.from_user.id):
        await message.answer("Добро пожаловать! Для начала работы с ботом, давайте зарегистрируемся.", reply_markup=registration_keyboard)
    else:
        await message.answer(f"С возвращением, {message.from_user.first_name}!", reply_markup=main_menu_keyboard)

async def cmd_plan(message: types.Message, state: FSMContext):
    await state.clear()
    user_plans = get_user_workout_plans(message.from_user.id)
    if not user_plans:
        await message.answer("У вас пока нет планов тренировок. Давайте создадим первый! Введите название для вашего нового плана:")
        await state.set_state(PlanCreationStates.waiting_for_plan_name)
    else:
        keyboard_buttons = []
        for plan_id, plan_name in user_plans:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"📝 {plan_name}", callback_data=f"view_plan_{plan_id}"),
                InlineKeyboardButton(text="✏️", callback_data=f"edit_plan_{plan_id}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"delete_plan_{plan_id}")
            ])
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Создать новый план", callback_data="create_new_plan")])
        
        plans_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await message.answer("Ваши планы тренировок:", reply_markup=plans_keyboard)

async def cmd_log(message: types.Message, state: FSMContext):
    await state.clear()
    user_plans = get_user_workout_plans(message.from_user.id)
    if not user_plans:
        await message.answer("У вас нет планов тренировок для записи прогресса. Сначала создайте план в разделе '📝 Планирование'.")
        return

    keyboard_buttons = []
    for plan_id, plan_name in user_plans:
        keyboard_buttons.append([InlineKeyboardButton(text=f"✍️ Записать: {plan_name}", callback_data=f"log_plan_{plan_id}")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="📊 Посмотреть прогресс", callback_data="view_progress")])
    
    plans_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer("Выберите действие:", reply_markup=plans_keyboard)
    await state.set_state(LogProgressStates.waiting_for_plan_selection)

async def cmd_calories(message: types.Message, state: FSMContext):
    user_data = get_user(message.from_user.id)
    if user_data:
        user_id, weight, height, age, gender, target, activity_level = user_data
        
        calorie_needs = calculate_calories(gender, weight, height, age, activity_level)
        
        response_text = (
            f"📊 **Ваша суточная норма калорий:**\n\n"
            f"📉 **Для сброса веса:** ~{calorie_needs['Сброс веса']} ккал\n"
            f"⚖️ **Для поддержания веса:** ~{calorie_needs['Поддержание']} ккал\n"
            f"📈 **Для набора массы:** ~{calorie_needs['Набор массы']} ккал\n\n"
            f"Ваша текущая цель — **{target}**. Рекомендуем придерживаться соответствующей нормы.\n\n"
            f"*Расчеты основаны на формуле Миффлина-Сан Жеора и вашем уровне активности.*"
        )
        await message.answer(response_text, parse_mode="Markdown")
    else:
        await message.answer("Вы не зарегистрированы. Пожалуйста, используйте /start для регистрации, чтобы рассчитать калории.")

async def cmd_profile(message: types.Message, state: FSMContext):
    user_data = get_user(message.from_user.id)
    if user_data:
        user_id, weight, height, age, gender, target, activity_level = user_data
        
        bmi, bmi_category = calculate_bmi(weight, height)

        profile_text = (
            f"👤 **Ваш профиль:**\n\n"
            f"⚖️ Вес: {weight} кг\n"
            f"📏 Рост: {height} см\n"
            f"🎂 Возраст: {age}\n"
            f"🚻 Пол: {gender}\n"
            f"🎯 Цель: {target}\n"
            f"🏃‍♂️ Активность: {activity_level}\n\n"
            f"📈 **ИМТ: {bmi} ({bmi_category})**"
        )
        await message.answer(profile_text, parse_mode="Markdown", reply_markup=profile_management_keyboard)
    else:
        await message.answer("Вы не зарегистрированы. Пожалуйста, используйте /start для регистрации.")

async def cmd_help(message: types.Message):
    help_text = (
        "**Справка по командам:**\n\n"
        "/start - Начало работы с ботом и регистрация.\n"
        "/plan - Планирование тренировок: создание, просмотр и удаление планов.\n"
        "/log - Запись и просмотр прогресса тренировок.\n"
        "/calories - Расчет суточной нормы калорий.\n"
        "/profile - Просмотр, изменение и сброс профиля.\n"
        "/help - Показывает эту справку.")
    await message.answer(help_text, parse_mode="Markdown")

# --- Обработчики состояний (Регистрация) ---
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        if not (20 < weight < 300):
            raise ValueError("Неправдоподобный вес.")
        await state.update_data(weight=weight)
        await message.answer("Отлично! Теперь введите ваш рост в см:")
        await state.set_state(RegistrationStates.waiting_for_height)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для веса (например, 75.5). Вес должен быть в диапазоне от 20 до 300 кг.")

async def process_height(message: types.Message, state: FSMContext):
    try:
        height = int(message.text)
        if not (100 < height < 250):
            raise ValueError("Неправдоподобный рост.")
        await state.update_data(height=height)
        await message.answer("Хорошо. Сколько вам лет?")
        await state.set_state(RegistrationStates.waiting_for_age)
    except ValueError:
        await message.answer("Пожалуйста, введите целочисленное значение для роста в см. Рост должен быть в диапазоне от 100 до 250 см.")

async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if not (12 < age < 100):
            raise ValueError("Неправдоподобный возраст.")
        await state.update_data(age=age)
        await message.answer("Укажите ваш пол:", reply_markup=gender_keyboard)
        await state.set_state(RegistrationStates.waiting_for_gender)
    except ValueError:
        await message.answer("Пожалуйста, введите целочисленное значение для возраста (от 12 до 100).")

async def process_gender(message: types.Message, state: FSMContext):
    gender_text = " ".join(message.text.split(" ")[1:])
    if gender_text in ["Мужской", "Женский"]:
        await state.update_data(gender=gender_text)
        await message.answer("Выберите ваш уровень физической активности:", reply_markup=activity_level_keyboard)
        await state.set_state(RegistrationStates.waiting_for_activity_level)
    else:
        await message.answer("Пожалуйста, выберите один из вариантов.")

async def process_activity_level(message: types.Message, state: FSMContext):
    activity_text = " ".join(message.text.split(" ")[1:])
    if activity_text in ["Минимальная", "Легкая", "Средняя", "Высокая"]:
        await state.update_data(activity_level=activity_text)
        data = await state.get_data()
        bmi, bmi_category = calculate_bmi(data['weight'], data['height'])
        
        recommendation = ""
        if bmi_category == "Избыточный вес" or bmi_category == "Ожирение":
            recommendation = "\n\n**Рекомендуем выбрать цель '📉 Сброс веса'.**"
        elif bmi_category == "Недостаточный вес":
            recommendation = "\n\n**Рекомендуем выбрать цель '📈 Набор массы'.**"

        await message.answer(
            f"Спасибо! Ваш ИМТ: {bmi} ({bmi_category}).{recommendation}\n\nТеперь выберите вашу главную цель:",
            reply_markup=target_keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_target)
    else:
        await message.answer("Пожалуйста, выберите один из вариантов.")

async def process_target(message: types.Message, state: FSMContext):
    target_text = " ".join(message.text.split(" ")[1:])
    if target_text in ["Набор массы", "Сброс веса", "Поддержание"]:
        await state.update_data(target=target_text)
        user_data = await state.get_data()
        add_user(message.from_user.id, **user_data)
        await message.answer("Отлично! Регистрация завершена. Теперь вам доступны все функции бота.", reply_markup=main_menu_keyboard)
        await state.clear()
    else:
        await message.answer("Пожалуйста, выберите один из вариантов.")

# --- Обработчики состояний (Создание и редактирование плана) ---
async def process_plan_name(message: types.Message, state: FSMContext):
    plan_name = message.text.strip()
    if not plan_name:
        await message.answer("Название плана не может быть пустым. Пожалуйста, введите название:")
        return
    
    if workout_plan_exists(message.from_user.id, plan_name):
        await message.answer("План с таким названием уже существует. Пожалуйста, введите другое название:")
        return

    plan_id = create_workout_plan(message.from_user.id, plan_name)
    await state.update_data(current_plan_id=plan_id)
    await message.answer(f"План '{plan_name}' создан. Теперь выберите группу мышц для добавления упражнений:", reply_markup=muscle_group_keyboard)
    await state.set_state(PlanCreationStates.waiting_for_muscle_group)

async def process_muscle_group_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'finish_exercises':
        await callback.message.edit_text("Изменения сохранены!")
        await state.clear()
        await callback.answer()
        return

    muscle_group = callback.data.split('_')[1]
    exercises = get_exercises_by_muscle_group(muscle_group)
    
    if not exercises:
        await callback.message.edit_text(f"Упражнений для группы '{muscle_group}' не найдено. Выберите другую группу мышц:", reply_markup=muscle_group_keyboard)
        await callback.answer()
        return

    exercise_buttons = []
    for ex_id, ex_name in exercises:
        exercise_buttons.append([InlineKeyboardButton(text=ex_name, callback_data=f"ex_{ex_id}")])
    
    exercise_buttons.append([InlineKeyboardButton(text="↩️ Назад к группам мышц", callback_data="choose_another_mg")])
    exercises_keyboard = InlineKeyboardMarkup(inline_keyboard=exercise_buttons)
    
    await callback.message.edit_text(f"Выберите упражнение для группы '{muscle_group}':", reply_markup=exercises_keyboard)
    await state.set_state(PlanCreationStates.waiting_for_exercise_selection)
    await callback.answer()

async def process_exercise_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    is_editing = data.get('is_editing', False)
    plan_id = data.get('current_plan_id')

    if callback.data == 'choose_another_mg':
        await callback.message.edit_text("Выберите группу мышц:", reply_markup=muscle_group_keyboard)
        await state.set_state(PlanCreationStates.waiting_for_muscle_group)
        await callback.answer()
        return

    exercise_id = int(callback.data.split('_')[1])
    defaults = get_exercise_defaults(exercise_id)
    
    if not defaults:
        await callback.message.answer("Не удалось найти информацию для этого упражнения. Пожалуйста, выберите другое.")
        await callback.answer()
        return

    default_sets, default_reps = defaults
    add_exercise_to_plan(plan_id, exercise_id, default_sets, default_reps)
    
    if is_editing:
        await callback.message.edit_text("Упражнение добавлено. Что дальше?", reply_markup=get_edit_plan_menu_keyboard(plan_id))
        await state.set_state(PlanEditingStates.waiting_for_edit_action)
    else:
        await callback.message.edit_text("Упражнение добавлено в план. Что дальше?", reply_markup=add_more_exercises_keyboard)
        await state.set_state(PlanCreationStates.waiting_for_add_more_exercises)
    
    await callback.answer()

async def process_add_more_exercises(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'add_more_exercises':
        await callback.message.edit_text("Выберите группу мышц для добавления следующего упражнения:", reply_markup=muscle_group_keyboard)
        await state.set_state(PlanCreationStates.waiting_for_muscle_group)
    elif callback.data == 'finish_plan':
        await callback.message.edit_text("План тренировок успешно сохранен!")
        await state.clear()
    await callback.answer()

# --- Обработчики состояний (Запись прогресса) ---
async def handle_plan_for_logging(callback: types.CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split('_')[-1])
    
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT E.exercise_id, E.name FROM WorkoutPlanExercises WPE JOIN Exercises E ON WPE.exercise_id = E.exercise_id WHERE WPE.plan_id = ?", (plan_id,))
    exercises_in_plan = cur.fetchall()
    conn.close()

    if not exercises_in_plan:
        await callback.message.edit_text("В этом плане нет упражнений. Добавьте их в разделе '📝 Планирование'.")
        await state.clear()
        await callback.answer()
        return

    keyboard_buttons = []
    for ex_id, ex_name in exercises_in_plan:
        keyboard_buttons.append([InlineKeyboardButton(text=ex_name, callback_data=f"log_ex_{ex_id}")])
    
    exercises_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text("Выберите упражнение для записи прогресса:", reply_markup=exercises_keyboard)
    await state.set_state(LogProgressStates.waiting_for_exercise_selection)
    await callback.answer()

async def handle_exercise_for_logging(callback: types.CallbackQuery, state: FSMContext):
    exercise_id = int(callback.data.split('_')[-1])
    await state.update_data(log_exercise_id=exercise_id)
    
    await callback.message.edit_text("Введите результат в формате: ВЕСxПОДХОДЫxПОВТОРЕНИЯ (например, 80x3x10)")
    await state.set_state(LogProgressStates.waiting_for_log_details)
    await callback.answer()

async def process_log_details(message: types.Message, state: FSMContext):
    try:
        parts = message.text.lower().split('x')
        if len(parts) != 3:
            raise ValueError("Неверный формат")
        
        weight = float(parts[0].replace(',', '.'))
        sets = int(parts[1])
        reps = parts[2]

        data = await state.get_data()
        exercise_id = data['log_exercise_id']
        
        add_progress_log(message.from_user.id, exercise_id, weight, sets, reps)
        
        await message.answer("Прогресс успешно записан!", reply_markup=main_menu_keyboard)
        await state.clear()

    except (ValueError, IndexError):
        await message.answer("Неверный формат. Пожалуйста, введите данные в формате 'ВЕСxПОДХОДЫxПОВТОРЕНИЯ', например: 80x3x10.")

# --- Обработчики просмотра прогресса ---
async def handle_view_progress_button(callback: types.CallbackQuery, state: FSMContext):
    user_plans = get_user_workout_plans(callback.from_user.id)
    if not user_plans:
        await callback.message.edit_text("У вас нет планов тренировок для просмотра прогресса. Сначала создайте план.")
        await state.clear()
        await callback.answer()
        return

    keyboard_buttons = []
    for plan_id, plan_name in user_plans:
        keyboard_buttons.append([InlineKeyboardButton(text=plan_name, callback_data=f"view_plan_progress_{plan_id}")])
    
    plans_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text("Выберите план для просмотра прогресса:", reply_markup=plans_keyboard)
    await state.set_state(ViewProgressStates.waiting_for_plan_selection)
    await callback.answer()

async def handle_plan_for_viewing(callback: types.CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split('_')[-1])
    
    conn = sqlite3.connect('fitness_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT E.exercise_id, E.name FROM WorkoutPlanExercises WPE JOIN Exercises E ON WPE.exercise_id = E.exercise_id WHERE WPE.plan_id = ?", (plan_id,))
    exercises_in_plan = cur.fetchall()
    conn.close()

    if not exercises_in_plan:
        await callback.message.edit_text("В этом плане нет упражнений.")
        await state.clear()
        await callback.answer()
        return

    keyboard_buttons = []
    for ex_id, ex_name in exercises_in_plan:
        keyboard_buttons.append([InlineKeyboardButton(text=ex_name, callback_data=f"view_ex_progress_{ex_id}")])
    
    exercises_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text("Выберите упражнение для просмотра прогресса:", reply_markup=exercises_keyboard)
    await state.set_state(ViewProgressStates.waiting_for_exercise_selection)
    await callback.answer()

async def handle_exercise_for_viewing(callback: types.CallbackQuery, state: FSMContext):
    exercise_id = int(callback.data.split('_')[-1])
    await show_progress(callback, state, exercise_id)

async def show_progress(callback: types.CallbackQuery, state: FSMContext, exercise_id: int):
    await state.update_data(progress_exercise_id=exercise_id)
    
    logs = get_progress_logs(callback.from_user.id, exercise_id, period='all')
    
    exercise_name = ""
    all_exercises = get_all_exercises()
    for ex_id, ex_name in all_exercises:
        if ex_id == exercise_id:
            exercise_name = ex_name
            break

    if not logs:
        await callback.message.edit_text(f"Пока нет записей для упражнения '{exercise_name}'.", reply_markup=None)
        await state.clear()
        await callback.answer()
        return

    response_text = f"**Прогресс для: {exercise_name}**\n\n"
    for log in logs:
        weight, sets, reps, log_date = log
        response_text += f"🗓️ {log_date}: {weight}кг x {sets}x{reps}\n"
        
    await callback.message.edit_text(response_text, reply_markup=progress_filter_keyboard, parse_mode="Markdown")
    await callback.answer()

async def handle_progress_filter(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.split('_')[1]
    data = await state.get_data()
    exercise_id = data.get('progress_exercise_id')

    if not exercise_id:
        await callback.message.edit_text("Произошла ошибка. Пожалуйста, попробуйте снова, выбрав упражнение.")
        await state.clear()
        return

    logs = get_progress_logs(callback.from_user.id, exercise_id, period=period)
    
    exercise_name = ""
    all_exercises = get_all_exercises()
    for ex_id, ex_name in all_exercises:
        if ex_id == exercise_id:
            exercise_name = ex_name
            break

    if not logs:
        await callback.message.edit_text(f"Нет записей для упражнения '{exercise_name}' за выбранный период.", reply_markup=progress_filter_keyboard)
        await callback.answer()
        return

    response_text = f"**Прогресс для: {exercise_name} ({period})**\n\n"
    for log in logs:
        weight, sets, reps, log_date = log
        response_text += f"🗓️ {log_date}: {weight}кг x {sets}x{reps}\n"
        
    await callback.message.edit_text(response_text, reply_markup=progress_filter_keyboard, parse_mode="Markdown")
    await callback.answer()

# --- Обработчики состояний (Редактирование профиля) ---
async def process_edited_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        if not (20 < weight < 300):
            raise ValueError("Неправдоподобный вес.")
        update_user_profile(message.from_user.id, {'weight': weight})
        await message.answer("Вес успешно обновлен.")
        await state.clear()
        await cmd_profile(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для веса (например, 75.5).")

async def process_edited_height(message: types.Message, state: FSMContext):
    try:
        height = int(message.text)
        if not (100 < height < 250):
            raise ValueError("Неправдоподобный рост.")
        update_user_profile(message.from_user.id, {'height': height})
        await message.answer("Рост успешно обновлен.")
        await state.clear()
        await cmd_profile(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите целочисленное значение для роста в см.")

async def process_edited_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if not (12 < age < 100):
            raise ValueError("Неправдоподобный возраст.")
        update_user_profile(message.from_user.id, {'age': age})
        await message.answer("Возраст успешно обновлен.")
        await state.clear()
        await cmd_profile(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите целочисленное значение для возраста.")

async def process_edited_gender(message: types.Message, state: FSMContext):
    if message.text in ["👨 Мужской", "👩 Женский"]:
        update_user_profile(message.from_user.id, {'gender': message.text.split(" ")[1]})
        await message.answer("Пол успешно обновлен.", reply_markup=main_menu_keyboard)
        await state.clear()
        await cmd_profile(message, state)
    else:
        await message.answer("Пожалуйста, выберите один из вариантов: Мужской или Женский.", reply_markup=gender_keyboard)

async def process_edited_activity(message: types.Message, state: FSMContext):
    if message.text.split(" ")[1] in ["Минимальная", "Легкая", "Средняя", "Высокая"]:
        update_user_profile(message.from_user.id, {'activity_level': message.text.split(" ")[1]})
        await message.answer("Уровень активности успешно обновлен.", reply_markup=main_menu_keyboard)
        await state.clear()
        await cmd_profile(message, state)
    else:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=activity_level_keyboard)

async def process_edited_target(message: types.Message, state: FSMContext):
    if message.text.split(" ")[1] in ["Набор массы", "Сброс веса", "Поддержание"]:
        update_user_profile(message.from_user.id, {'target': message.text.split(" ")[1]})
        await message.answer("Цель успешно обновлена.", reply_markup=main_menu_keyboard)
        await state.clear()
        await cmd_profile(message, state)
    else:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=target_keyboard)

# --- Обработчики обратных вызовов ---
async def handle_reset_profile(callback: types.CallbackQuery, state: FSMContext):
    delete_user(callback.from_user.id)
    await callback.message.edit_text("Ваш профиль был сброшен. Для повторной регистрации используйте команду /start.")
    await callback.answer()

async def handle_edit_profile(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Какое поле вы хотите изменить?", reply_markup=edit_profile_keyboard)
    await callback.answer()

async def handle_start_registration(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Давайте начнем регистрацию. Введите ваш вес в кг (например, 75.5):")
    await state.set_state(RegistrationStates.waiting_for_weight)
    await callback.answer()

async def handle_plan_action(callback: types.CallbackQuery, state: FSMContext):
    action_parts = callback.data.split('_')
    action = action_parts[0]

    # Обработка кнопки "назад" из просмотра плана
    if callback.data == 'back_to_plans_from_view':
        await state.clear()
        user_plans = get_user_workout_plans(callback.from_user.id)
        keyboard_buttons = []
        for p_id, p_name in user_plans:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"📝 {p_name}", callback_data=f"view_plan_{p_id}"),
                InlineKeyboardButton(text="✏️", callback_data=f"edit_plan_{p_id}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"delete_plan_{p_id}")
            ])
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Создать новый план", callback_data="create_new_plan")])
        plans_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text("Ваши планы тренировок:", reply_markup=plans_keyboard)
        await callback.answer()
        return

    if action == 'view':
        plan_id = int(action_parts[2])
        plan_details = get_workout_plan_details(plan_id)
        
        if plan_details:
            plan_name = "Ваш план"
            user_plans = get_user_workout_plans(callback.from_user.id)
            for p_id, p_name in user_plans:
                if p_id == plan_id:
                    plan_name = p_name
                    break

            details_text = f"🏋️‍♂️ **План тренировок: {plan_name}**\n\n"
            for exercise_name, sets, reps in plan_details:
                details_text += f"  - {exercise_name}: {sets}x{reps}\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад к планам", callback_data="back_to_plans_from_view")]])
            await callback.message.edit_text(details_text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await callback.message.edit_text("В этом плане пока нет упражнений.")
        await callback.answer()

    elif action == 'delete':
        plan_id = int(action_parts[2])
        delete_workout_plan(plan_id)
        
        user_plans = get_user_workout_plans(callback.from_user.id)
        if not user_plans:
            await callback.message.edit_text("План удален. У вас больше нет планов.\n\nЧтобы создать новый, введите команду /plan или нажмите '📝 Планирование'.", reply_markup=None)
        else:
            keyboard_buttons = []
            for p_id, p_name in user_plans:
                keyboard_buttons.append([
                    InlineKeyboardButton(text=f"📝 {p_name}", callback_data=f"view_plan_{p_id}"),
                    InlineKeyboardButton(text="✏️", callback_data=f"edit_plan_{p_id}"),
                    InlineKeyboardButton(text="🗑️", callback_data=f"delete_plan_{p_id}")
                ])
            keyboard_buttons.append([InlineKeyboardButton(text="➕ Создать новый план", callback_data="create_new_plan")])
            plans_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await callback.message.edit_text("План удален. Ваши планы тренировок:", reply_markup=plans_keyboard)
        await callback.answer()

    elif action == 'create':
        await callback.message.edit_text("Введите название для вашего нового плана тренировок:")
        await state.set_state(PlanCreationStates.waiting_for_plan_name)
        await callback.answer()
        
    elif action == 'edit':
        plan_id = int(action_parts[2])
        await state.update_data(editing_plan_id=plan_id)
        await callback.message.edit_text("Что вы хотите сделать с планом?", reply_markup=get_edit_plan_menu_keyboard(plan_id))
        await state.set_state(PlanEditingStates.waiting_for_edit_action)
        await callback.answer()


async def handle_edit_plan_action(callback: types.CallbackQuery, state: FSMContext):
    action_parts = callback.data.split('_')
    action = action_parts[0]
    
    if action == 'back':
        await state.clear()
        user_plans = get_user_workout_plans(callback.from_user.id)
        keyboard_buttons = []
        if user_plans:
            for p_id, p_name in user_plans:
                keyboard_buttons.append([
                    InlineKeyboardButton(text=f"📝 {p_name}", callback_data=f"view_plan_{p_id}"),
                    InlineKeyboardButton(text="✏️", callback_data=f"edit_plan_{p_id}"),
                    InlineKeyboardButton(text="🗑️", callback_data=f"delete_plan_{p_id}")
                ])
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Создать новый план", callback_data="create_new_plan")])
        plans_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text("Ваши планы тренировок:", reply_markup=plans_keyboard)
        await callback.answer()
        return

    plan_id = int(action_parts[-1])
    await state.update_data(current_plan_id=plan_id)

    if action == 'rename':
        await callback.message.edit_text("Введите новое название для плана:")
        await state.set_state(PlanEditingStates.renaming_plan)
    elif action == 'add':
        await state.update_data(is_editing=True)
        await callback.message.edit_text("Выберите группу мышц, чтобы добавить упражнение:", reply_markup=muscle_group_keyboard)
        await state.set_state(PlanCreationStates.waiting_for_muscle_group)
    elif action == 'remove':
        conn = sqlite3.connect('fitness_bot.db')
        cur = conn.cursor()
        cur.execute("SELECT E.exercise_id, E.name FROM WorkoutPlanExercises WPE JOIN Exercises E ON WPE.exercise_id = E.exercise_id WHERE WPE.plan_id = ?", (plan_id,))
        exercises_in_plan = cur.fetchall()
        conn.close()

        if not exercises_in_plan:
            await callback.message.edit_text("В этом плане нет упражнений для удаления.", reply_markup=get_edit_plan_menu_keyboard(plan_id))
            await state.set_state(PlanEditingStates.waiting_for_edit_action)
            await callback.answer()
            return
        
        keyboard_buttons = []
        for ex_id, ex_name in exercises_in_plan:
            keyboard_buttons.append([InlineKeyboardButton(text=f"➖ {ex_name}", callback_data=f"del_ex_from_plan_{plan_id}_{ex_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data=f"edit_plan_{plan_id}")])
        
        remove_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text("Выберите упражнение для удаления:", reply_markup=remove_keyboard)
        await state.set_state(PlanEditingStates.removing_exercise)

    await callback.answer()

async def process_plan_rename(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название не может быть пустым. Введите другое:")
        return
    
    if workout_plan_exists(message.from_user.id, new_name):
        await message.answer("План с таким названием уже существует. Пожалуйста, введите другое название:")
        return

    data = await state.get_data()
    plan_id = data.get('current_plan_id')
    
    if plan_id:
        update_plan_name(plan_id, new_name)
        await message.answer(f"План переименован в '{new_name}'.")
        await state.clear()
        await cmd_plan(message, state)
    else:
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.clear()

async def handle_remove_exercise_from_plan(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    plan_id = int(parts[4])
    exercise_id = int(parts[5])

    remove_exercise_from_plan(plan_id, exercise_id)
    
    await callback.message.edit_text("Упражнение удалено из плана.", reply_markup=get_edit_plan_menu_keyboard(plan_id))
    await state.set_state(PlanEditingStates.waiting_for_edit_action)
    await callback.answer()

async def handle_edit_field_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'back_to_profile':
        await state.clear()
        await callback.message.delete()
        await cmd_profile(callback.message, state)
        await callback.answer()
        return

    field = callback.data.split('_field_')[1]
    
    prompts = {
        'weight': ("Введите новый вес в кг:", ProfileEditingStates.editing_weight),
        'height': ("Введите новый рост в см:", ProfileEditingStates.editing_height),
        'age': ("Введите новый возраст:", ProfileEditingStates.editing_age),
        'gender': ("Выберите новый пол:", ProfileEditingStates.editing_gender),
        'activity': ("Выберите новый уровень активности:", ProfileEditingStates.editing_activity),
        'target': ("Выберите новую цель:", ProfileEditingStates.editing_target)
    }
    
    prompt_text, new_state = prompts[field]
    
    reply_markup = None
    if field == 'gender':
        reply_markup = gender_keyboard
    elif field == 'activity':
        reply_markup = activity_level_keyboard
    elif field == 'target':
        reply_markup = target_keyboard

    await callback.message.answer(prompt_text, reply_markup=reply_markup)
    await state.set_state(new_state)
    await callback.answer()