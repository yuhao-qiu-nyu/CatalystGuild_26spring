import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel
import plotly.express as px
from PIL import Image
import json
import os
import random

# --- Basic Configuration ---
MAX_ROUNDS = 10
st.set_page_config(page_title="Evolution: The Filter of Time", layout="wide", page_icon="🧬")

class Traits(BaseModel):
    body_size: int
    feather_density: int
    metabolism: int
    flight_ability: int
    habitat: int
    health: int
    adaptability: int

class EvolutionResult(BaseModel):
    narrative: str
    traits: Traits

# --- Helper Functions ---

def get_image(filename):
    try:
        if filename and os.path.exists(filename):
            return Image.open(filename)
    except Exception as e:
        st.error(f"Image Load Error ({filename}): {e}")
    return None

def get_evolution_stage_image(history, current_round, system_choice):
    """Matches images based on your specific round logic."""
    default_img = "OG.png"
    if not history:
        return default_img
    
    state = history[-1]
    
    # --- PHASE 1: Initial Morphology (Rounds 0-1) ---
    # Show Case A (1.0) as the base form for the first two generations
    if current_round <= 1:
        mapping = {
            "Warming Weather": "#1Case A",
            "Cooling Weather": "#2Case A",
            "Dry Environment": "#3Case A",
            "Forest System": "#4Case A"
        }
        prefix = mapping.get(system_choice, "OG")
        try:
            for f in os.listdir('.'):
                if f.startswith(prefix) and ("（1.0）" in f or "(1.0)" in f):
                    return f
        except: pass
        return default_img

    # --- PHASE 2: Branch Detection & Version Control (Rounds 2-10) ---
    oxy = state.get('Oxygen', 50)
    food = state.get('Food', 50)
    pred = state.get('Predation', 50)
    temp = state.get('Temperature', 50)
    water = state.get('Water', 50)
    nocturnal = state.get('Nocturnal_Shift', False)
    special_diet = state.get('Specialized_Diet', False)
    camo = state.get('Camouflage_Focus', False)
    hab_type = state.get('Habitat_Type', 'Ground-Dwelling')

    # Logic to detect Branch (A or B)
    case_prefix = ""
    if oxy > 70 and food > 70 and pred < 30: case_prefix = "#1Case A"
    elif temp > 70 and food < 40 and pred > 70: case_prefix = "#1Case B"
    elif temp < 30 and food > 60: case_prefix = "#2Case A"
    elif temp < 40 and food < 40: case_prefix = "#2Case B"
    elif water < 30 and temp > 70 and pred > 60 and nocturnal: case_prefix = "#3Case A"
    elif water < 50 and pred < 40 and special_diet: case_prefix = "#3Case B"
    elif hab_type == 'Dense Forest' and food > 60 and pred > 70: case_prefix = "#4Case A"
    elif hab_type == 'Dense Forest' and pred < 40 and camo: case_prefix = "#4Case B"
    
    if not case_prefix: return default_img

    # --- NEW ROUND LOGIC ---
    # Round 2-3: Show 1.0
    # Round 4-6: Show 2.0
    # Round 7-9: Show 3.0
    # Round 10: Show 4.0
    v_num = ""
    if current_round >= 10: v_num = "4.0"
    elif current_round >= 7: v_num = "3.0"
    elif current_round >= 4: v_num = "2.0"
    else: v_num = "1.0"
    
    try:
        variants = [f"（{v_num}）", f"({v_num})"]
        for f in os.listdir('.'):
            if f.startswith(case_prefix) and any(v in f for v in variants):
                return f
    except: pass
    return default_img

# --- Manual Simulation Engine ---

def run_manual_simulation(current_state, env_vars):
    new_traits = current_state.copy()
    if env_vars['Oxygen'] > 75: new_traits['Body Size'] += 7
    elif env_vars['Food'] < 30: new_traits['Body Size'] -= 5
    if env_vars['Temperature'] < 35: new_traits['Feather Density'] += 8
    elif env_vars['Temperature'] > 80: new_traits['Feather Density'] -= 8
    if env_vars['Temperature'] > 70 or env_vars['Predation'] > 60: new_traits['Metabolism'] += 5
    if env_vars['Habitat_Type'] == 'Dense Forest' and env_vars['Predation'] > 50: new_traits['Flight Ability'] += 6
    if env_vars['Habitat_Type'] == 'Open Plains': new_traits['Habitat'] -= 4
    if env_vars['Water'] < 25 or env_vars['Food'] < 25 or env_vars['Temperature'] > 90: new_traits['Health'] -= 15
    else: new_traits['Health'] += 2
    if env_vars['Nocturnal_Shift'] or env_vars['Camouflage_Focus']: new_traits['Adaptability'] += 5
    
    for k in ['Body Size', 'Feather Density', 'Metabolism', 'Flight Ability', 'Habitat', 'Health', 'Adaptability']:
        new_traits[k] = max(0, min(100, int(new_traits[k])))
    
    narrative = f"Manual Simulation: The species is adapting to {env_vars['Habitat_Type']} conditions."
    return narrative, new_traits

def simulate_round(env_vars):
    current_state = st.session_state.history[-1]
    if st.session_state.api_key and len(st.session_state.api_key) > 10:
        client = genai.Client(api_key=st.session_state.api_key)
        prompt = f"Round {st.session_state.round + 1}. Env: {env_vars}. Current state: {current_state}."
        try:
            with st.spinner("🧬 AI Mentor analyzing..."):
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=EvolutionResult),
                )
                result = json.loads(response.text)
                t = result['traits']
                new_state = {
                    'round': st.session_state.round + 1,
                    'Body Size': t['body_size'], 'Feather Density': t['feather_density'],
                    'Metabolism': t['metabolism'], 'Flight Ability': t['flight_ability'],
                    'Habitat': t['habitat'], 'Health': t['health'], 'Adaptability': t['adaptability'],
                    **env_vars, 'Narrative': result['narrative']
                }
        except:
            narr, nt = run_manual_simulation(current_state, env_vars)
            new_state = {**nt, **env_vars, 'round': st.session_state.round + 1, 'Narrative': narr}
    else:
        narr, nt = run_manual_simulation(current_state, env_vars)
        new_state = {**nt, **env_vars, 'round': st.session_state.round + 1, 'Narrative': narr}

    st.session_state.history.append(new_state)
    st.session_state.round += 1
    if new_state['Health'] <= 0 or st.session_state.round >= MAX_ROUNDS:
        st.session_state.game_over = True

# --- UI Setup ---

if 'phase' not in st.session_state: st.session_state.phase = 'selection'
if 'round' not in st.session_state: st.session_state.round = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'game_over' not in st.session_state: st.session_state.game_over = False
if 'api_key' not in st.session_state: st.session_state.api_key = ''
if 'system_choice' not in st.session_state: st.session_state.system_choice = ''

if st.session_state.phase == 'selection':
    st.title("🧬 Evolution: The Filter of Time")
    img = get_image("System Selection.png")
    if img: st.image(img, use_container_width=True)
    st.markdown("### Select Your Starting System")
    cols = st.columns(4)
    envs = [
        ("Warming Weather", {'Temperature': 65, 'Oxygen': 90, 'Water': 75, 'Food': 85, 'Predation': 35}),
        ("Cooling Weather", {'Temperature': 15, 'Oxygen': 55, 'Water': 40, 'Food': 40, 'Predation': 30}),
        ("Dry Environment", {'Temperature': 85, 'Oxygen': 45, 'Water': 10, 'Food': 35, 'Predation': 60}),
        ("Forest System", {'Temperature': 60, 'Oxygen': 75, 'Water': 80, 'Food': 90, 'Predation': 80})
    ]
    for i, (name, mods) in enumerate(envs):
        if cols[i].button(name, use_container_width=True):
            st.session_state.phase = 'simulation'
            st.session_state.system_choice = name
            st.session_state.history = [{
                'round': 0, 'Body Size': 20, 'Feather Density': 50, 'Metabolism': 40, 
                'Flight Ability': 10, 'Habitat': 90, 'Health': 100, 'Adaptability': 100,
                **mods, 'Narrative': f"Evolution begins in the {name}.",
                'Habitat_Type': 'Ground-Dwelling', 'Nocturnal_Shift': False, 'Specialized_Diet': False, 'Camouflage_Focus': False
            }]
            st.rerun()

elif st.session_state.phase == 'simulation':
    with st.sidebar:
        st.header("⚙️ Config")
        st.session_state.api_key = st.text_input("Gemini API Key", type="password", value=st.session_state.api_key)
        if st.button("🔄 Restart"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.title(f"🐣 Generation {st.session_state.round} ({st.session_state.system_choice})")
    
    # Image Display
    img_name = get_evolution_stage_image(st.session_state.history, st.session_state.round, st.session_state.system_choice)
    display_img = get_image(img_name)
    if display_img:
        st.image(display_img, caption=f"Current Morphology: {img_name}", use_container_width=True)
    
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("🌍 Environment")
            curr = st.session_state.history[-1]
            t = st.slider("Temperature", 0, 100, int(curr['Temperature']))
            o = st.slider("Oxygen", 0, 100, int(curr['Oxygen']))
            w = st.slider("Water", 0, 100, int(curr['Water']))
            f = st.slider("Food", 0, 100, int(curr['Food']))
            p = st.slider("Predation", 0, 100, int(curr['Predation']))
            st.write("---")
            h_type = st.selectbox("Biome", ["Ground-Dwelling", "Dense Forest", "Open Plains"])
            n_on = st.checkbox("Nocturnal Shift", value=curr.get('Nocturnal_Shift', False))
            d_on = st.checkbox("Specialized Diet", value=curr.get('Specialized_Diet', False))
            c_on = st.checkbox("Camouflage Focus", value=curr.get('Camouflage_Focus', False))
            
            if not st.session_state.game_over:
                if st.button("🧬 Simulate Next Round", type="primary", use_container_width=True):
                    simulate_round({'Temperature': t, 'Oxygen': o, 'Water': w, 'Food': f, 'Predation': p,
                                    'Habitat_Type': h_type, 'Nocturnal_Shift': n_on, 
                                    'Specialized_Diet': d_on, 'Camouflage_Focus': c_on})
                    st.rerun()
            else:
                st.warning("🚨 Evolution Halted.")

    with col2:
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            st.plotly_chart(px.line(df, x='round', y=['Body Size', 'Feather Density', 'Metabolism', 'Flight Ability', 'Health', 'Adaptability']), use_container_width=True)
            with st.chat_message("assistant", avatar="🧬"):
                st.markdown(st.session_state.history[-1]['Narrative'])
