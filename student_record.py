import os

def read_student_record(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist. Creating a new file with default content.")
        default_content = """
# Student Record

## Student Information
**Name:** Taylor Teal

## Engagement
_No engagement yet._

## Knowledge
- **Idioms:** Not demonstrated
- **Vocabulary:** Not demonstrated
- **Grammar:** Not demonstrated
"""
        with open(file_path, "w") as file:
            file.write(default_content)
        return default_content

    with open(file_path, "r") as file:
        return file.read()

def write_student_record(file_path, content):
    with open(file_path, "w") as file:
        file.write(content)

def format_student_record(student_info, engagement, knowledge):
    record = "# Student Record\n\n## Student Information\n"
    for key, value in student_info.items():
        record += f"**{key}:** {value}\n"
    
    record += "\n## Engagement\n"
    if engagement:
        for engagement_entry in engagement:
            print("taylor--------> Engagement entry: \n\n", engagement_entry)
            record += f"- **{engagement_entry.get('score', '')}:** {engagement_entry.get('summary', '')}\n"
    else:
        record += "_No engagement yet._\n"
    
    record += "\n## Knowledge\n"
    for key, value in knowledge.items():
        record += f"- **{key}:** {value}\n"
    
    return record

def parse_student_record(markdown_content):
    student_info = {}
    engagement = []
    knowledge = {}
    
    current_section = None
    lines = markdown_content.split("\n")
    
    for line in lines:
        line = line.strip()  # Strip leading/trailing whitespace
        if line.startswith("## "):
            current_section = line[3:].strip()
        elif current_section == "Student Information" and line.startswith("**"):
            if ":** " in line:
                key, value = line.split(":** ", 1)
                key = key.strip("**").strip()
                value = value.strip()
                student_info[key] = value
        elif current_section == "Engagement":
            if "_No engagement yet._" in line:
                engagement = []
            elif line.startswith("- **"):
                if ":** " in line:
                    score, summary = line.split(":** ", 1)
                    score = score.strip("- **").strip()
                    summary = summary.strip()
                    engagement.append({"score": score, "summary": summary})
        elif current_section == "Knowledge" and line.startswith("- **"):
            if ":** " in line:
                key, value = line.split(":** ", 1)
                key = key.strip("- **").strip()
                value = value.strip()
                knowledge[key] = value
    
    final_record = {
        "Student Information": student_info,
        "Engagement": engagement,
        "Knowledge": knowledge
    }
    print(f"Final parsed record: {final_record}")
    return final_record