import streamlit as st
import pandas as pd
from datetime import datetime
import os
import anthropic
import json

# ─── Constants ────────────────────────────────────────────────────────────────
PENALTY_NORMAL = -2
PENALTY_SENSITIVE = -3
DECISION_THRESHOLDS = {"ok": 5, "revise": 2}

CRITERIA = [
    {"key": "sensitivity",      "label": "⚠️ This post might feel tone-deaf or too celebratory", "type": "risk"},
    {"key": "risk_trigger",     "label": "⚠️ Might cause panic or confusion",                    "type": "risk"},
    {"key": "aggressive_promo", "label": "⚠️ Feels too promotional or pushy",                    "type": "risk"},
    {"key": "customer_value",   "label": "✅ This post helps customers (inform / guide / ease shopping)", "type": "positive"},
    {"key": "clarity",          "label": "✅ Message is clear within 5 seconds",                 "type": "positive"},
    {"key": "reassurance",      "label": "✅ Adds reassurance (stores open, availability, etc.)", "type": "positive"},
    {"key": "relevance",        "label": "✅ Relevant to current situation",                      "type": "positive"},
    {"key": "tone_balance",     "label": "✅ Tone is gentle (not overly festive)",                "type": "positive"},
    {"key": "actionability",    "label": "✅ Tells customers what to do",                         "type": "positive"},
]

LOG_FILE = "posting_log.csv"

# ─── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="CMHL Posting Guide", layout="centered")

st.title("🛒 CMHL Content Decision Tool")
st.caption("Keep every post calm, clear, and customer-first")
st.warning("⚠️ Use this tool before posting any content during sensitive periods")

# ─── Context ──────────────────────────────────────────────────────────────────
mode = st.radio("Select Context", ["Normal", "Sensitive Period (Thingyan / Crisis)"])

st.divider()

# ─── Post input ───────────────────────────────────────────────────────────────
post_caption = st.text_area(
    "📝 Enter Post Caption / Name (Max 500 characters)",
    max_chars=500,
    placeholder="Type your post caption here..."
)

st.subheader("📝 Quick Evaluation")

# ─── Checklist UI (driven by CRITERIA config) ─────────────────────────────────
checklist = {}
for item in CRITERIA:
    checklist[item["key"]] = st.checkbox(item["label"])

# ─── Logic ────────────────────────────────────────────────────────────────────
def evaluate_post(checklist: dict, mode: str) -> tuple[int, str, list[str]]:
    score = 0
    penalty = PENALTY_SENSITIVE if mode == "Sensitive Period (Thingyan / Crisis)" else PENALTY_NORMAL

    for item in CRITERIA:
        key = item["key"]
        if item["type"] == "risk":
            score += penalty if checklist[key] else 1
        else:
            score += 1 if checklist[key] else 0

    if score >= DECISION_THRESHOLDS["ok"]:
        decision = "✅ OK to Post"
    elif score >= DECISION_THRESHOLDS["revise"]:
        decision = "⚠️ Revise Before Posting"
    else:
        decision = "❌ Do NOT Post"

    suggestions = []
    if checklist["sensitivity"]:
        suggestions.append("Tone down message — avoid celebratory language")
    if checklist["risk_trigger"]:
        suggestions.append("Remove urgency / panic wording")
    if checklist["aggressive_promo"]:
        suggestions.append("Reduce hard selling tone")
    if not checklist["reassurance"]:
        suggestions.append("Add reassurance (stores open, availability, etc.)")
    if not checklist["clarity"]:
        suggestions.append("Simplify message (5-second rule)")
    if not checklist["actionability"]:
        suggestions.append("Tell customers what to do (shop early, delivery, etc.)")

    if not suggestions:
        suggestions.append("Looks good — ready to post")

    return score, decision, suggestions


def analyze_with_ai(caption: str, mode: str) -> dict:
    """Send the caption to Claude for tone and risk analysis."""
    client = anthropic.Anthropic()

    system_prompt = """You are a social media content reviewer for a Myanmar retail grocery chain called CMHL.
Your job is to evaluate post captions for tone, risk, and customer value — especially during sensitive cultural 
or crisis periods like Thingyan (Water Festival) or emergencies.

Respond ONLY with a valid JSON object — no preamble, no markdown, no code fences.

The JSON must have exactly these keys:
{
  "tone": "calm | neutral | celebratory | alarming | pushy",
  "risk_level": "low | medium | high",
  "customer_value": "high | medium | low",
  "summary": "One sentence summary of the post's intent.",
  "ai_suggestions": ["suggestion 1", "suggestion 2"],
  "revised_caption": "A revised version of the caption if improvements are needed, otherwise return the original."
}"""

    user_message = f"""Context: {mode}

Post caption to review:
\"{caption}\"

Evaluate this caption and return the JSON."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)


def save_to_csv(checklist: dict, score: int, decision: str, post_name: str, ai_result: dict | None):
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "post_name": post_name,
        **{item["key"]: checklist[item["key"]] for item in CRITERIA},
        "score": score,
        "decision": decision,
        "ai_tone": ai_result.get("tone", "") if ai_result else "",
        "ai_risk": ai_result.get("risk_level", "") if ai_result else "",
        "ai_customer_value": ai_result.get("customer_value", "") if ai_result else "",
        "ai_summary": ai_result.get("summary", "") if ai_result else "",
    }

    try:
        df_new = pd.DataFrame([row])
        if os.path.exists(LOG_FILE):
            df_existing = pd.read_csv(LOG_FILE)
            df = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df = df_new
        df.to_csv(LOG_FILE, index=False)
    except Exception as e:
        st.error(f"⚠️ Could not save log: {e}")


@st.cache_data
def load_history():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    return pd.DataFrame()


# ─── Evaluate button ──────────────────────────────────────────────────────────
if st.button("🚀 Evaluate Post"):
    if not post_caption.strip():
        st.warning("⚠️ Please enter a post caption before evaluating.")
    else:
        score, decision, suggestions = evaluate_post(checklist, mode)

        # ── AI Analysis ──
        ai_result = None
        with st.spinner("🤖 Running AI analysis on your caption..."):
            try:
                ai_result = analyze_with_ai(post_caption, mode)
            except Exception as e:
                st.warning(f"AI analysis unavailable: {e}")

        save_to_csv(checklist, score, decision, post_caption, ai_result)

        st.divider()

        # ── Checklist result ──
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Checklist Score", score)
        with col2:
            st.markdown(f"### {decision}")

        st.write("### 💡 Checklist Suggestions")
        for s in suggestions:
            st.write(f"- {s}")

        # ── AI result ──
        if ai_result:
            st.divider()
            st.subheader("🤖 AI Analysis")

            col1, col2, col3 = st.columns(3)
            col1.metric("Tone", ai_result.get("tone", "—").capitalize())
            col2.metric("Risk Level", ai_result.get("risk_level", "—").capitalize())
            col3.metric("Customer Value", ai_result.get("customer_value", "—").capitalize())

            st.write("**Summary:**", ai_result.get("summary", ""))

            if ai_result.get("ai_suggestions"):
                st.write("**AI Suggestions:**")
                for s in ai_result["ai_suggestions"]:
                    st.write(f"- {s}")

            revised = ai_result.get("revised_caption", "")
            if revised and revised != post_caption:
                st.write("**✍️ Suggested Revised Caption:**")
                st.info(revised)

        st.info("👉 Final check: Does this make customers feel more confident or more confused?")

# ─── History ──────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 Posting History")
df = load_history()
if df.empty:
    st.caption("No evaluations logged yet.")
else:
    st.dataframe(df)
