from aiogram.fsm.state import StatesGroup, State

class RegistrationStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_activity_level = State()
    waiting_for_target = State()

class PlanCreationStates(StatesGroup):
    waiting_for_plan_name = State()
    waiting_for_plan_muscle_group = State()
    waiting_for_muscle_group = State()
    waiting_for_exercise_selection = State()
    waiting_for_add_more_exercises = State()

class LogProgressStates(StatesGroup):
    waiting_for_plan_selection = State()
    waiting_for_exercise_selection = State()
    waiting_for_log_details = State()

class ViewProgressStates(StatesGroup):
    waiting_for_plan_selection = State()
    waiting_for_exercise_selection = State()

class PlanEditingStates(StatesGroup):
    waiting_for_edit_action = State()
    renaming_plan = State()
    removing_exercise = State()

class ProfileEditingStates(StatesGroup):
    editing_weight = State()
    editing_height = State()
    editing_age = State()
    editing_gender = State()
    editing_activity = State()
    editing_target = State()