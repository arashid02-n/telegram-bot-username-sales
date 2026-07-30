# FSM state definitions

from aiogram.fsm.state import State, StatesGroup

class BidStates(StatesGroup):
    waiting_for_bid = State()
    waiting_for_contact = State()