"""OutsideQuest — a local-first AI adventure companion."""

from __future__ import annotations

import streamlit as st

from outsidequest.adventure import GenerationResult, generate_adventure
from outsidequest.deployment import is_public_mode
from outsidequest.models import Mission, MissionValidationError, Preferences, validate_preferences
from outsidequest.storage import (
    DEFAULT_DATA_PATH,
    StorageError,
    add_journal_entry,
    complete_mission,
    load_data,
)

st.set_page_config(
    page_title="OutsideQuest — Your AI Adventure Buddy",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --ink: #17352c; --muted: #557166; --leaf: #2c7254; --mint: #e9f3eb; --cream: #f8f7f0; }
    .stApp { background: radial-gradient(ellipse at 12% 0%, #e4f1e6 0%, transparent 35%), #f8f8f3; color: var(--ink); }
    html, body, [class*="css"] { font-family: 'Segoe UI', Arial, sans-serif; }
    h1, h2, h3 { font-family: 'Segoe UI', Arial, sans-serif !important; color: var(--ink) !important; letter-spacing: -0.035em; }
    .hero { padding: 2.3rem 2.5rem; border-radius: 28px; color: #f7fbf5; background: linear-gradient(120deg, #173c31, #286748 60%, #74a66e); box-shadow: 0 16px 44px #183f3020; margin-bottom: 1.4rem; }
    .hero h1 { color: #fff !important; font-size: clamp(2.4rem, 5vw, 4.2rem) !important; margin: .25rem 0 .3rem; }
    .hero p { color: #e2f0e2; font-size: 1.08rem; max-width: 700px; margin: 0; }
    .eyebrow { text-transform: uppercase; letter-spacing: .15em; font-size: .74rem; font-weight: 700; color: #d3ead2; }
    .panel { border: 1px solid #e4e9df; background: #ffffffd9; border-radius: 22px; padding: 1.35rem 1.5rem; box-shadow: 0 8px 30px #2343300a; }
    .mission-card { border: 1px solid #dce8dc; background: linear-gradient(145deg, #fff, #f2f7ef); border-radius: 24px; padding: 1.6rem 1.8rem; box-shadow: 0 12px 32px #23433012; }
    .tag { display: inline-block; border-radius: 99px; background: #e7f1e8; color: #286047; padding: .35rem .7rem; font-size: .82rem; font-weight: 700; margin-right: .35rem; }
    section[data-testid="stSidebar"] { background: #f0f4ed; border-right: 1px solid #e2e9df; }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] :is(h1, h2, h3, p, span, label, li, div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"], div[data-testid="stMarkdownContainer"]) { color: var(--ink); }
    section[data-testid="stSidebar"] :is([data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] *) { color: var(--muted) !important; }
    section[data-testid="stSidebar"] div[data-testid="stProgress"] > div > div { background-color: #d5e4d6; }
    section[data-testid="stSidebar"] div[data-testid="stProgress"] > div > div > div { background-color: var(--leaf); }
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primaryFormSubmit"] {
      background-color: #2c7254 !important;
      border-color: #2c7254 !important;
      color: #fff !important;
    }
    button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
      background-color: #225c43 !important;
      border-color: #225c43 !important;
    }
    div.stButton > button { border-radius: 12px; }
    div[data-testid="stForm"] { border: 1px solid #e4e9df; border-radius: 20px; padding: 1.2rem; background: #ffffffc9; }
    @media (max-width: 700px) { .hero { padding: 1.5rem; border-radius: 20px; } .mission-card { padding: 1.25rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)

PUBLIC_MODE = is_public_mode()

if PUBLIC_MODE:
    # Never touch the shared JSON file on a public host: it would mix visitors' data.
    progress_data = {"completed_missions": [], "journal_entries": []}
else:
    try:
        progress_data = load_data()
    except StorageError as exc:
        st.error(f"Your local progress could not be loaded. {exc}")
        st.stop()

completed = progress_data["completed_missions"]
journal_entries = progress_data["journal_entries"]

with st.sidebar:
    st.markdown("## 🌱 Your journey")
    st.caption("Small adventures add up.")
    if PUBLIC_MODE:
        st.info(
            "Progress and reflections are turned off in this public demo so no one's "
            "personal notes are stored or shared. Run OutsideQuest locally to keep a private journey."
        )
    else:
        st.metric("Adventures completed", len(completed))
        st.metric("Reflections saved", len(journal_entries))
        next_goal = 5
        st.progress(min(len(completed) / next_goal, 1.0))
        st.caption(f"{max(next_goal - len(completed), 0)} until your next 5-adventure milestone")
        st.divider()
        st.markdown("**Your recent adventures**")
        if completed:
            for entry in reversed(completed[-4:]):
                st.markdown(f"✓ {entry.get('title', 'Completed mission')}")
        else:
            st.caption("Your first quest is waiting.")
        st.divider()
        st.caption("🔒 Your history stays in a local JSON file on this device.")

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">A little less scrolling. A little more living.</div>
      <h1>OutsideQuest</h1>
      <p>Your AI adventure buddy turns the time, energy, and curiosity you have today
      into one doable, feel-good mission. No perfect plans required.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

intro_left, intro_right = st.columns([1.5, 1], vertical_alignment="center")
with intro_left:
    st.markdown("### Your next good story starts small.")
    st.write("Tell us what today looks like. We’ll make you a practical mission that fits.")
with intro_right:
    first_tag = "Built-in demo missions" if PUBLIC_MODE else "Local AI"
    st.markdown(
        f'<div class="panel"><span class="tag">{first_tag}</span><span class="tag">No API keys</span>'
        '<span class="tag">Your pace</span><p style="color:#557166;margin:.8rem 0 0">'
        "Made for real life: free and low-energy options count, too.</p></div>",
        unsafe_allow_html=True,
    )

st.markdown("## 🎒 Set your adventure")
with st.form("adventure_preferences"):
    left, right = st.columns(2)
    with left:
        available_minutes = st.slider("How much time do you have?", 5, 240, 30, 5, format="%d min")
        energy_level = st.select_slider("Your energy today", options=["Low", "Medium", "High"], value="Medium")
        activity_type = st.radio("Where would you like to adventure?", ["Outside", "Inside", "Either"], horizontal=True)
    with right:
        selected_interests = st.multiselect(
            "What sounds interesting?",
            ["Nature", "Creativity", "Movement", "Food", "Learning", "Photography", "Mindfulness", "Local culture"],
            default=["Nature"],
        )
        custom_interest = st.text_input("Add your own interest (optional)", max_chars=60, placeholder="e.g. sketching")
        budget = st.number_input("Maximum spend (in your local currency)", min_value=0.0, max_value=10000.0, value=0.0, step=5.0)
    submitted = st.form_submit_button("✨ Find my adventure", type="primary", use_container_width=True)

if submitted:
    interests = [*selected_interests]
    if custom_interest.strip():
        interests.append(custom_interest.strip())
    try:
        preferences = validate_preferences(
            available_minutes, energy_level, interests, budget, activity_type
        )
    except MissionValidationError as exc:
        st.error(str(exc))
    else:
        st.session_state["last_preferences"] = preferences.to_dict()
        variant = st.session_state.get("generation_count", 0)
        with st.spinner("Finding an adventure that fits your day…"):
            result = generate_adventure(preferences, fallback_variant=variant)
        st.session_state["generation_count"] = variant + 1
        st.session_state["current_result"] = {
            "mission": result.mission.to_dict(),
            "source": result.source,
            "notice": result.notice,
        }

if st.session_state.get("current_result"):
    result_data = st.session_state["current_result"]
    mission = Mission(**result_data["mission"])
    st.markdown("---")
    st.markdown("## ✨ Your mission")
    if result_data["source"] == "ollama":
        if PUBLIC_MODE:
            st.success("Created with the Ollama model configured for this deployment.")
        else:
            st.success("Created locally with your Ollama model. Your preferences were not sent to a cloud AI service.")
    else:
        st.info("🌿 Built-in fallback mission — this is not AI-generated content.")
        if result_data.get("notice"):
            st.caption(f"Why fallback was used: {result_data['notice']}")

    st.markdown('<div class="mission-card">', unsafe_allow_html=True)
    st.markdown(f"### {mission.title}")
    st.write(mission.reason)
    tag_col1, tag_col2 = st.columns(2)
    tag_col1.markdown(f'<span class="tag">⏱ {mission.duration_minutes} min</span>', unsafe_allow_html=True)
    tag_col2.markdown(f'<span class="tag">💸 {mission.estimated_cost:g} estimated cost</span>', unsafe_allow_html=True)
    st.markdown("**Your steps**")
    for index, step in enumerate(mission.steps, start=1):
        st.markdown(f"{index}. {step}")
    st.info(f"🛡️ **Safety first:** {mission.safety_tip}")
    st.markdown("</div>", unsafe_allow_html=True)

    action_col, refresh_col = st.columns([1, 1])
    already_completed = any(entry.get("id") == mission.id for entry in completed)
    with action_col:
        if already_completed:
            st.success("Mission completed — nicely done!")
        elif PUBLIC_MODE:
            st.caption("Completion tracking is available when you run OutsideQuest locally.")
        elif st.button("✅ I completed this mission", type="primary", use_container_width=True):
            try:
                progress_data = complete_mission(mission)
            except StorageError as exc:
                st.error(f"Your mission is not marked complete because local saving failed. {exc}")
            else:
                st.session_state["current_result"]["completed"] = True
                st.rerun()
    with refresh_col:
        if st.button("🔄 Give me another mission", use_container_width=True):
            preference_data = st.session_state.get("last_preferences")
            if preference_data:
                preferences = Preferences(**preference_data)
                variant = st.session_state.get("generation_count", 0)
                with st.spinner("Dreaming up another safe, doable option…"):
                    refreshed: GenerationResult = generate_adventure(
                        preferences, fallback_variant=variant
                    )
                st.session_state["generation_count"] = variant + 1
                st.session_state["current_result"] = {
                    "mission": refreshed.mission.to_dict(),
                    "source": refreshed.source,
                    "notice": refreshed.notice,
                }
                st.rerun()

if PUBLIC_MODE:
    st.markdown("---")
    st.markdown("## 📓 Reflection journal")
    st.info(
        "The journal is disabled in this public demo because reflections are personal and "
        "this deployment has no per-user storage. Run OutsideQuest locally to keep a private journal."
    )
else:
    st.markdown("---")
    st.markdown("## 📓 Your reflection journal")
    st.write("Keep a little memory of how it felt. A sentence is plenty.")
    completed_titles = [entry.get("title", "Completed adventure") for entry in completed]
    with st.form("journal_entry"):
        associated_mission = st.selectbox(
            "Connect this reflection to an adventure (optional)",
            ["Just a reflection", *completed_titles],
        )
        reflection = st.text_area(
            "What did you notice, enjoy, or want to remember?",
            max_chars=2000,
            placeholder="A small thing that made today feel different…",
        )
        save_reflection = st.form_submit_button("Save reflection", use_container_width=True)

    if save_reflection:
        if not reflection.strip():
            st.error("Write a few words before saving your reflection.")
        else:
            try:
                progress_data = add_journal_entry(
                    reflection,
                    None if associated_mission == "Just a reflection" else associated_mission,
                )
            except StorageError as exc:
                st.error(f"Your reflection was not saved. {exc}")
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["journal_saved"] = True
                st.rerun()

    if st.session_state.pop("journal_saved", False):
        st.success("Reflection saved on this device.")

    if journal_entries:
        with st.expander(f"Read your reflections ({len(journal_entries)})"):
            for entry in reversed(journal_entries):
                st.markdown(f"**{entry.get('mission_title') or 'A reflection'}**")
                st.write(entry.get("text", ""))
                st.caption(entry.get("created_at", "")[:10])
                st.divider()

    st.caption(f"Progress is stored locally at `{DEFAULT_DATA_PATH}`. Keep this file private; it is excluded from Git.")
