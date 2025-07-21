import streamlit as st

# Inject custom CSS for styling
st.markdown("""
    <style>
    body {
        background-color: #f0f4f8;
        font-family: 'Segoe UI', sans-serif;
    }
    .stApp {
        max-width: 1000px;
        margin: auto;
        padding: 2rem;
    }
    .block-container {
        background-color: white;
        border-radius: 10px;
        padding: 2rem;
        border-left: 6px solid #2a6de0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
    }
    h1, h2, h3 {
        color: #2a6de0;
    }
    .stTextInput > div > div > input {
        border: 2px solid #2a6de0;
        border-radius: 5px;
        padding: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


# === Basic password protection ===
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect password")
        return False
    else:
        return True

if not check_password():
    st.stop()

import pandas as pd
import os
from openai import OpenAI
from PIL import Image
import json

# === Load OpenAI API Key ===
client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"],
    organization=st.secrets["OPENAI_ORG_ID"],
    project=st.secrets["OPENAI_PROJECT_ID"]
)

# === Synonyms and Mappings ===

gender_synonyms = {
    "male": ["male", "man", "men", "boy", "boys", "guy", "guys"],
    "female": ["female", "woman", "women", "girl", "girls", "lady", "ladies"]
}

state_abbr = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA",
    "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM",
    "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY"
}
region_synonyms = {
    "rust belt": ["IL", "IN", "MI", "MO", "NY", "OH", "PA", "WI"],
    "battleground": ["PA", "WI", "MI", "AZ", "NV", "GA", "NC"],
    "south": ["TX", "FL", "GA", "AL", "MS", "SC", "NC", "LA", "TN"],
    "midwest": ["IL", "IN", "IA", "MI", "MN", "MO", "OH", "WI"],
    "west": ["CA", "CO", "WA", "OR", "NV", "AZ"],
    "northeast": ["NY", "NJ", "MA", "CT", "PA", "MD"],
    "sun belt": ["AL", "AZ", "CA", "FL", "GA", "LA", "MS", "NM", "SC", "NV", "NC", "OK", "TX", "TN", "UT", "AR"],
    "bible belt": ["AL", "AR", "FL", "GA", "KS", "KY", "LA", "MO", "MS", "NC", "OK", "SC", "TN", "TX", "VA", "WV"],
    "pacific northwest": ["WA", "OR", "ID"],
    "mountain west": ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY"],
    "deep south": ["AL", "GA", "LA", "MS", "SC"]
}

# === Merge state_abbr and state_groups ===
state_abbr.update(region_synonyms)

issue_synonyms = {
    "abortion": ["abortion", "choice", "reproductive rights", "roe", "dobbs", "planned parenthood"],
    "small biz": ["small biz", "small business", "business owner", "entrepreneur", "startup", "independent business", "family business", "local business", "businesses", "self-employed", "self employment", "small business owners", "small business owner", "small businesses"],
    "RX drugs / healthcare": ["healthcare", "medical", "medicaid", "doctor", "hospital", "insurance" , "rx", "prescription rx", "prescription drugs", "rx drugs"],
    "student debt": ["student debt", "loan forgiveness", "student loans", "college debt", "debt relief"],
    "inflation": ["inflation", "prices", "cost of living", "grocery", "gas", "economy"],
    "democracy": ["democracy", "election", "vote", "trump", "january 6", "insurrection"]
}

race_synonyms = {
    "White": ["white", "caucasian"],
    "AfAm": ["black", "african american", "afam", "african-american"],
    "Latino": ["latino", "latina", "latinx", "hispanic"],
    "AAPI": ["aapi", "asian", "asian american", "pacific islander"],
    "Native": ["native", "indigenous", "american indian"],
    "Mixed": ["mixed", "biracial", "multiracial"],
    "Other": ["other"]
}

# === Name Variants ===
name_variants = {
    "matt": ["matt", "matthew"],
    "liz": ["liz", "elizabeth"],
    "kate": ["kate", "katherine", "kathryn"],
    "john": ["john", "jon"],
    "alex": ["alex", "alexander", "alexandra"],
    "rick": ["rick", "richard", "ricky"],
    "patrick": ["patrick", "pat"]
}

# === Load Data ===
df = pd.read_excel("GPT Version -- BSS Storybank.xlsx")
df.columns = df.columns.str.strip()

# === Page Layout ===
st.set_page_config(page_title="Blue Sky Strategy StoryBot", layout="wide")
st.title("🔍 Blue Sky Strategy StoryBot")
st.markdown("Enter the type of story you're looking for! (e.g. 'Please give me one story on abortion from a battleground state'):")
query = st.text_input("What kind of story are you looking for?", "")

# === Run Search ===
if query:
    # Step 1: Ask GPT to generate filters
    prompt = f"""
You are an assistant helping search a structured voter story database.
The user asked: '{query}'
Return a JSON with keys: \"state\", \"issue\", \"gender\", \"race\", \"name\", and \"total_requested\".
Only extract real values. If unclear, leave the field empty.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract clean search filters from user queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        filters = response.choices[0].message.content.strip()

        st.subheader("Filters Interpreted by GPT")
        st.code(filters)

        # Step 2: Apply filters (enhanced matching logic)
        try:
            filter_dict = json.loads(filters)
            filtered_df = df.copy()

# --- State Filter ---
            if filter_dict.get("state"):
                states = [s.strip() for s in filter_dict["state"].split(",")]
                expanded_states = []
                for s in states:
                    upper_s = s.upper()
                    lower_s = s.lower()
                    if upper_s in state_abbr:
                        val = state_abbr[upper_s]
                    elif lower_s in state_abbr:
                        val = state_abbr[lower_s]
                    else:
                        val = s.upper()
                    if isinstance(val, list):
                        expanded_states.extend(val)
                    else:
                        expanded_states.append(val)
                if "State" in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df["State"].astype(str).str.upper().isin(expanded_states)]
                st.write("✅ Rows after state filter:", len(filtered_df))

# --- Issue Filter ---
            if filter_dict.get("issue"):
                issue = filter_dict["issue"].lower()
                expanded_issues = [issue]
                for k, v in issue_synonyms.items():
                    if issue in v:
                        expanded_issues.extend(v)
                for col in ["Issue"]:
                    if col in filtered_df.columns:
                        mask = filtered_df[col].astype(str).str.lower().apply(lambda x: any(term in x for term in expanded_issues))
                        filtered_df = filtered_df[mask]
                        st.markdown(f"✅ Rows after **issue** filter: {len(filtered_df)}")
                        break

# --- Gender Filter ---
            if filter_dict.get("gender"):
                gender_input = filter_dict["gender"].lower()
                normalized_gender = None
                for label, synonyms in gender_synonyms.items():
                    if gender_input in synonyms:
                        normalized_gender = label
                        break
                if normalized_gender and "Gender" in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df["Gender"].astype(str).str.lower() == normalized_gender]
                st.write("✅ Rows after gender filter:", len(filtered_df))

# --- Race Filter ---
            if filter_dict.get("race"):
                race = filter_dict["race"].lower()
                expanded_races = [race]
                for k, v in race_synonyms.items():
                    if race in v:
                        expanded_races.extend(v)
                for col in ["Race", "Demographic"]:
                    if col in filtered_df.columns:
                        mask = filtered_df[col].astype(str).str.lower().apply(lambda x: any(term in x for term in expanded_races))
                        filtered_df = filtered_df[mask]
                        st.markdown(f"✅ Rows after **race** filter: {len(filtered_df)}")
                        break

# --- Name Filter ---
            if filter_dict.get("name"):
                name = filter_dict["name"].lower()
                if "First Name" in filtered_df.columns and "Last Name" in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df["First Name"].astype(str).str.lower().str.contains(name, na=False) |
                        filtered_df["Last Name"].astype(str).str.lower().str.contains(name, na=False)
                    ]
                    st.markdown(f"✅ Rows after **name** filter: {len(filtered_df)}")

            try:
                # Try to extract number from query if GPT didn't supply one
                if not filter_dict.get("total_requested"):
                    import re
                    match = re.search(r'\b(\d+)\b', query)
                    if match:
                        filter_dict["total_requested"] = match.group(1)

                # Safely handle int or str
                total_requested_raw = filter_dict.get("total_requested", 3)
                total = int(total_requested_raw) if isinstance(total_requested_raw, str) else total_requested_raw
                if total <= 0:
                    total = 3
            except (ValueError, TypeError):
                total = 3
                        top_stories = filtered_df.head(total)

            st.subheader("📋 Matching Stories")

            for _, row in top_stories.iterrows():
                full_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                st.markdown("""---""")
                st.markdown(f"**NAME**: {full_name}")
                st.markdown(f"**STATE**: {row.get('State', 'N/A')}")
                st.markdown(f"**ISSUE**: {row.get('Issue', 'N/A')}")
                st.markdown(f"**Age**: {row.get('Age', 'N/A')}")
                st.markdown(f"**Race**: {row.get('Race', row.get('Demographic', 'N/A'))}")
                st.markdown(f"**STORY**:\n{row.get('Story', row.get('Story Overview', 'N/A'))}")
                st.markdown(f"**Email**: {row.get('Email', 'N/A')}")
                st.markdown(f"**Phone**: {row.get('Phone', 'N/A')}")

                photo_path = os.path.join("photos", f"{row.get('Unique ID', '')}.jpg")
                if os.path.exists(photo_path):
                    image = Image.open(photo_path)
                    st.image(image, caption=f"Photo for {full_name}", width=300)
                else:
                    st.markdown("_No photo available._")

        except Exception as e:
            st.error(f"❌ Error applying filters: {e}")

    except Exception as e:
        st.error(f"❌ GPT API error: {e}")
