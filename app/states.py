from aiogram.fsm.state import State, StatesGroup

class ClientState(StatesGroup):
    gathering_question = State()

class LawyerState(StatesGroup):
    replying = State()