import streamlit as st
import openai
import pandas as pd
from io import StringIO
from openai import OpenAI

# Configure page
st.set_page_config(layout="wide", page_title="ENTC Timetable Generator")

# Custom UI
with st.container():
    st.markdown("""
    <style>
    .main {background-color: #f9f9f9; padding: 20px; border-radius: 10px;}
    h1 {color: #0F52BA; text-align: center; font-size: 2.5em;}
    .stButton>button {background-color: #0F52BA; color: white; border-radius: 5px; padding: 10px 20px; font-weight: bold;}
    .stButton>button:hover {background-color: #084298;}
    td[colspan] {text-align: center; background-color: #e8f4ff;}
    </style>
    <div class="main">
        <h1>AI INFUSED DESIGN PLANNING</h1>
        <h3 style="text-align:center;">ENTC Department Timetable Generator</h3>
    </div>
    """, unsafe_allow_html=True)

# Initialize OpenAI client
client = OpenAI(api_key="LLM API KEY / OPEN AI API KEY")

# Prompt generator
def generate_prompt(subjects_lecture, subjects_practical, division, all_teachers, all_rooms):
    prompt = f"""
Generate a structured academic timetable for {division} using a markdown table (not CSV, plain text, or code block) with the following structure and rules:

📅 Days: Monday to Friday
🕒 Time Slots (Columns):
• 8:45–9:45
• 9:45–10:45
• 10:45–11:30
• 11:30–12:30
• 12:30–1:30
• 1:30–1:45
• 1:45–2:45
• 2:45–3:45

 Rules:

A teacher must not appear in more than one place at the same time, whether in lecture or practical. This rule must be strictly followed across all time slots and divisions.

Each lecture lasts exactly 1 hour and must be scheduled in any of the 1-hour slots except break times.

Each practical lasts exactly 2 hours and can only be scheduled in the following fixed blocks:

8:45–10:45

11:30–1:30

1:45–3:45
If a practical is scheduled in any of these blocks, no lecture should be scheduled within any overlapping time slot.
During a practical block, both B1 and B2 must have practicals simultaneously, formatted like this:
B1:SubjectName(TeacherCode)Room | B2:SubjectName(TeacherCode)Room

Each day must include one 2-hour practical block with two parallel practicals, formatted as shown above.

Distribute practicals fairly across all three practical blocks (morning, mid-day, afternoon) over the week.

All other available slots must be filled with 1-hour lecture subjects.

Each lecture subject can appear only once per day.

A teacher cannot teach more than 4 hours per day, including both lectures and practicals.

Do not invent any subjects, teachers, or rooms. Use only the data provided below.

The timetable must include exactly two fixed breaks every day, clearly labeled as BREAK, and they must always be at these exact time slots — no exceptions:

10:45–11:30

1:30–1:45
Do not move, remove, or replace these breaks under any condition.
Lectures:

"""
    for s in subjects_lecture:
        prompt += f"- {s}\n"
    prompt += "\nPracticals:\n"
    for s in subjects_practical:
        prompt += f"- {s}\n"
    return prompt

# HTML Renderer
def markdown_to_html(markdown_table, title):
    try:
        lines = [line.strip() for line in markdown_table.strip().split('\n') if "|" in line]
        headers = [col.strip() for col in lines[0].split("|") if col.strip()]
        rows = []
        for line in lines[2:]:
            split_line = line.split("|")
            cells = [cell.strip() for cell in split_line[1:-1]]
            if len(cells) < len(headers):
                cells += ["MISSING"] * (len(headers) - len(cells))
            elif len(cells) > len(headers):
                cells = cells[:len(headers)]
            rows.append(cells)
        df = pd.DataFrame(rows, columns=headers)
    except Exception as e:
        return f"<p>Error parsing table: {e}</p>"

    html = f"<h4 style='text-align:center'>{title}</h4>"
    html += """
    <style>
    table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; text-align: center; }
    th, td { border: 1px solid #888; padding: 8px; }
    th { background-color: #e0e0e0; }
    td.break { background-color: #f2f2f2; font-weight: bold; }
    </style>
    <table><thead><tr>""" + "".join(f"<th>{h}</th>" for h in df.columns) + "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>" + "".join(
            f"<td class='break'>{cell}</td>" if isinstance(cell, str) and "break" in cell.lower()
            else f"<td>{cell}</td>" for cell in row) + "</tr>"
    html += "</tbody></table>"
    return html

# UI and Input
all_teacher_names = []
all_room_names = []
timetables = {}

with st.sidebar:
    st.header("Enter Subjects and Teachers for Each Year")

    def get_year_input(year_name):
        timetables[year_name] = {}
        for section in ["Section A", "Section B"]:
            if section not in timetables[year_name]:
                timetables[year_name][section] = {"lectures": [], "practicals": []}
            num_lec = st.number_input(f"Number of Lecture Subjects for {year_name} {section}", 0, 10, key=f"lec_count_{year_name}_{section}")
            lectures = []
            for i in range(num_lec):
                subj = st.text_input(f"{year_name} {section} Lecture {i+1} Subject", key=f"lec_subj_{year_name}_{section}_{i}")
                teacher = st.text_input(f"{year_name} {section} Lecture {i+1} Teacher", key=f"lec_teacher_{year_name}_{section}_{i}")
                if subj and teacher:
                    lectures.append(f"{subj} ({teacher})")
                    all_teacher_names.append(teacher)

            num_prac = st.number_input(f"Number of Practical Subjects for {year_name} {section}", 0, 10, key=f"prac_count_{year_name}_{section}")
            practicals = []
            for i in range(num_prac):
                subj = st.text_input(f"{year_name} {section} Practical {i+1} Subject", key=f"prac_subj_{year_name}_{section}_{i}")
                teacher = st.text_input(f"{year_name} {section} Practical {i+1} Teacher", key=f"prac_teacher_{year_name}_{section}_{i}")
                room = st.text_input(f"{year_name} {section} Practical {i+1} Room", key=f"prac_room_{year_name}_{section}_{i}")
                if subj and teacher and room:
                    practicals.append(f"{subj} ({teacher}) {room}")
                    all_teacher_names.append(teacher)
                    all_room_names.append(room)

            timetables[year_name][section]["lectures"] = lectures
            timetables[year_name][section]["practicals"] = practicals

    get_year_input("Second Year")
    get_year_input("Third Year")
    get_year_input("Final Year")

# Generate Button
if st.button("Generate Timetable"):
    for year in ["Second Year", "Third Year", "Final Year"]:
        for section in ["Section A", "Section B"]:
            division = f"{year} {section}"
            section_data = timetables.get(year, {}).get(section, {})
            lectures = section_data.get("lectures", [])
            practicals = section_data.get("practicals", [])

            if not lectures and not practicals:
                continue

            prompt = generate_prompt(lectures, practicals, division, all_teacher_names, all_room_names)

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a timetable-generating assistant for an engineering college. Your task is to generate a timetable strictly based on the provided data only. Do not assume or add anything extra. Strictly follow the user’s prompt structure and constraints to generate a markdown table for the timetable. Do not assign any teacher to more than one place at the same time. The output must follow the exact format and rules given, without deviation or extrapolation. Ensure no empty cells and that every box is filled appropriately."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                timetable = response.choices[0].message.content.strip()
                st.markdown(markdown_to_html(timetable, f"{division} Timetable"), unsafe_allow_html=True)
                with st.expander("📄 Raw Markdown Table"):
                    st.code(timetable, language="markdown")
            except Exception as e:
                st.error(f"❌ Error generating timetable for {division}: {e}")

