# Exports a master router combining all handler routers

from aiogram import Router

# Import the individual routers you just created
from handlers.commands import router as commands_router
from handlers.bidding import router as bidding_router
from handlers.callbacks import router as callbacks_router
from handlers.negotiation import router as negotiation_router

# Create a master router to hold them all
main_router = Router()

# Attach the sub-routers to the master router
main_router.include_router(negotiation_router)
main_router.include_router(commands_router)
main_router.include_router(bidding_router)
main_router.include_router(callbacks_router)