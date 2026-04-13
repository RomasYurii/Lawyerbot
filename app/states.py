from aiogram.fsm.state import State, StatesGroup

class ClientState(StatesGroup):
    gathering_question = State() # Клієнт пише питання і кидає файли

class LawyerState(StatesGroup):
    replying = State() # Юрист пише відповідь