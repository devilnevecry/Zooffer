from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    consent = State()
    name = State()


class ListingWizard(StatesGroup):
    species = State()
    sex = State()
    name = State()
    birth = State()
    city = State()
    purpose = State()
    title = State()
    description = State()
    price = State()
    photos = State()
    confirm = State()


class ChatFlow(StatesGroup):
    writing = State()


class LinkFlow(StatesGroup):
    confirm = State()


class SupportFlow(StatesGroup):
    subject = State()
    message = State()
