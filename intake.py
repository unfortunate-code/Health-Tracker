import os
import pickle as pkl
from datetime import datetime

import pytz
import streamlit as st
from filelock import FileLock
from streamlit_modal import Modal

# streamlit run intake.py --server.headless=true --server.port=9000 --theme.base=dark

est = pytz.timezone("US/Eastern")

st.set_page_config(page_title="Health Tracker")

if "intake" not in st.session_state:
    with FileLock("intake.pkl.lock"):
        if os.path.exists("intake.pkl"):
            with open("intake.pkl", "rb") as f:
                st.session_state.intake = pkl.load(f)
        else:
            st.session_state.intake = {}

st.title("Health tracker")

remove_entries_modal = Modal(
    "Remove Entries", key="remove_entries_modal", padding=20, max_width=744
)

plot_modal = Modal("Plot", key="plot_modal", padding=20, max_width=744)


def summary():
    today = datetime.now(est).date()
    calories = sum(
        [entry[1] for entry in st.session_state.intake.get(today, {}).get("food", [])]
    )
    st.markdown(
        f"<div style='background-color: #333; padding: 3px 5px;'><b>{st.session_state.intake.get(today, {}).get('sleep', 0)}</b> hours of <b>sleep</b> today</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='background-color: #333; padding: 3px 5px;'><b>{st.session_state.intake.get(today, {}).get('water', 0)}</b> ml of <b>water</b> today</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='background-color: #333; padding: 3px 5px; margin-bottom: 10px;'><b>{calories}</b> <b>calories</b> today</div>",
        unsafe_allow_html=True,
    )


summary()

input_option = st.selectbox(
    "What would you like to update?",
    ("", "Sleep", "Food", "Water"),
    key="input_option",
    index=0,
)


def clear():
    st.session_state.input_option = ""
    st.session_state.food_entries_count = 1
    with FileLock("intake.pkl.lock"):
        with open("intake.pkl", "wb") as f:
            pkl.dump(st.session_state.intake, f)


if input_option == "Sleep":
    st.write("How many hours of sleep did you get last night?")
    sleep = st.number_input("Hours of sleep", 0, 24, 0)

    def submit():
        today = datetime.now(est).date()
        if today in st.session_state.intake:
            st.session_state.intake[today]["sleep"] = (
                st.session_state.intake[today].get("sleep", 0) + sleep
            )
        else:
            st.session_state.intake[today] = {"sleep": sleep}
        clear()

    st.button("Submit", on_click=submit)

elif input_option == "Food":
    st.write("What did you eat today?")
    if "food_entries_count" not in st.session_state:
        st.session_state.food_entries_count = 1
    foods = []
    calories = []
    for i in range(st.session_state.food_entries_count):
        col1, col2 = st.columns([1, 1])
        with col1:
            foods.append(st.text_input("Food", "", key=f"food_{i}"))
        with col2:
            calories.append(
                st.number_input("Calories", 0, 10000, 0, key=f"calories_{i}")
            )

    def add_food_entry():
        st.session_state.food_entries_count += 1

    st.button("Add Another", on_click=add_food_entry)

    def submit():
        today = datetime.now(est).date()
        if today in st.session_state.intake:
            st.session_state.intake[today]["food"] = st.session_state.intake[today].get(
                "food", []
            ) + list(zip(foods, calories))
        else:
            st.session_state.intake[today] = {"food": list(zip(foods, calories))}
        clear()

    st.button("Submit", on_click=submit)

elif input_option == "Water":
    st.write("How many ml of water did you drink today?")
    water = st.number_input("Water", 0, 10000, 0)

    def submit():
        today = datetime.now(est).date()
        if today in st.session_state.intake:
            st.session_state.intake[today]["water"] = (
                st.session_state.intake[today].get("water", 0) + water
            )
        else:
            st.session_state.intake[today] = {"water": water}
        clear()

    st.button("Submit", on_click=submit)


def delete_entries():
    today = datetime.now(est).date()
    food_indices_to_remove = []
    for key in st.session_state:
        if key.startswith("r_") and st.session_state[key]:
            if key == "r_sleep":
                st.session_state.intake[today].pop("sleep", None)
            elif key == "r_water":
                st.session_state.intake[today].pop("water", None)
            elif key.startswith("r_food"):
                i = int(key.split("_")[-1])
                food_indices_to_remove.append(i)
    st.session_state.intake[today]["food"] = [
        entry
        for i, entry in enumerate(st.session_state.intake[today].get("food", []))
        if i not in food_indices_to_remove
    ]
    clear()


if remove_entries_modal.is_open():
    with remove_entries_modal.container():
        todays_intake = st.session_state.intake.get(datetime.now(est).date(), {})
        have_data_to_remove = False
        if "sleep" in todays_intake:
            have_data_to_remove = True
            st.checkbox(f"Sleep of {todays_intake['sleep']} hours", key="r_sleep")
        if "water" in todays_intake:
            have_data_to_remove = True
            st.checkbox(f"Water of {todays_intake['water']} ml", key="r_water")
        if "food" in todays_intake:
            if len(todays_intake["food"]) > 0:
                have_data_to_remove = True
            for i, (food, calories) in enumerate(todays_intake["food"]):
                st.checkbox(f"{food} ({calories} calories)", key=f"r_food_{i}")
        if have_data_to_remove:
            st.button("Remove Selected", on_click=delete_entries)
        else:
            st.write("No data to remove")

st.button("Remove entries", on_click=remove_entries_modal.open)

if plot_modal.is_open():
    with plot_modal.container():
        no_plots = True
        water_data = [
            (date, intake.get("water", 0))
            for date, intake in st.session_state.intake.items()
        ]
        if sum([entry[1] for entry in water_data]) > 0:
            no_plots = False
            st.write("Water intake plot")
            water_data.sort(key=lambda x: x[0])
            st.scatter_chart(water_data)
        sleep_data = [
            (date, intake.get("sleep", 0))
            for date, intake in st.session_state.intake.items()
        ]
        if sum([entry[1] for entry in sleep_data]) > 0:
            no_plots = False
            st.write("Sleep plot")
            sleep_data.sort(key=lambda x: x[0])
            st.scatter_chart(sleep_data)
        calories_data = [
            (date, sum([entry[1] for entry in intake.get("food", [])]))
            for date, intake in st.session_state.intake.items()
        ]
        if sum([entry[1] for entry in calories_data]) > 0:
            no_plots = False
            st.write("Calories plot")
            calories_data.sort(key=lambda x: x[0])
            st.scatter_chart(calories_data)
        if no_plots:
            st.write("No data to plot")


st.button("Plot data", on_click=plot_modal.open)
