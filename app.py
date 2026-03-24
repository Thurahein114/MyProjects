import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Page setup
st.set_page_config(page_title="CMHL Posting Guide", layout="centered")

st.title("🛒 CMHL Content Decision Tool")
st.caption("Keep every post calm, clear, and customer-first")

st.warning("⚠️ Use this tool before posting any content during sensitive periods")

# Context selection
mode = st.radio("Select Context", ["Normal", "Sensitive Period (Thingyan / Crisis)"])

st.divider()

# Post input
post_name = st.text_area(
    "📝 Enter Post Caption / Name (Max 500 characters)",
    max_chars=500,
    placeholder="Type your post caption here..."
)

st.subheader("📝 Quick Evaluation")

# Checklist inputs
data = {
    "sensitivity": st.checkbox("⚠️ This post might feel tone-deaf or too celebratory"),
    "customer_value": st.checkbox("✅ This post helps customers (inform / guide / ease shopping)"),
    "clarity": st.checkbox("✅ Message is clear within 5 seconds"),
    "reassurance": st.checkbox("✅ Adds reassurance (stores open, availability, etc.)"),
    "relevance": st.checkbox("✅ Relevant to current situation"),
    "tone_balance": st.checkbox("✅ Tone is gentle (not overly festive)"),
    "actionability": st.checkbox("✅ Tells customers what to do"),
    "risk_trigger": st.checkbox("⚠️ Might cause panic or confusion"),
    "aggressive_promo": st.checkbox("⚠️ Feels too promotional or pushy")
}

# Evaluation logic
def evaluate_post(data, mode):
    score = 0

    risk_penalty = -3 if mode == "Sensitive Period (Thingyan / Crisis)" else -2

    # Negative factors
    score += risk_penalty if data["sensitivity"] else 1
    score += risk_penalty if data["risk_trigger"] else 1
    score += risk_penalty if data["aggressive_promo"] else 1

    # Positive factors
    positives = [
        "customer_value",
        "clarity",
        "reassurance",
        "relevance",
        "tone_balance",
        "actionability"
    ]

    for key in positives:
        if data[key]:
            score += 1

    # Decision
    if score >= 5:
        decision = "✅ OK to Post"
    elif score >= 2:
        decision = "⚠️ Revise Before Posting"
    else:
        decision = "❌ Do NOT Post"

    # Suggestions
    suggestions = []

    if data["sensitivity"]:
        suggestions.append("Tone down message — avoid celebratory language")
    if data["risk_trigger"]:
        suggestions.append("Remove urgency / panic wording")
    if data["aggressive_promo"]:
        suggestions.append("Reduce hard selling tone")
    if not data["reassurance"]:
        suggestions.append("Add reassurance (stores open, availability, etc.)")
    if not data["clarity"]:
        suggestions.append("Simplify message (5-second rule)")
    if not data["actionability"]:
        suggestions.append("Tell customers what to do (shop early, delivery, etc.)")

    if not suggestions:
        suggestions.append("Looks good — ready to post")

    return score, decision, suggestions


# Save function
def save_to_csv(data, score, decision, post_name):
    file_name = "posting_log.csv"

    new_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "post_name": post_name,
        "sensitivity": data["sensitivity"],
        "customer_value": data["customer_value"],
        "clarity": data["clarity"],
        "reassurance": data["reassurance"],
        "relevance": data["relevance"],
        "tone_balance": data["tone_balance"],
        "actionability": data["actionability"],
        "risk_trigger": data["risk_trigger"],
        "aggressive_promo": data["aggressive_promo"],
        "score": score,
        "decision": decision
    }

    df_new = pd.DataFrame([new_row])

    if os.path.exists(file_name):
        df_existing = pd.read_csv(file_name)
        df = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_csv(file_name, index=False)


# Button action
if st.button("🚀 Evaluate Post"):
    if not post_name.strip():
        st.warning("⚠️ Please enter a post caption before evaluating.")
    else:
        score, decision, suggestions = evaluate_post(data, mode)

        save_to_csv(data, score, decision, post_name)

        st.divider()

        st.metric("Score", score)
        st.markdown(f"### {decision}")

        st.write("### 💡 Suggestions")
        for s in suggestions:
            st.write(f"- {s}")

        st.info("👉 Final check: Does this make customers feel more confident or more confused?")


# Show history
if os.path.exists("posting_log.csv"):
    st.divider()
    st.subheader("📊 Posting History")
    df = pd.read_csv("posting_log.csv")
    st.dataframe(df)